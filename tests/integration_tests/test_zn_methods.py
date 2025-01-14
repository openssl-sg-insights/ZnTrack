import dataclasses
import json
import pathlib
import subprocess
import typing

import pytest
import yaml

from zntrack import zn
from zntrack.core.base import Node


@dataclasses.dataclass
class ExampleMethod:
    param1: int
    param2: int


@dataclasses.dataclass
class ExampleMethod2:
    param3: int
    param4: int


class SingleNode(Node):
    data_class: ExampleMethod = zn.Method()
    dummy_param = zn.params(1)  # required to have some dependency
    result = zn.outs()

    def __init__(self, data_class=None, **kwargs):
        super().__init__(**kwargs)
        self.data_class = data_class

    def run(self):
        self.result = self.data_class.param1 + self.data_class.param2


class HelloWorld(Node):
    param = zn.params(42)

    def run(self):
        pass


def test_run_twice_diff_params(proj_path):
    SingleNode(data_class=ExampleMethod(1, 1)).write_graph(no_exec=False)
    assert SingleNode.load().result == 2
    # second run
    SingleNode(data_class=ExampleMethod(2, 2)).write_graph(no_exec=False)
    subprocess.check_call(["dvc", "repro"])
    assert SingleNode.load().result == 4


class SingleNodeWithDefault(Node):
    data_class: ExampleMethod = zn.Method(ExampleMethod(2, 2))
    result = zn.outs()

    def run(self):
        self.result = self.data_class.param1 + self.data_class.param2


def test_run_with_default(proj_path):
    SingleNodeWithDefault().write_graph(no_exec=False)

    assert SingleNodeWithDefault.load().result == 4


class SingleNodeMethodList(Node):
    data_classes: typing.List[ExampleMethod] = zn.Method()
    dummy_param = zn.params(1)  # required to have some dependency
    result = zn.outs()

    def __init__(self, data_classes=None, **kwargs):
        super().__init__(**kwargs)
        self.data_classes = data_classes

    def run(self):
        self.result = sum(x.param1 + x.param2 for x in self.data_classes)


def test_methods_list(proj_path):
    single_node = SingleNodeMethodList(
        data_classes=[
            ExampleMethod(param1=1, param2=1),
            ExampleMethod(param1=10, param2=10),
        ]
    )

    assert isinstance(single_node.data_classes[0], ExampleMethod)

    single_node.write_graph(no_exec=False)

    assert SingleNodeMethodList.load().result == 22
    assert isinstance(SingleNodeMethodList.load().data_classes[0], ExampleMethod)
    assert SingleNodeMethodList.load().data_classes[0].param1 == 1
    assert SingleNodeMethodList.load().data_classes[1].param1 == 10


def test_diff_methods_list(proj_path):
    single_node = SingleNodeMethodList(
        data_classes=[
            ExampleMethod(param1=1, param2=2),
            ExampleMethod2(param3=3, param4=4),
        ]
    )

    single_node.save()

    assert isinstance(SingleNodeMethodList.load().data_classes[0], ExampleMethod)
    assert isinstance(SingleNodeMethodList.load().data_classes[1], ExampleMethod2)


def test_created_files(proj_path):
    # Test for https://github.com/zincware/ZnTrack/issues/192
    SingleNode(data_class=ExampleMethod(1, 2)).save()

    zntrack_dict = json.loads(pathlib.Path("zntrack.json").read_text())
    params_dict = yaml.safe_load(pathlib.Path("params.yaml").read_text())

    assert zntrack_dict["SingleNode"]["data_class"] == {
        "_type": "zn.method",
        "value": {"module": "test_zn_methods"},
    }
    assert params_dict["SingleNode"]["data_class"] == {
        "param1": 1,
        "param2": 2,
        "_cls": "ExampleMethod",
    }


class SingleNodeNoParams(Node):
    data_class: ExampleMethod = zn.Method()
    result = zn.outs()

    def __init__(self, data_class=None, **kwargs):
        super().__init__(**kwargs)
        self.data_class = data_class

    def run(self):
        self.result = self.data_class.param1 + self.data_class.param2


class EmptyMethod:
    param1 = 1
    param2 = 2


def test_write_params(proj_path):
    SingleNodeNoParams(data_class=ExampleMethod(1, 2)).write_graph(run=True)

    dvc_dict = yaml.safe_load(pathlib.Path("dvc.yaml").read_text())
    assert dvc_dict["stages"]["SingleNodeNoParams"]["params"] == ["SingleNodeNoParams"]


def test_write_params_no_kwargs(proj_path):
    SingleNodeNoParams(data_class=EmptyMethod()).write_graph(run=True)

    dvc_dict = yaml.safe_load(pathlib.Path("dvc.yaml").read_text())
    assert dvc_dict["stages"]["SingleNodeNoParams"]["params"] == ["SingleNodeNoParams"]


@pytest.fixture()
def zntrack_params_dict() -> (dict, dict):
    zntrack_dict = {
        "SingleNodeNoParams": {
            "data_class": {"_type": "zn.method", "value": {"module": "test_zn_methods"}}
        }
    }
    params_dict = {
        "SingleNodeNoParams": {
            "data_class": {"_cls": "ExampleMethod", "param1": 1, "param2": 2}
        }
    }
    return zntrack_dict, params_dict


def test_assert_write_files(proj_path, zntrack_params_dict):
    """Test the written files (without mocking pathlibs write_text)"""
    SingleNodeNoParams(data_class=ExampleMethod(1, 2)).write_graph()

    zntrack_dict = json.loads(pathlib.Path("zntrack.json").read_text())
    params_dict = yaml.safe_load(pathlib.Path("params.yaml").read_text())

    assert zntrack_dict == zntrack_params_dict[0]
    assert params_dict == zntrack_params_dict[1]


def test_assert_read_files(proj_path, zntrack_params_dict):
    """Test the written files (without mocking pathlibs write_text)"""
    zntrack_dict, params_dict = zntrack_params_dict

    pathlib.Path("zntrack.json").write_text(json.dumps(zntrack_dict))
    pathlib.Path("params.yaml").write_text(yaml.safe_dump(params_dict))

    node = SingleNodeNoParams.load()
    assert node.data_class.param1 == 1
    assert node.data_class.param2 == 2


def test_assert_read_files_old1(proj_path):
    """Test the written files (without mocking pathlibs write_text)

    Test for versions before https://github.com/zincware/ZnTrack/pull/231
    """
    zntrack_dict = {
        "SingleNodeNoParams": {
            "data_class": {
                "_type": "zn.method",
                "value": {"cls": "ExampleMethod", "module": "test_zn_methods"},
            }
        }
    }
    params_dict = {"SingleNodeNoParams": {"data_class": {"param1": 1, "param2": 2}}}

    pathlib.Path("zntrack.json").write_text(json.dumps(zntrack_dict))
    pathlib.Path("params.yaml").write_text(yaml.safe_dump(params_dict))

    node = SingleNodeNoParams.load()
    assert node.data_class.param1 == 1
    assert node.data_class.param2 == 2


def test_err_node_as_method(proj_path):
    HelloWorld().write_graph()

    with pytest.raises(ValueError):
        SingleNode(data_class=HelloWorld.load())

    with pytest.raises(ValueError):
        SingleNode(data_class=[HelloWorld.load(), HelloWorld.load()])

    with pytest.raises(ValueError):
        SingleNode(data_class=HelloWorld)

    with pytest.raises(ValueError):
        SingleNode(data_class=[HelloWorld, HelloWorld])


# Node as Method


class NodeOrMethod(Node):
    input = zn.params()
    output = zn.outs()

    def run(self):
        self.output = self.input


class NodeCollector(Node):
    output = zn.outs()

    method: NodeOrMethod = zn.deps()

    def run(self):
        self.method.run()
        self.output = self.method.output


def test_NodeCollector(proj_path):
    node_collector = NodeCollector(method=NodeOrMethod(input="Hello World"))
    node_collector.run()

    assert node_collector.output == "Hello World"


def test_NodeCollector_repro(proj_path):
    # TODO the NodeOrMethod parameter must be saved as parameters of NodeCollector
    #  and not of NodeOrMethod.
    method = NodeOrMethod(input="Hello World")
    method.write_graph(run=True)

    node_collector = NodeCollector(method=method)
    node_collector.write_graph(run=True)

    assert NodeCollector.load().output == "Hello World"
