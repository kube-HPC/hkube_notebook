import requests
import json
import inspect
import tarfile
import os
import platform
import getpass
import git
from git import RemoteProgress
import shutil
from ..api_utils import report_request_error, is_success, JSON_HEADERS, FORM_URLENCODED_HEADERS

class CustomProgress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        if message:
            print(message, op_code, cur_count, max_count)

class AlgorithmBuilder(object):
    """ Builds, views and deletes algorithms in hkube """

    def __init__(self, api_server_base_url):
        self._base_url = api_server_base_url

    def _get_store_url(self):
        return '{base}/store/algorithms'.format(base=self._base_url)

    def _get_apply_url(self):
        return '{base}/apply/algorithms'.format(base=self._base_url)

    def get_all(self, only_names=False):
        """ Get all algorithms """
        response = requests.get(self._get_store_url(), verify=False)
        if not is_success(response):
            report_request_error(response, 'get algorithms')
            return list()
        
        json_data = json.loads(response.text)
        algs_names = list(map(lambda pipeline: pipeline['name'], json_data))
        if only_names:
            return algs_names
        print("Got {num} algorithms: {names}".format(num=len(json_data), names=algs_names))
        return json_data

    def add(self, alg_name, image, cpu, mem, options=None, min_hot_workers=None):
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
        response = requests.post(self._get_store_url(), headers=JSON_HEADERS, data=json_data, verify=False)
        if not is_success(response):
            report_request_error(response, 'post algorithm {name}'.format(name=alg_name))
            return False
        
        print("algorithm {alg} posted successfully".format(alg=alg_name))
        return True

    def delete(self, alg_name):
        """ delete algorithm from hkube """
        response = requests.delete('{base}/{name}'.format(base=self._get_store_url(), name=alg_name), verify=False)
        if not is_success(response):
            report_request_error(response, 'delete algorithm "{name}"'.format(name=alg_name))
            return False
        
        print("OK: algorithm {name} was deleted successfully".format(name=alg_name))
        return True
    
    def apply(self, compressed_alg_file, config):
        """ Request to build/rebuild an algorithm image """
        files = {'zip': open(compressed_alg_file,'rb')}
        json_config = json.dumps(config)
        values = { 'payload': json_config }
        response = requests.post(self._get_apply_url(), files=files, data=values, verify=False)
        if not is_success(response):
            report_request_error(response, 'apply algorithm "{name}"'.format(name=config['name']))
            return False
        
        print("OK: algorithm {name} was applied successfully".format(name=config['name']))
        return True

    def create_config(self, alg_name, entryfile, cpu=1, mem='512Mi', minHotWorkers=0, alg_env=None, worker_env=None, options=None):
        config = {
            "name": alg_name,
            "env": "python",
            "code": {
                "entryPoint": entryfile
            },
            "algorithmImage": "hkube/{}".format(alg_name),
            "cpu": cpu,
            "mem": mem,
            "minHotWorkers": minHotWorkers,
            "userInfo": {
                "platform": platform.system(),
                "hostname": platform.node(),
                "username": getpass.getuser()
            }
        }
        if type(worker_env) is dict:
            config['workerEnv'] = worker_env
        if type(alg_env) is dict:
            config['algorithmEnv'] = alg_env
        if type(options) is dict:
            config['options'] = options
        return config


    def create_algfile_by_functions(self, init_func, start_func, stop_func, exit_func):
        """ 
        Create algorithm code from given functions inplementations then compress to tar.gz

        :param init_func algorithm 'init' function
        :param start_func algorithm 'start' function
        :param stop_func algorithm 'stop' function
        :param exit_func algorithm 'exit' function
        :return entry_filename, compressed_filename
        """
        # create alg file code
        func_list = [
            ('init', init_func),
            ('start', start_func), 
            ('stop', stop_func), 
            ('exit', exit_func)
            ]
        alg_code = ''
        for func_info in func_list:
            try:
                func = func_info[1]
                func_name = func_info[0]
                func_code = inspect.getsource(func)
                def_func = 'def {func_name}'.format(func_name=func.__name__)
                func_code = func_code.replace(def_func, 'def ' + func_name, 1)
                alg_code += (func_code + '\n')
            except Exception as error:
                print('failure: {}'.format(error))
                return None
        
        # write to file
        filename = 'alg.py'
        fd = open(filename, "w")
        fd.write(alg_code)
        fd.close()

        # create tar.gz file
        tarfilename = '{cwd}/alg.tar.gz'.format(cwd=os.getcwd())
        with tarfile.open(tarfilename, mode='w:gz') as archive:
            archive.add(filename)

        return filename, tarfilename


    def create_algfile_by_folder(self, folder_path):
        """ Compress given python algorithm folder content to tar.gz """
        # create tar.gz file recursively from all folder contents
        tarfilename = '{cwd}/alg.tar.gz'.format(cwd=os.getcwd())
        # folderpath_aslist = folder_path.split('/')
        # just_folder = folderpath_aslist.pop()
        # path_tofolder = '/'.join(folderpath_aslist)
        cwd = os.getcwd()
        folder_content_list = os.listdir(folder_path)
        os.chdir(folder_path)
        with tarfile.open(tarfilename, mode='w:gz') as archive:
            for file in folder_content_list:
                archive.add(file, recursive=True)
        os.chdir(cwd)
        return tarfilename


    def create_algfile_by_github(self, github_url, alg_root_in_project='', clean=True):
        """ 
        Clone github algorithm project and compress it to tar.gz
        
        :param github_url github algorithm project url, e.g.: git@github.com:kube-HPC/ds-alg-example.git
        :param alg_root_in_project relative root path of python algorithm within the project repo folder
        :param clean if True remove temporary folder where we put alg project just after compressing it
        """
        local_dir = f'{os.getcwd()}/githubclone'
        if os.path.exists(local_dir):
            print('removing prev local repo...')
            shutil.rmtree(local_dir)
        os.mkdir(local_dir)
        try:
            repo = git.Repo.clone_from(github_url, local_dir, branch='master', progress=CustomProgress())
        except Exception as error:
            print(f'Error: failed to clone repo: {error.__str__()}')
            return None

        if repo is None:
            print('ERROR: got no repo')
            return None
        
        alg_path = f'{local_dir}/{alg_root_in_project}'
        tarfilename = self.create_algfile_by_folder(alg_path)
        if clean:
            print('removing local repo...')
            shutil.rmtree(local_dir)
        return tarfilename
