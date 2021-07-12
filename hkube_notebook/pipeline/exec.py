import json
import logging
import time
from flask import Flask, request, abort
from threading import Thread
import requests
import socket
import random
from .progress import ProgressHandler
from .tracker import TrackerType, ListenerTracker, PollingTracker
from ..api_utils import report_request_error, is_success, JSON_HEADERS
from hkube_notebook.config import config, utils

MAX_RESULTS = 10

class PipelineExecutor(object):
    """ Manages an Hkube Pipeline execution (exec, run, track status, get results, stop, etc.) """

    def __init__(self, name=None, raw=None, tracker=TrackerType.LISTENER, first_progress_port=0, options={}):
        """ 
        :param name pipeline name, optional - for stored pipeline
        :param raw raw pipeline object, optional - for raw pipeline (overides name if given)
        :param api_server_base_url includes protocol, host, port, base path
        :param tracker pipeline tracking method: listener or polling
        :param first_progress_port first port for listening to progress messages (optional with default for listener tracker only)
        """
        if name is None and raw is None:
            raise Exception('ERROR: nor stored pipeline "name" nor "raw" pipeline is given!')

        # pipeline name
        self._raw = raw
        if raw:
            self._name = raw['name']    
        else:
            self._name = name
        self._options=options
        self._base_url = utils.api_server_url(options)
        self._tracker_type = tracker
        self._trackers = dict()
        if first_progress_port == 0:
            first_progress_port = random.randint(50000, 59999)
        self._progress_port = first_progress_port
        

    def _create_tracker(self):
        if self._tracker_type is TrackerType.LISTENER:
            self._progress_port += 1    # avoid port collision
            tracker = ListenerTracker(name=self._name, executor=self, progress_port=self._progress_port)
        else:
            tracker = PollingTracker(name=self._name, executor=self)
        return tracker

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
        if self._tracker_type is TrackerType.LISTENER:
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
        tracker = self._create_tracker()
        tracker.prepare()
        
        # run pipeline
        body = self._get_exec_body(input)
        exec_url = self._get_exec_url()
        json_data = json.dumps(body)
        response = requests.post(exec_url, headers=JSON_HEADERS, data=json_data, verify=config.api['verify_ssl'])
        if not is_success(response):
            report_request_error(response, 'exec pipeline "{name}"'.format(name=self._name))
            tracker.cleanup()
            return None, None

        resp_body = json.loads(response.text)
        jobId = resp_body['jobId']
        print('OK - pipeline is running, jobId: {}'.format(jobId))
        return jobId, tracker


    def exec_async(self, input={}):
        """ 
        Execute the pipeline asynchronously (return immediately); progress bar still displays progress

        :param input pipeline input
        :return: jobId
        """
        # execute
        jobId, tracker = self._exec(input)
        if jobId is None or tracker is None:
            return None
        self._trackers[jobId] = tracker
        # wait to finish
        tracker.follow(jobId=jobId, timeout_sec=0)
        return jobId


    def exec(self, input={}, timeout_sec=None, max_displayed_results=MAX_RESULTS):
        """ 
        Execute the pipeline, track progress and report results 

        :param input pipeline input
        :param timeout_sec time to track progress before return (None: return upon completion/fail/stopped)
        :param max_displayed_results max number of results to display (if 0 don't display results)
        :return: list of results
        """
        # execute
        jobId, tracker = self._exec(input)        
        if jobId is None or tracker is None:
            return None
        self._trackers[jobId] = tracker       
        # wait to finish
        tracker.follow(jobId=jobId, timeout_sec=timeout_sec)

        # get results
        results = self.get_results(jobId=jobId, max_display=max_displayed_results)
        # self._pbar.close()
        print('<<<<< finished')
        return results

    def get_results(self, jobId, max_display=0):
        """ Get results for a pipeline job """
        if jobId is None:
            print('ERROR: no valid jobId')
            return

        print("getting results...")
        result_url = self._base_url + '/exec/results/' + jobId
        time.sleep(1)
        response = requests.get(result_url, headers=JSON_HEADERS, verify=config.api['verify_ssl'])
        # print('result status: {}'.format(response.status_code))
        if is_success(response):
            json_data = json.loads(response.text)
            status = json_data['status']
            name = json_data['pipeline']
            print('pipeline "{}" status: {}'.format(name, status))
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
                return list()
        else:
            report_request_error(response, 
                'get results for jobId {jobid}'.format(jobid=jobId))
            return list()

    def stop(self, jobId, reason='stop in jupyter notebook'):
        """ Stop pipeline of jobId """
        if jobId is None:
            print('ERROR: cannot stop - no jobId!')
            return False

        stop_url = '{base}/exec/stop'.format(base=self._base_url)
        stop_body = {
            "jobId": jobId,
            "reason": reason
        }
        json_data = json.dumps(stop_body)
        response = requests.post(stop_url, headers=JSON_HEADERS, data=json_data, verify=config.api['verify_ssl'])
        if not is_success(response):
            report_request_error(response, 'delete pipeline "{name}"'.format(name=self._name))
            return False
        else:
            print('OK - pipeline "{name}" stopped, jobId: {jobId}'.format(name=self._name, jobId=jobId))
        self.cleanup()
        return True

    def clean_tracker(self, jobId):
        if jobId is None:
            return
        if jobId in self._trackers.keys():
            del self._trackers[jobId]

    def cleanup(self):
        """ Clean all trackers """
        # print('<<Executor-Cleanup>>')
        self._trackers.clear()
    
    def get_all_status(self):
        """ Get status of all active pipeline jobs that were staring here """
        status_list = list()
        if len(self._trackers.keys()) == 0:
            print('executor has no active jobs')
            return status_list
        for jobId in self._trackers.keys():
            status_info = PipelineExecutor.get_status(options=self._options, jobId=jobId)
            status_list.append(status_info)
            status = status_info['status']
            data = status_info['data']
            details = data['details']
            print('jobId {jobId}: {status} - {details}'.format(
                jobId=jobId, status=status, details=details
            ))
        return status_list
            
    def _get_status(self, jobId):
        return PipelineExecutor.get_status(options=self._options, jobId=jobId)


    @classmethod
    def get_status(cls, options, jobId):
        """ Get status of given jobId """
        status_url = '{base}/exec/status/{jobId}'.format(base=utils.api_server_url(options), jobId=jobId)
        response = requests.get(status_url, headers=JSON_HEADERS, verify=config.api['verify_ssl'])
        if not is_success(response):
            report_request_error(response, 'status request for {}'.format(jobId))
            return None
        return json.loads(response.text)


    @classmethod
    def get_all_stored(cls, options):
        """ Get all stored pipelines """
        pipelines_url = '{base}/store/pipelines'.format(base=utils.api_server_url(options))
        response = requests.get(pipelines_url, verify=config.api['verify_ssl'])
        if not is_success(response):
            report_request_error(response, 'get stored pipelines')
            return list()
        
        json_data = json.loads(response.text)
        pipelines_names = list(map(lambda pipeline: pipeline['name'], json_data))
        print("Got {num} stored pipelines: {names}".format(num=len(json_data), names=pipelines_names))
        return json_data

    @classmethod
    def get_running_jobs(cls, options):
        """ Get all running pipeline jobs """
        pipelines_url = '{base}/exec/pipeline/list'.format(base=utils.api_server_url(options))
        response = requests.get(pipelines_url, verify=config.api['verify_ssl'])
        if not is_success(response):
            report_request_error(response, 'get running pipelines')
            return list()
        
        json_data = json.loads(response.text)
        pipelines_jobs = list(map(lambda pipeline: pipeline['jobId'], json_data))
        print("Got {num} running jobs:".format(num=len(json_data)))
        for job in pipelines_jobs:
            print(job)
        return json_data