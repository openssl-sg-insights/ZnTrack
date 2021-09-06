"""
This program and the accompanying materials are made available under the terms of the
Eclipse Public License v2.0 which accompanies this distribution, and is available at
https://www.eclipse.org/legal/epl-v20.html
SPDX-License-Identifier: EPL-2.0

Copyright Contributors to the Zincware Project.

Description: PyTrack parameter
"""
from __future__ import annotations
import logging
import typing

import json
from pytrack.utils import is_jsonable, serializer, deserializer
from pathlib import Path
from typing import Union

log = logging.getLogger(__file__)

if typing.TYPE_CHECKING:
    from pytrack.utils.type_hints import TypeHintParent


class PyTrackOption:
    def __init__(
        self,
        value: Union[str, tuple] = None,
        option: str = None,
        attr: str = None,
        cls: TypeHintParent = None,
    ):
        """PyTrack Descriptor to handle the loading and writing of files

        Parameters
        ----------
        option: str
            One of the DVC options, e.g., params, outs, ...
        value:
            default value
        attr
        cls
        """
        if option is None:
            log.warning("Using a custom PyTrackOption! No default values supported!")
            option = "custom"

        self.pytrack_dvc_option = option
        self.value = value
        self.check_input(value)
        if value is not None and cls is not None:
            value = self.make_serializable(value)
            self.set_internals(cls, {attr: value})

    def __get__(self, instance: TypeHintParent, owner):
        """Get the value of this instance from pytrack_internals and return it"""
        try:
            return self._get(instance, owner)
        except NotImplementedError:
            if self.pytrack_dvc_option == "result":
                return deserializer(
                    self.get_results(instance).get(self.get_name(instance))
                )
            else:
                output = self.get_internals(instance).get(self.get_name(instance), "")
                return deserializer(output)
                # if self.pytrack_dvc_option == "params":
                #     return deserializer(output)
                # elif self.pytrack_dvc_option == "deps":
                #     if isinstance(output, list):
                #         return [Path(x) for x in output]
                #     else:
                #         return Path(output)
                # else:
                #     # convert to path
                #     file_path: Path = getattr(
                #         instance.pytrack.dvc, f"{self.pytrack_dvc_option}_path"
                #     )
                #     if isinstance(output, list):
                #         return [file_path / x for x in output]
                #     elif isinstance(output, str):
                #         return file_path / output
                #     else:
                #         return output

    def __set__(self, instance: TypeHintParent, value):
        """Update the value"""
        try:
            self._set(instance, value)
        except NotImplementedError:
            if self.pytrack_dvc_option != "result":
                self.check_input(value)
            log.debug(f"Updating {self.get_name(instance)} with {value}")

            value = self.make_serializable(value)

            self.set_internals(instance, {self.get_name(instance): value})

    def _get(self, instance: TypeHintParent, owner):
        """Overwrite this method for custom PyTrackOption get method"""
        raise NotImplementedError

    def _set(self, instance: TypeHintParent, value):
        """Overwrite this method for custom PyTrackOption set method"""
        raise NotImplementedError

    def make_serializable(self, value):
        """Make value serializable to save as json"""
        if isinstance(value, self.__class__):
            value = value.value

        # Check if the passed value is a PyTrack class
        # if so, add its json file as a dependency to this stage.
        if hasattr(value, "pytrack"):
            # Allow self.deps = DVC.deps(Stage(id_=0))
            if self.pytrack_dvc_option == "deps":
                new_value = value.pytrack.dvc.json_file
                if new_value is None:
                    raise ValueError(f"Stage {value} has no results assigned to it!")
                else:
                    value = new_value

        value = serializer(value)

        return value

    def get_name(self, instance):
        """

        Parameters
        ----------
        instance: TypeHintParent
            A instance of the Parent that contains

        Returns
        -------
        str: Name of this instance, e.g., self.abc = DVC.outs() returns "abc"

        """
        for attr, val in vars(type(instance)).items():
            if val == self:
                return attr

        raise ValueError(f"Could not find {self} in instance {instance}")

    def check_input(self, value):
        if isinstance(value, dict):
            log.warning(
                f"Used mutable type dict for {self.pytrack_dvc_option}! "
                f"Always overwrite the {self.pytrack_dvc_option} and don't alter it otherwise!"
                f" It won't work."
            )

        if isinstance(value, list):
            log.warning(
                f"Used mutable type list for {self.pytrack_dvc_option}! "
                f"Always overwrite the {self.pytrack_dvc_option} and don't append to it!"
                f" It won't work."
            )

    def set_internals(self, instance: TypeHintParent, value: dict):
        """Set the Internals for this instance (Stage & Id)

        This writes them to self._pytrack_all_parameters, i.e., to the config file.
        """
        if isinstance(value, dict):
            if self.pytrack_dvc_option == "result":
                if not instance.pytrack.allow_result_change:
                    if instance.pytrack.is_init:
                        log.debug("ValueError Exception during init!")
                        return
                    else:
                        raise ValueError(
                            "Result can only be changed within `run` call!"
                        )
                    # log.warning("Result can only be changed within `run` call!")
                    # return
                if not is_jsonable(value):
                    raise ValueError("Results must be JSON serializable")
                log.debug(f"Processing value {value}")
                results = self.get_results(instance)
                results.update(value)
                self.set_results(instance, results)

            else:
                log.debug(
                    f"Param_Change: {instance.pytrack.allow_param_change} on {instance.pytrack}"
                )
                if not instance.pytrack.allow_param_change:
                    if instance.pytrack.is_init:
                        log.debug("ValueError Exception during init!")
                        return
                    else:
                        raise ValueError(
                            "This stage is being loaded. Parameters can not be set!"
                        )
                value = self.make_serializable(value)
                name = instance.pytrack.name
                id_ = instance.pytrack.id
                file = instance.pytrack.dvc.internals_file

                full_internals = self.get_full_internals(file)
                stage = full_internals.get(name, {})
                stage_w_id = stage.get(id_, {})

                option = stage_w_id.get(self.pytrack_dvc_option, {})
                option.update(value)

                stage_w_id[self.pytrack_dvc_option] = option
                stage[id_] = stage_w_id
                full_internals[name] = stage

                self.set_full_internals(file, full_internals)

        else:
            raise ValueError(
                f"Value has to be a dictionary but found {type(value)} instead!"
            )

    def get_internals(self, instance: TypeHintParent):
        """Get the parameters for this instance (Stage & Id)"""
        name = instance.pytrack.name
        id_ = instance.pytrack.id
        file = instance.pytrack.dvc.internals_file

        full_internals = self.get_full_internals(file)

        return (
            full_internals.get(name, {}).get(id_, {}).get(self.pytrack_dvc_option, {})
        )

    @staticmethod
    def get_full_internals(file) -> dict:
        """Load ALL internals from .pytrack.json"""
        try:
            with open(file) as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            log.debug(f"Could not load params from {file}!")
        return {}

    @staticmethod
    def set_full_internals(file, value: dict):
        """Update internals in .pytrack.json"""
        log.debug(f"Writing updates to .pytrack.json as {value}")
        value.update({"default": None})

        if not is_jsonable(value):
            raise ValueError(f"{value} is not JSON serializable")

        Path(file).parent.mkdir(exist_ok=True, parents=True)

        with open(file, "w") as json_file:
            json.dump(value, json_file, indent=4)

    @staticmethod
    def get_results(instance: TypeHintParent):
        file = instance.pytrack.dvc.json_file
        try:
            with open(file) as f:
                result = json.load(f)
            log.debug(f"Loading results {result}")
            return result
        except FileNotFoundError:
            log.warning("No results found!")
            return {}

    @staticmethod
    def set_results(instance: TypeHintParent, value):
        file = instance.pytrack.dvc.json_file
        if not is_jsonable(value):
            raise ValueError(f"{value} is not JSON serializable")
        log.debug(f"Writing {value} to {file}")
        with open(file, "w") as f:
            json.dump(value, f, indent=4)
        log.debug("successful!")

    def __repr__(self):
        return f"Descriptor for {self.pytrack_dvc_option}"


class DVC:
    """Basically a dataclass of DVC methods

    Referring to https://dvc.org/doc/command-reference/run#options
    """

    def __init__(self):
        """Basically a dataclass of DVC methods"""
        raise NotImplementedError(
            "Cannot initialize DVC - this class is only for accessing its methods!"
        )

    @staticmethod
    def params(value=None):
        """Parameter for PyTrack

        Parameters
        ----------
        obj: any class object that the parameter will take on, so that type hinting does not raise issues

        Returns
        -------
        cls: Class that inherits from obj

        """

        return PyTrackOption(value, option="params")

    @staticmethod
    def result(value=None):
        """Parameter for PyTrack

        Parameters
        ----------
        obj: any class object that the parameter will take on, so that type hinting does not raise issues
        outs: Future Version, allows for defining the type ot output

        Returns
        -------
        cls: Class that inherits from obj

        """

        if value is not None:
            raise ValueError("Can not pre-initialize result!")

        return PyTrackOption(value, option="result")

    @staticmethod
    def deps(value=None):
        return PyTrackOption(value, option="deps")

    @staticmethod
    def outs(value=None):
        return PyTrackOption(value, option="outs")

    @staticmethod
    def metrics_no_cache(value=None):
        return PyTrackOption(value, option="metrics_no_cache")
