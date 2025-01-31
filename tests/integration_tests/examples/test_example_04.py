from zntrack import Node, ZnTrackProject, zn


class HelloWorld(Node):
    """BasicTest class"""

    output = zn.outs()
    inputs = zn.params()

    def __init__(self, inputs=None, **kwargs):
        super().__init__(**kwargs)
        self.inputs = inputs

    def run(self):
        """Run method of the Node test instance"""
        self.output = self.inputs


def test_basic_io_assertion(proj_path):
    """Make a simple input/output assertion test for the nodes with different names"""
    project = ZnTrackProject()

    HelloWorld(inputs=3).write_graph()
    HelloWorld(name="Test01", inputs=17).write_graph()
    HelloWorld(name="Test02", inputs=42).write_graph()

    project.repro()

    assert HelloWorld.load().output == 3
    assert HelloWorld.load(name="Test01").output == 17
    assert HelloWorld.load(name="Test02").output == 42
