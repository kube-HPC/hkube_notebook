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
from ..pipeline import JSON_HEADERS
from .api_utils import report_request_error

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
        self._flask_thread = None
        self._jobId = None
        self._base_url = api_server_base_url
        self._follower_type = follower
        if progress_port == 0:
            progress_port = random.randint(50001, 59999)
        self._progress_port = progress_port
        if follower is FollowerType.LISTENER:
            self._follower = ListenerFollower(progress_port=progress_port)
        else:
            self._follower = PollFollower(api_server_base_url)

    # flask server func
    @classmethod
    def _run_server(cls, progress_handler, port):
        progress_handler.run(port)


    def _get_exec_body(self, input):
        if self._raw:
            body = self._raw.copy()
        else:
            body = {
                "name": self._name,
                "options": {
                    "batchTolerance": 100,
                    "progressVerbosityLevel": "debug"
                }
            }

        body['flowInput'] = input
        if self._follower_type is FollowerType.LISTENER:
            body['webhooks'] = {
                "progress": "http://{host}:{port}/webhook/progress".format(
                    host=socket.gethostname(), port=self._progress_port)
            }

        return body

    def __get_exec_url(self):
        type = 'raw' if self._raw else 'stored'
        url = '{base}/exec/{type}'.format(base=self._base_url, type=type)
        return url

    def exec(self, input={}, timeout_sec=10):
        """ 
        Execute the pipeline, follow progress and report results 

        :param input pipeline input
        :param timeout_sec max estimated pipeline execution time (stop execution after timeout)
        """
        self._pbar = tqdm_notebook(total=100)   # create new pregress bar
        self._follower.prepare()
        
        # run pipeline
        body = self._get_exec_body(input)
        exec_url = self.__get_exec_url()
        json_data = json.dumps(body)
        response = requests.post(exec_url, headers=JSON_HEADERS, data=json_data)
        if response.status_code != 200:
            report_request_error(response, 'exec pipeline "{name}"'.format(name=self._name))
            self._follower.cleanup()
            return

        resp_body = json.loads(response.text)
        self._jobId = resp_body['jobId']
        print('request status={} - pipeline jobId: {}'.format(response.status_code, self._jobId))
        
        # wait to finish
        self._follower.follow(jobId=self._jobId, pbar=self._pbar, timeout_sec=timeout_sec)
            
        # get results
        self._pbar.close()
        results = self.get_results()
        print('<<<<< finished')
        return results

    def get_results(self):
        """ Get results for saved jobId """
        if self._jobId is None:
            print('ERROR: no valid jobId')
            return

        print("getting results...")
        result_url = self._base_url + '/exec/results/' + self._jobId
        time.sleep(1)
        response = requests.get(result_url, headers=JSON_HEADERS)
        print('result status: {}'.format(response.status_code))
        if response.status_code == 200:
            json_data = json.loads(response.text)
            status = json_data['status']
            print('pipeline "{}" status: {}'.format(self._name, status))
            if status == 'completed':
                self._pbar.update(1) # force pbar to be green (ensure 100%, it may be less because use of round)
                timeTook = json_data['timeTook']
                print('timeTook: {} seconds'.format(timeTook))
                data = json_data['data']
                i = 0
                print('RESULT ({} of {} items):'.format(min(MAX_RESULTS, len(data)), len(data)))
                for item in data:
                    i = i + 1
                    result_parsed = item['result']
                    result_pretty = json.dumps(result_parsed, indent=4, sort_keys=True)
                    print('RESULT ITEM {}:'.format(i))
                    print(result_pretty)
                    if i > MAX_RESULTS:
                        return
                        break
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

        stop_url = '{base}/exec/stop'
        stop_body = {
            "jobId": self._jobId,
            "reason": reason
        }
        json_data = json.dumps(stop_body)
        response = requests.post(stop_url, headers=JSON_HEADERS, data=json_data)
        if response.status_code != 200:
            report_request_error(response, 'delete pipeline "{name}"'.format(name=self._name))
            return False
        
        return True

    def get_jsonId(self):
        return self._jobId
