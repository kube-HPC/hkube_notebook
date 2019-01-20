import json
import logging
import time
from tqdm import tqdm_notebook, tqdm
from flask import Flask, request, abort
from threading import Thread
import requests
import socket
import random
from .server import ProgressHandler

MAX_RESULTS = 10

class PipelineManager(object):
    """ Manages an Hkube Pipeline (create, run, follow status, etc.) """

    def __init__(self, name):
        self._name = name # pipeline name
        # mapping: progress_address => (progress_bar, sofar)
        self._session_map = dict()
        self._pbar = tqdm_notebook(total=100)   # pregress bar
        self._progress_handler = ProgressHandler(self._session_map)
        self._flask_thread = None

    # flask server func
    @classmethod
    def _run_server(cls, progress_handler, port):
        progress_handler.run(port)


    def exec(self, api_host, api_port, input={}, timeout_sec=10, progress_port=0):
        """ 
        Execute the pipeline, follow progress and report results 

        :param api_host hkube api-server host
        :param api_port hkube api-server port
        :param input pipeline input
        :param timeout_sec max estimated pipeline execution time (stop execution after timeout)
        :param progress_port port to listen to progress messages
        """

        # prepare
        if progress_port == 0:
            progress_port = random.randint(50001, 59999)
        progress_entry = '{}:{}'.format(socket.gethostname(), progress_port)
        self._session_map[progress_entry] = {
            'pbar': self._pbar,
            'sofar': 0
        }

        # run flask by thread
        self._flask_thread = Thread(target = PipelineManager._run_server, args = (self._progress_handler, progress_port))
        self._flask_thread.start()
        
        # prepare pipeline
        base_url = 'http://{host}:{port}/api/v1'.format(host=api_host, port=api_port)
        url = base_url + '/exec/stored'
        data = {
        "name": self._name,
        "options": {
            "batchTolerance": 100,
            "progressVerbosityLevel": "debug"
        },
        "flowInput": input,
        "webhooks": {
                "progress": "http://{host}:{port}/webhook/progress".format(host=socket.gethostname(), port=progress_port)
        }
        }
        json_data = json.dumps(data)
        
        # run pipeline
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, data=json_data)
        #print(response)
        json_data = json.loads(response.text)
        if 'error' in json_data:
            error = json_data['error']
            msg = error['message']
            print('Pipeline "{name}" ERROR: {msg}'.format(name=self._name, msg=msg))
            self._progress_handler.shutdown()
            return
            
        jobId = json_data['jobId']
        print('request status={} - pipeline jobId: {}'.format(response.status_code, jobId))
        
        # wait to finish
        self._flask_thread.join(timeout_sec)
        if self._flask_thread.isAlive():
            print('WARNING: not completed after timeout of {} seconds - killing flask server...'.format(timeout_sec))
            self._progress_handler.shutdown()
            return
            
        # get results
        print("getting results...")
        result_url = base_url + '/exec/results/' + jobId
        time.sleep(1)
        response = requests.get(result_url, headers=headers)
        print('result status: {}'.format(response.status_code))
        if response.status_code == 200:
            json_data = json.loads(response.text)
            status = json_data['status']
            print('pipeline "{}" status: {}'.format(self._name, status))
            if status == 'completed':
                self._pbar.update(1)
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
                        break
            elif status == 'failed':
                try:
                    self._pbar.update(-1)
                except Exception:
                    pass
                print('error: {}'.format(json_data['error']))
        else:
            print('Failed to get results for jobId: {}'.format(jobId))
        self._pbar.close()
        print('<<<<< finished')