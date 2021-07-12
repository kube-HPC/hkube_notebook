import json
import requests
from ..api_utils import report_request_error, is_success, JSON_HEADERS
from ..algorithm.manager import AlgorithmBuilder
from hkube_notebook.config import config, utils

class PipelineBuilder(object):
    """ Pipeline creator: build pipeline, get as raw, store, delete, etc. """

    def __init__(self, name, options={}):
        self._name = name
        self._nodes = list()
        self._options = options
        self._base_url = utils.api_server_url(options)
        self._alg_mgr = AlgorithmBuilder(options)

    def add_node(self, node_name, alg_name, input, extra_data=None, validate_alg=False):
        """
        Add node to pipeline.
        :param node_name node name
        :param alg_name algorithm name
        :param extra_data node extra_data object (used in eval-alg)
        :param validate_alg if True check alg_name to be a known algorithm
        """
        if validate_alg:
            algorithms = self._alg_mgr.get_all(only_names=True)
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
        response = requests.post(store_url, headers=JSON_HEADERS, data=json_data, verify=config.api['verify_ssl'])
        if not is_success(response):
            report_request_error(response, 'store pipeline "{name}"'.format(name=self._name))
            return False
        print('OK: pipeline "{name}" was stored successfully!'.format(name=self._name))
        return True

    def delete(self):
        """ Delete stored pipeline from hkube using api-server"""
        delete_url = '{base}/store/pipelines/{name}'.format(base=self._base_url, name=self._name)
        response = requests.delete(delete_url, verify=config.api['verify_ssl'])
        if not is_success(response):
            report_request_error(response, 'delete pipeline "{name}"'.format(name=self._name))
            return False
        print('OK: pipeline "{name}" was deleted successfully!'.format(name=self._name))
        return True
