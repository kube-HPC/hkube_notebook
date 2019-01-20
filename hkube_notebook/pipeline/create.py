import json
import requests
from ..api_utils import report_request_error, is_success, JSON_HEADERS
from ..algorithm.manager import AlgorithmManager

class PipelineBuilder(object):
    """ Pipeline creator: build pipeline, get as raw, store, delete, etc. """

    def __init__(self, name, api_server_base_url, options={}):
        self._name = name
        self._nodes = list()
        self._options = options
        self._base_url = api_server_base_url

    def add_node(self, node_name, alg_name, input, extra_data=None):
        algorithms = AlgorithmManager.get_all(api_server_base_url=self._base_url, only_names=True)
        if alg_name not in algorithms:
            print('ERROR: unknown algorithm "{name}"'.format(name=alg_name))
            print('Registered algorithms: {algs}'.format(algs=algorithms))
            return False
        node = {
            "nodeName": node_name,
            "algorithmName": alg_name,
            "input": input
        }
        if extra_data is not None:
            node['extraData'] = extra_data
        self._nodes.append(node)
        return True

    def get_raw(self, flow_input={}):
        """ Get pipeline as a raw pipeline object """
        if len(self._nodes) == 0:
            print('ERROR: pipeline has no nodes')
            return None

        raw = {
            "name": self._name,
            "nodes": self._nodes,
            "options": self._options,
            "flowInput": flow_input
        }
        return raw

    def store(self):
        """ Store pipeline in hkube using api-server """
        if len(self._nodes) == 0:
            print('ERROR: pipeline has no nodes')
            return False

        store_url = '{base}/store/pipelines'.format(base=self._base_url)
        raw = {
            "name": self._name,
            "nodes": self._nodes,
            "options": self._options
        }
        json_data = json.dumps(raw)

        # run pipeline
        response = requests.post(store_url, headers=JSON_HEADERS, data=json_data)
        if not is_success(response):
            report_request_error(response, 'store pipeline "{name}"'.format(name=self._name))
            return False
        print('OK: pipeline "{name}" was stored successfully!'.format(name=self._name))
        return True

    def delete(self):
        """ Delete stored pipeline from hkube using api-server"""
        delete_url = '{base}/store/pipelines/{name}'.format(base=self._base_url, name=self._name)
        response = requests.delete(delete_url)
        if not is_success(response):
            report_request_error(response, 'delete pipeline "{name}"'.format(name=self._name))
            return False
        print('OK: pipeline "{name}" was deleted successfully!'.format(name=self._name))
        return True
