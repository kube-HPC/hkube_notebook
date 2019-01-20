import json
import logging
import time
from tqdm import tqdm_notebook, tqdm
from flask import Flask, request, abort
from threading import Thread
import requests
import socket
import random
from .progress import ProgressHandler
from .follower import FollowerType, ListenerFollower, PollFollower
from ..api_utils import report_request_error, is_success, JSON_HEADERS

MAX_RESULTS = 10

class PipelineExecutor(object):
    """ Manages an Hkube Pipeline execution (exec, run, follow status, get results, stop, etc.) """

    def __init__(self, api_server_base_url, name=None, raw=None, follower=FollowerType.LISTENER, progress_port=0):
        """ 
        :param name pipeline name, optional - for stored pipeline
        :param raw raw pipeline object, optional - for raw pipeline (overides name if given)
        :param api_server_base_url includes protocol, host, port, base path
        :param follower pipeline tracking method: listener or poller
        :param progress_port port to listen to progress messages (optional with default for listener follower only)
        """
        if name is None and raw is None:
            raise Exception('ERROR: nor stored pipeline "name" nor "raw" pipeline is given!')

        # pipeline name
        self._raw = raw
        if raw:
            self._name = raw['name']    
        else:
            self._name = name
        self._jobId = None
        self._base_url = api_server_base_url
        self._follower_type = follower
        self._follower = None
        self._pbar = None
        if progress_port == 0:
            progress_port = random.randint(50001, 59999)
        self._progress_port = progress_port
        

    def _create_follower(self):
        if self._follower_type is FollowerType.LISTENER:
            self._follower = ListenerFollower(progress_port=self._progress_port)
        else:
            self._follower = PollFollower(self._base_url)

    def _get_exec_body(self, input):
        if self._raw:
            body = self._raw.copy()
        else:
            body = {
                "name": self._name,
                "options": {
                    "batchTolerance": 100,
                }
            }

        body['flowInput'] = input
        if self._follower_type is FollowerType.LISTENER:
            body['options']['progressVerbosityLevel'] = 'debug'
            body['webhooks'] = {
                "progress": "http://{host}:{port}/webhook/progress".format(
                    host=socket.gethostname(), port=self._progress_port)
            }

        return body

    def _get_exec_url(self):
        type = 'raw' if self._raw else 'stored'
        url = '{base}/exec/{type}'.format(base=self._base_url, type=type)
        return url

    def _exec(self, input):
        self.cleanup()
        self._create_follower()
        self._pbar = tqdm_notebook(total=100)   # create new pregress bar
        self._follower.prepare()
        
        # run pipeline
        body = self._get_exec_body(input)
        exec_url = self._get_exec_url()
        json_data = json.dumps(body)
        response = requests.post(exec_url, headers=JSON_HEADERS, data=json_data)
        if not is_success(response):
            report_request_error(response, 'exec pipeline "{name}"'.format(name=self._name))
            self._follower.cleanup()
            return None

        resp_body = json.loads(response.text)
        self._jobId = resp_body['jobId']
        print('OK - pipeline is running, jobId: {}'.format(self._jobId))


    def exec_async(self, input={}):
        """ 
        Execute the pipeline asynchronously (return immediately); progress bar still displays progress

        :param input pipeline input
        :return: jobId
        """
        # execute
        self._exec(input)        
        # wait to finish
        self._follower.follow(jobId=self._jobId, pbar=self._pbar, timeout_sec=0)
        return self._jobId


    def exec(self, input={}, timeout_sec=None, max_displayed_results=MAX_RESULTS):
        """ 
        Execute the pipeline, follow progress and report results 

        :param input pipeline input
        :param timeout_sec time to track progress before return (None: return upon completion/fail/stopped)
        :param max_displayed_results max number of results to display (if 0 don't display results)
        :return: list of results
        """
        # execute
        self._exec(input)        
        # wait to finish
        self._follower.follow(jobId=self._jobId, pbar=self._pbar, timeout_sec=timeout_sec)

        # get results
        results = self.get_results(max_display=max_displayed_results)
        self._pbar.close()
        print('<<<<< finished')
        return results

    def get_results(self, max_display=0):
        """ Get results for last pipeline job """
        if self._jobId is None:
            print('ERROR: no valid jobId')
            return

        print("getting results...")
        result_url = self._base_url + '/exec/results/' + self._jobId
        time.sleep(1)
        response = requests.get(result_url, headers=JSON_HEADERS)
        # print('result status: {}'.format(response.status_code))
        if is_success(response):
            json_data = json.loads(response.text)
            status = json_data['status']
            print('pipeline "{}" status: {}'.format(self._name, status))
            if status == 'completed':
                # self._pbar.update(1) # force pbar to be green (ensure 100%, it may be less because use of round)
                timeTook = json_data['timeTook']
                print('timeTook: {} seconds'.format(timeTook))
                data = json_data['data']
                if max_display > 0:
                    i = 0
                    print('RESULT ({} of {} items):'.format(min(max_display, len(data)), len(data)))
                    for item in data:
                        i = i + 1
                        result_parsed = item['result']
                        result_pretty = json.dumps(result_parsed, indent=4, sort_keys=True)
                        print('RESULT ITEM {}:'.format(i))
                        print(result_pretty)
                        if i >= max_display:
                            break
                else:
                    print('RESULTS ITEMS: {}'.format(len(data)))
                return data
                    
            elif status == 'failed':
                try:
                    self._pbar.update(-1) # force pbar to be red
                except Exception:
                    pass
                return list()
        else:
            report_request_error(response, 
                'get results for jobId {jobid}'.format(jobid=self._jobId))
            return list()

    def stop(self, reason='stop in jupyter notebook'):
        """ Stop current jobId """
        if self._jobId is None:
            print('ERROR: cannot stop - no jobId!')
            return False

        stop_url = '{base}/exec/stop'.format(base=self._base_url)
        stop_body = {
            "jobId": self._jobId,
            "reason": reason
        }
        json_data = json.dumps(stop_body)
        response = requests.post(stop_url, headers=JSON_HEADERS, data=json_data)
        if not is_success(response):
            report_request_error(response, 'delete pipeline "{name}"'.format(name=self._name))
            return False
        else:
            print('OK - pipeline "{name}" stopped, jobId: {jobId}'.format(name=self._name, jobId=self._jobId))
        self.cleanup()
        return True

    def cleanup(self):
        """ Clean jobId and follower object """
        # print('<<Executor-Cleanup>>')
        if self._pbar is not None:
            self._pbar.close()
        if self._follower is not None:
            self._follower.cleanup()
            self._follower = None
        self._jobId = None
        

    def get_jsonId(self):
        """ Get jobId of last executed pipeline """
        return self._jobId

    @classmethod
    def get_all_stored(cls, api_server_base_url):
        """ Get all stored pipelines """
        pipelines_url = '{base}/store/pipelines'.format(base=api_server_base_url)
        response = requests.get(pipelines_url)
        if not is_success(response):
            report_request_error(response, 'get stored pipelines')
            return list()
        
        json_data = json.loads(response.text)
        pipelines_names = list(map(lambda pipeline: pipeline['name'], json_data))
        print("Got {num} stored pipelines: {names}".format(num=len(json_data), names=pipelines_names))
        return json_data

    @classmethod
    def get_running_jobs(cls, api_server_base_url):
        """ Get all running pipeline jobs """
        pipelines_url = '{base}/exec/pipelines/list'.format(base=api_server_base_url)
        response = requests.get(pipelines_url)
        if not is_success(response):
            report_request_error(response, 'get running pipelines')
            return list()
        
        json_data = json.loads(response.text)
        pipelines_jobs = list(map(lambda pipeline: pipeline['jobId'], json_data))
        print("Got {num} running jobs:".format(num=len(json_data)))
        for job in pipelines_jobs:
            print(job)
        return json_data