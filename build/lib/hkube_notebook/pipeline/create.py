import json
import requests
from ..pipeline import JSON_HEADERS
from .api_utils import report_request_error

class PipelineBuilder(object):
    """ Pipeline creator: build pipeline, get as raw, store, delete, etc. """

    def __init__(self, name, options={}):
        self._name = name
        self._nodes = list()
        self._options = options

    def add_node(self, node_name, alg_name, input):
        node = {
            "nodeName": node_name,
            "algorithmName": alg_name,
            "input": input
        }
        self._nodes.append(node)

    def get_raw(self, flow_input={}):
        """ Get pipeline as a raw pipeline object """
        if self._nodes.count == 0:
            print('ERROR: pipeline has no nodes')
            return ''

        raw = {
            "name": self._name,
            "nodes": self._nodes,
            "options": self._options,
            "flowInput": flow_input
        }
        return raw

    def store(self, api_server_base_url):
        """ Store pipeline in hkube using api-server """
        if self._nodes.count == 0:
            print('ERROR: pipeline has no nodes')
            return

        store_url = '{base}/store/pipelines'.format(base=api_server_base_url)
        raw = {
            "name": self._name,
            "nodes": self._nodes,
            "options": self._options
        }
        json_data = json.dumps(raw)

        # run pipeline
        response = requests.post(store_url, headers=JSON_HEADERS, data=json_data)
        if response.status_code != 200:
            report_request_error(response, 'store pipeline "{name}"'.format(name=self._name))
            return
        print('OK: pipeline {name} stored successfully!'.format(name=self._name))

    def delete(self, api_server_base_url):
        """ Delete stored pipeline from hkube using api-server"""
        delete_url = '{base}/store/pipelines/{name}'.format(base=api_server_base_url, name=self._name)
        response = requests.delete(delete_url)
        if response.status_code != 200:
            report_request_error(response, 'delete pipeline "{name}"'.format(name=self._name))
            return
        print('OK: pipeline {name} deleted successfully!'.format(name=self._name))
