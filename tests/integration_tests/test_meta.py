import pathlib
import subprocess

import pytest
import yaml

import zntrack


class NodeWithMeta(zntrack.Node):
    author = zntrack.meta.Text("Fabian")
    title = zntrack.meta.Text("Test Node")


def test_NodeWithMeta(proj_path):
    NodeWithMeta().write_graph()

    node_w_meta = NodeWithMeta.load()
    assert node_w_meta.author == "Fabian"

    dvc_yaml = yaml.safe_load(pathlib.Path("dvc.yaml").read_text())
    assert dvc_yaml["stages"]["NodeWithMeta"]["meta"] == {
        "author": "Fabian",
        "title": "Test Node",
    }


class CombinedNodeWithMeta(zntrack.Node):
    input: str = zntrack.zn.params("Hello ")
    output: str = zntrack.zn.outs()
    author: str = zntrack.meta.Text()

    def run(self):
        self.output = self.input + self.author


def test_CombinedNodeWithMeta(proj_path):
    with pytest.raises(TypeError):
        # should raise an error because author is missing as kwarg
        _ = CombinedNodeWithMeta()

    CombinedNodeWithMeta(author="World").write_graph(run=True)
    assert CombinedNodeWithMeta.load().output == "Hello World"
    assert CombinedNodeWithMeta.load().author == "World"

    CombinedNodeWithMeta(author="there").write_graph(run=True)
    # changing the 'meta.Text' should not trigger running the model again
    assert CombinedNodeWithMeta.load().output == "Hello World"
    assert CombinedNodeWithMeta.load().author == "there"

    subprocess.check_call(["dvc", "repro", "-f"])
    # Forcing rerun should use the updated meta keyword.
    assert CombinedNodeWithMeta.load().output == "Hello there"
