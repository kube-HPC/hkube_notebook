import requests
import json
from ..api_utils import report_request_error, is_success, JSON_HEADERS

class AlgorithmManager(object):
    """ Manages algorithms in hkube """

    @classmethod
    def _get_alg_url(clas, api_server_base_url):
        return '{base}/store/algorithms'.format(base=api_server_base_url)

    @classmethod
    def get_all(cls, api_server_base_url, only_names=False):
        """ Get all algorithms """
        response = requests.get(cls._get_alg_url(api_server_base_url))
        if not is_success(response):
            report_request_error(response, 'get algorithms')
            return list()
        
        json_data = json.loads(response.text)
        algs_names = list(map(lambda pipeline: pipeline['name'], json_data))
        if only_names:
            return algs_names
        print("Got {num} algorithms: {names}".format(num=len(json_data), names=algs_names))
        return json_data

    @classmethod
    def add(cls, api_server_base_url, alg_name, image, cpu, mem, options=None, min_hot_workers=None):
        """ Add algorithm to hkube """
        algorithm = {
            "name": alg_name,
            "algorithmImage": image,
            "cpu": cpu,
            "mem": mem
        }
        if options is not None:
            algorithm['options'] = options
        if min_hot_workers is not None:
            algorithm['minHotWorkers'] = min_hot_workers

        json_data = json.dumps(algorithm)
        response = requests.post(cls._get_alg_url(api_server_base_url), headers=JSON_HEADERS, data=json_data)
        if not is_success(response):
            report_request_error(response, 'post algorithm {name}'.format(name=alg_name))
            return False
        
        print("algorithm {alg} posted successfully".format(alg=alg_name))
        return True

    @classmethod
    def delete(cls, api_server_base_url, alg_name):
        """ delete algorithm from hkube """
        response = requests.delete('{base}/{name}'.format(base=cls._get_alg_url(api_server_base_url), name=alg_name))
        if not is_success(response):
            report_request_error(response, 'delete algorithm "{name}"'.format(name=alg_name))
            return False
        
        print("OK: algorithm {name} was deleted successfully".format(name=alg_name))
        return True
    