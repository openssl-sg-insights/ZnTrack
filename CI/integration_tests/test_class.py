from zntrack import Node, dvc, ZnTrackProject
from pathlib import Path
import json
import os
import shutil
from tempfile import TemporaryDirectory
import pytest

temp_dir = TemporaryDirectory()
cwd = os.getcwd()


@Node()
class BasicTest:
    """BasicTest class"""

    def __init__(self):
        """Constructor of the Node test instance"""
        self.deps = dvc.deps([Path("deps1", "input.json"), Path("deps2", "input.json")])
        self.parameters = dvc.params()
        self.results = dvc.result()

    def __call__(self, **kwargs):
        """Call Method of the Node test instance"""
        self.parameters = kwargs

    def run(self):
        """Run method of the Node test instance"""
        self.results = {"name": self.parameters["name"]}


@pytest.fixture(autouse=True)
def prepare_env():
    temp_dir = TemporaryDirectory()
    shutil.copy(__file__, temp_dir.name)
    os.chdir(temp_dir.name)

    project = ZnTrackProject()
    project.create_dvc_repository()

    base = BasicTest()
    base(name="PyTest", values=[2, 4, 8, 16, 32, 64, 128, 256])

    for idx, dep in enumerate(base.deps):
        Path(dep).parent.mkdir(exist_ok=True, parents=True)
        with open(dep, "w") as f:
            json.dump({"id": idx}, f)

    project.name = "Test1"
    project.repro()

    yield

    os.chdir(cwd)
    temp_dir.cleanup()


def test_parameters():
    """Test that the parameters are read correctly"""
    base = BasicTest(load=True)
    assert base.parameters == dict(
        name="PyTest", values=[2, 4, 8, 16, 32, 64, 128, 256]
    )


def test_results():
    """Test that the results are read correctly"""
    base = BasicTest(load=True)
    assert base.results == {"name": "PyTest"}


def test_deps():
    """Test that the dependencies are stored correctly"""
    base = BasicTest(load=True)
    assert base.deps == [Path("deps1", "input.json"), Path("deps2", "input.json")]
