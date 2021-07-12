import requests
import json
import inspect
import tarfile
import os
import time
import platform
import getpass
import git
from git import RemoteProgress
import shutil
import pathlib
import subprocess
from ..api_utils import report_request_error, is_success, JSON_HEADERS, FORM_URLENCODED_HEADERS
from hkube_notebook.config import config as config_object

class CustomProgress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        if message:
            print(message, op_code, cur_count, max_count)

class TextSpinner(object):
    SPINNER_STATES = ('-', '/', '|', '\\')
    
    def __init__(self):
        self._i = 0
    
    def get_next(self, text):
        result = f'{TextSpinner.SPINNER_STATES[self._i]} {text}'
        self._i += 1
        if self._i >= len(TextSpinner.SPINNER_STATES):
            self._i = 0
        return result

class AlgorithmBuilder(object):
    """ Builds, views and deletes algorithms in hkube """

    POLL_INTERVAL_SEC = 1
    
    def __init__(self, api_server_base_url):
        self._base_url = api_server_base_url

    def _get_store_url(self):
        return f'{self._base_url}/store/algorithms'

    def _get_apply_url(self):
        return f'{self._base_url}/store/algorithms/apply'

    def _get_build_status_url(self, build_id):
        return f'{self._base_url}/builds/status/{build_id}'

    def get_all(self, only_names=False):
        """ Get all algorithms """
        response = requests.get(self._get_store_url(), verify=config_object.api['verify_ssl'])
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
        response = requests.post(self._get_store_url(), headers=JSON_HEADERS, data=json_data, verify=config_object.api['verify_ssl'])
        if not is_success(response):
            report_request_error(response, 'post algorithm {name}'.format(name=alg_name))
            return False
        
        print("algorithm {alg} posted successfully".format(alg=alg_name))
        return True

    def delete(self, alg_name):
        """ delete algorithm from hkube """
        response = requests.delete('{base}/{name}'.format(base=self._get_store_url(), name=alg_name), verify=config_object.api['verify_ssl'])
        if not is_success(response):
            report_request_error(response, 'delete algorithm "{name}"'.format(name=alg_name))
            return False
        
        print("OK: algorithm {name} was deleted successfully".format(name=alg_name))
        return True
    
    def get_build_state(self, build_id, verbose=True):
        """ return algorithm build state (including status and all algorithm properties) """
        status_url = self._get_build_status_url(build_id)
        response = requests.get(status_url, verify=config_object.api['verify_ssl'])
        if not is_success(response):
            report_request_error(response, 'get algorithm build status')
            return None
        json_data = json.loads(response.text)
        #alg = json_data['algorithm']
        #name = alg['name']
        name = json_data['algorithmName']
        status = json_data['status']
        if verbose:
            print(f'algorithm {name} buildId {build_id} status: {status}')
        return json_data

    def apply_async(self, compressed_alg_file, config):
        """ 
        Async request to build/rebuild an algorithm image
        :param compressed_alg_file algorithm tar.gz filename
        :param config algorithm configuration
        :return algorithm build state - if not includes buildId then build is completed
        """
        name = config['name']
        files = {'file': open(compressed_alg_file,'rb')}
        json_config = json.dumps(config)
        values = { 'payload': json_config }
        response = requests.post(self._get_apply_url(), files=files, data=values, verify=config_object.api['verify_ssl'])
        if not is_success(response):
            report_request_error(response, f'build algorithm "{name}"')
            return None
        state = json.loads(response.text)
        
        return state

    def apply(self, compressed_alg_file, config):
        """ 
        Blocking request to build/rebuild an algorithm image
        :param compressed_alg_file algorithm tar.gz filename
        :param config algorithm configuration
        :return algorithm state (including status and all algorithm properties)
        """
        name = config['name']
        state = self.apply_async(compressed_alg_file, config)
        if state is None:
            return None
        if "buildId" in state.keys():
            current_milli_time = lambda: int(round(time.time() * 1000))
            start_time = current_milli_time()
            build_id = state['buildId']
            print(f'algorithm buildId: {build_id}')
            # poll build status
            status = ''
            spinner = TextSpinner()
            while not (status=='completed' or status=='failed'):
                state = self.get_build_state(build_id, verbose=False)
                if state is None:
                    return None
                status = state['status']
                print(spinner.get_next(f'...building algorithm {name} - status: {status}               '), end='\r')
                time.sleep(AlgorithmBuilder.POLL_INTERVAL_SEC)
                
        build_time_sec = (current_milli_time() - start_time)/1000
        if status == 'completed':
            print(f"OK: algorithm {name} was built successfully in {build_time_sec} seconds                ")
            return state
        print(f'Algorithm {name} build failed after {build_time_sec} seconds')
        return state

    def create_config(self, alg_name, entryfile, is_image=False, cpu=1, mem='512Mi', minHotWorkers=0, version=None, alg_env=None, worker_env=None, options=None):
        config = {
            "name": alg_name,
            "env": "python",
            "entryPoint": entryfile,
            "cpu": cpu,
            "mem": mem,
            "minHotWorkers": minHotWorkers,
            "userInfo": {
                "platform": platform.system(),
                "hostname": platform.node(),
                "username": getpass.getuser()
            }
        }
        if is_image:
            config['algorithmImage'] = "hkube/{}".format(alg_name)
        if type(worker_env) is dict:
            config['workerEnv'] = worker_env
        if type(alg_env) is dict:
            config['algorithmEnv'] = alg_env
        if type(options) is dict:
            config['options'] = options
        if version is not None:
            config['version'] = version
        return config


    def create_algfile_by_functions(self, start_func, init_func=None, stop_func=None, exit_func=None):
        """ 
        Create algorithm code from given functions inplementations then compress to tar.gz.
        NOTE: given funcions must include the whole code (imports, internal functions as nested, etc.)

        :param start_func algorithm 'start' function
        :param init_func algorithm 'init' function (optional)
        :param stop_func algorithm 'stop' function (optional)
        :param exit_func algorithm 'exit' function (optional)
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
                if func is not None:
                    func_name = func_info[0]
                    func_code = inspect.getsource(func)
                    def_func = 'def {func_name}'.format(func_name=func.__name__)
                    func_code = func_code.replace(def_func, 'def ' + func_name, 1)
                    alg_code += (func_code + '\n')
            except Exception as error:
                print('failure: {}'.format(error))
                return None
        
        # write to file
        dirname = 'temp'
        pathlib.Path(dirname).mkdir(exist_ok=True)
        filename = 'alg.py'
        fd = open(f'{dirname}/{filename}', "w")
        fd.write(alg_code)
        fd.close()
        # run_state = subprocess.run(f'pipreqs --force {dirname}', shell=True)  
        run_state = subprocess.run(['pipreqs', '--force',  dirname])  
        if not run_state.returncode == 0:
            print(f'ERROR: failed to create requirements.txt file (error: {run_state.stderr}, stderr: {run_state.stdout})')
            return filename, None
        # NOTE: it works only when 'pipreqs' is installed in target python env.
        
        # create tar.gz file
        tarfilename = self.create_algfile_by_folder(folder_path=dirname, files_list=[filename, 'requirements.txt'])

        return filename, tarfilename


    def create_algfile_by_folder(self, folder_path, files_list=None):
        """ 
        Compress given python algorithm folder content (or given files) to tar.gz

        :param folder_path path to source folder of which we compress
        :param files_list if None insert recursively all folder contents, else insert given files.
        :return tarfilename
        """
        # create tar.gz file recursively from all folder contents
        tarfilename = '{cwd}/alg.tar.gz'.format(cwd=os.getcwd())
        cwd = os.getcwd()
        try:
            if files_list is None:
                files_list = os.listdir(folder_path)
            os.chdir(folder_path)
            with tarfile.open(tarfilename, mode='w:gz') as archive:
                for file in files_list:
                    archive.add(file, recursive=True)
        except Exception as error:
            print(f'ERROR: failed to create tar file {tarfilename}: {error.__str__()}')
            os.chdir(cwd)
            return None
        
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
