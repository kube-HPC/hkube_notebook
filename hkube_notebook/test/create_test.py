from unittest import TestCase
from hkube_notebook.pipeline.create import PipelineBuilder

class TestCreatePipeline(TestCase):

    def test_build(self):
        pipe_name = 'moshe'
        api_server = 'http://localhost:3000/api/v1'
        pb = PipelineBuilder(name=pipe_name, api_server_base_url=api_server)
        pb.add_node(node_name='green', alg_name='green-alg', input=["@flowInput.tata"])
        pb.add_node(node_name='yellow', alg_name='yellow-alg', input=["@green"])
        pb.add_node(node_name='black', alg_name='black-alg', input=["@yellow"])
        moshe_raw = pb.get_raw()
        self.assertIsNotNone(moshe_raw)
        
