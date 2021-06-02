import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union


@dataclass(frozen=False, order=True)
class DVCParams:
    # DVCOp Parameter
    multi_use: bool = False
    params_file: str = 'params.json'
    params_file_path: Path = Path("config")

    dvc_file: str = "dvc.yaml"

    # DVC Parameter
    deps: list[Path] = field(default_factory=list)
    # deps_path: Path = Path("deps")

    outs: list[str] = field(default_factory=list)
    outs_path: Path = Path("outs")

    outs_no_cache: list[str] = field(default_factory=list)
    outs_no_cache_path: Path = Path("outs")

    outs_persistent: list[str] = field(default_factory=list)
    outs_persistent_path: Path = Path("outs")

    params: list[str] = field(default_factory=list)
    params_path: Path = Path("params")

    metrics: list[str] = field(default_factory=list)
    metrics_path: Path = Path("metrics")

    metrics_no_cache: list[str] = field(default_factory=list)
    metrics_no_cache_path: Path = Path("metrics")

    plots: list[str] = field(default_factory=list)
    plots_path: Path = Path("plots")

    plots_no_cache: list[str] = field(default_factory=list)
    plots_no_cache_path: Path = Path("plots")

    def make_paths(self):
        """Create all paths that can possibly be used"""
        for key in self.__dict__:
            if key.endswith('path'):
                # self.__dict__[key]: Path
                if len(self.__dict__[key[:-5]]) > 0:
                    # Check if the corresponding list has an entry - if not, you don't need to create the folder
                    self.__dict__[key].mkdir(exist_ok=True, parents=True)


@dataclass(frozen=False, order=True, init=False)
class Files:
    deps: list[Path]
    outs: list[Path]
    outs_no_cache: list[Path]
    outs_persistent: list[Path]
    params: list[Path]
    metrics: list[Path]
    metrics_no_cache: list[Path]
    plots: list[Path]
    plots_no_cache: list[Path]

    json_file: Union[Path, None] = None

    def __init__(self, id_: str, dvc_params: DVCParams, json_file):
        if json_file is not None:
            json_file = dvc_params.outs_path / f"{id_}_{json_file}"

        # NOTE: Can not use this, because it is a dataclass! Have to use property setter
        # for key in self.__dict__:
        #     if key == "json_file":
        #         continue
        #
        #     self.__dict__[key] = [dvc_params.__dict__[f"{key}_path"] / f"{id_}_{x}" for x in dvc_params.__dict__[key]]

        # self.deps = [dvc_params.deps_path / f"{id_}_{dep}" for dep in dvc_params.deps]
        self.deps = dvc_params.deps
        self.outs = [dvc_params.outs_path / f"{id_}_{out}" for out in dvc_params.outs]
        self.outs_no_cache = [dvc_params.outs_no_cache_path / f"{id_}_{out}" for out in dvc_params.outs_no_cache]
        self.outs_persistent = [dvc_params.outs_persistent_path / f"{id_}_{out}" for out in dvc_params.outs_persistent]
        self.params = [dvc_params.params_path / f"{id_}_{param}" for param in dvc_params.params]
        self.metrics = [dvc_params.metrics_path / f"{id_}_{metric}" for metric in dvc_params.metrics]
        self.metrics_no_cache = [dvc_params.metrics_no_cache_path / f"{id_}_{metric}" for metric in
                                 dvc_params.metrics_no_cache]
        self.plots = [dvc_params.plots_path / f"{id_}_{plot}" for plot in dvc_params.plots]
        self.plots_no_cache = [dvc_params.plots_no_cache_path / f"{id_}_{plot}" for plot in dvc_params.plots_no_cache]
        self.json_file = json_file

    def get_dvc_arguments(self) -> list:
        def flatten(x):
            """
            Convert [[str, Path], [str, Path]] to [str, Path, str, Path]
            """
            return sum(x, [])

        out = []

        for option in self.__dict__:
            try:
                out.append(
                    flatten([[f"--{option.replace('_', '-')}", x] for x in self.__dict__[option]])
                )
            except TypeError:
                # reached json_file which is not iterable!
                pass
        if self.json_file is not None:
            out += [['--outs', self.json_file]]

        return flatten(out)


@dataclass(frozen=True, order=True)
class SlurmConfig:
    n: int = 1
