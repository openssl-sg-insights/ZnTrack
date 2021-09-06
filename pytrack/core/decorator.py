"""
This program and the accompanying materials are made available under the terms of the
Eclipse Public License v2.0 which accompanies this distribution, and is available at
https://www.eclipse.org/legal/epl-v20.html
SPDX-License-Identifier: EPL-2.0

Copyright Contributors to the Zincware Project.

Description: PyTrack decorators
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
import re
import sys
import typing

from .py_track import PyTrackParent

log = logging.getLogger(__file__)

if typing.TYPE_CHECKING:
    from pytrack.utils.type_hints import TypeHintParent


class PyTrack:
    def __init__(self, cls=None, nb_name: str = None, name: str = None, **kwargs):
        """

        Parameters
        ----------
        cls: object
            Required for use as decorator with @PyTrack
        nb_name: str
            Name of the jupyter notebook e.g. PyTrackNb.ipynb which enables jupyter support
        name: str
            A custom name for the DVC stage.
            !There is currently no check in place, that avoids overwriting an existing stage!
        kwargs: No kwargs are implemented
        """
        if cls is not None:
            raise ValueError("Please use `@Pytrack()` instead of `@Pytrack`.")
        self.cls = cls

        self.name = name

        self.pytrack_cls_dict = {}
        # TODO maybe make this a weakref dict?

        self.kwargs = kwargs
        self.return_with_args = True
        log.debug(f"decorator_kwargs: {kwargs}")

        # jupyter
        if nb_name is not None:
            log.warning(
                "Jupyter support is an experimental feature! Please save your notebook before running this command!\n"
                "Submit issues to https://github.com/zincware/py-track."
            )
            nb_name = Path(nb_name)
        self.nb_name = nb_name
        self.nb_class_path = Path("src")

    def __call__(self, *args, **kwargs):
        """

        Parameters
        ----------
        args: tuple
            The first arg might be the class, if @PyTrack() is used, otherwise args that are passed to the cls
        kwargs: dict
            kwargs that are passed to the cls

        Returns
        -------

        decorated cls

        """
        log.debug(f"call_args: {args}")
        log.debug(f"call kwargs: {kwargs}")

        if self.cls is None:
            self.cls = args[0]
            self.return_with_args = False

        self.apply_decorator()

        if self.nb_name is not None:
            self.jupyter_class_to_file()

        if self.return_with_args:
            return self.cls(*args, **kwargs)
        else:
            return self.cls

    def jupyter_class_to_file(self):
        """Extract the class definition form a ipynb file"""

        subprocess.run(["jupyter", "nbconvert", "--to", "script", self.nb_name])

        reading_class = False

        imports = ""

        class_definition = ""

        with open(Path(self.nb_name).with_suffix(".py"), "r") as f:
            for line in f:
                if line.startswith("import") or line.startswith("from"):
                    imports += line
                if reading_class:
                    if (
                        re.match(r"\S", line)
                        and not line.startswith("#")
                        and not line.startswith("class")
                    ):
                        reading_class = False
                if reading_class or line.startswith("class"):
                    reading_class = True
                    class_definition += line
                if line.startswith("@PyTrack"):
                    reading_class = True
                    class_definition += "@PyTrack()\n"

        src = imports + "\n\n" + class_definition

        src_file = Path(self.nb_class_path, self.cls.__name__).with_suffix(".py")
        self.nb_class_path.mkdir(exist_ok=True, parents=True)

        src_file.write_text(src)

        # Remove converted ipynb file
        self.nb_name.with_suffix(".py").unlink()

    def apply_decorator(self):
        """Apply the decorators to the class methods"""
        if "run" not in vars(self.cls):
            raise NotImplementedError("PyTrack class must implement a run method!")

        if "__call__" not in vars(self.cls):
            setattr(self.cls, "__call__", lambda *args: None)

        if "__init__" not in vars(self.cls):
            setattr(self.cls, "__init__", lambda *args: None)

        for name, obj in vars(self.cls).items():
            if name == "__init__":
                setattr(self.cls, name, self.init_decorator(obj))
            if name == "__call__":
                setattr(self.cls, name, self.call_decorator(obj))
            if name == "run":
                setattr(self.cls, name, self.run_decorator(obj))

    def init_decorator(self, func):
        """Decorator to handle the init of the decorated class"""

        def wrapper(cls: TypeHintParent, *args, id_=None, **kwargs):
            log.debug(f"Got id_: {id_}")

            def map_pytrack_to_dict(self_):
                """Map the correct pytrack instance to the correct cls

                This is required, because we use setattr(TYPE(cls)) and not on the instance,
                so we need to distinguish between different instances, otherwise there is only a single
                cls.pytrack for all instances!
                """
                if self.pytrack_cls_dict.get(self_) is None:
                    self.pytrack_cls_dict[self_] = PyTrackParent(self_)
                return self.pytrack_cls_dict[self_]

            setattr(type(cls), "pytrack", property(map_pytrack_to_dict))

            cls.pytrack.pre_init(id_=id_)
            log.debug(f"Processing {cls.pytrack}")
            result = func(cls, *args, **kwargs)
            cls.pytrack.post_init()

            cls.pytrack.stage_name = self.name

            if self.nb_name is not None:
                cls.pytrack._module = f"{self.nb_class_path}.{self.cls.__name__}"
                cls.pytrack.nb_mode = True

            if cls.pytrack.module == "__main__":
                cls.pytrack._module = Path(sys.argv[0]).stem

            return result

        return wrapper

    @staticmethod
    def call_decorator(f):
        """Decorator to handle the call of the decorated class"""

        def wrapper(
            cls: TypeHintParent,
            *args,
            force=True,
            exec_=False,
            always_changed=False,
            slurm=False,
            **kwargs,
        ):
            cls.pytrack.pre_call()
            function = f(cls, *args, **kwargs)
            cls.pytrack.post_call(force, exec_, always_changed, slurm)
            return function

        return wrapper

    @staticmethod
    def run_decorator(f):
        """Decorator to handle the run of the decorated class"""

        def wrapper(cls: TypeHintParent):
            cls.pytrack.pre_run()
            function = f(cls)
            cls.pytrack.post_run()
            return function

        return wrapper
