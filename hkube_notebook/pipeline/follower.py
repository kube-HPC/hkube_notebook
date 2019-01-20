from abc import ABC
from .progress import ProgressHandler
from threading import Thread
import requests
import socket
import random
import time
import json
from ..api_utils import report_request_error, is_success, JSON_HEADERS
from enum import Enum

class FollowerType(Enum):
    LISTENER = 'ListenerFollower',
    POLLING = 'PollFollower'

class PipelineFollower(ABC):
    """ pipeline result follower base class """

    def prepare(self):
        pass
    
    def follow(self, jobId, pbar, timeout_sec):
        pass

    def cleanup(self):
        pass


class ListenerFollower(PipelineFollower):
    """ webhook based pipeline result follower """

    def __init__(self, progress_port):
        # mapping: progress_address => (progress_bar, sofar)
        self._session_map = dict()
        self._progress_port = progress_port

    # flask server func
    @classmethod
    def _run_server(cls, progress_handler, port):
        return progress_handler.run(port)

    def prepare(self):
        # actually run flask progress server by thread
        self._progress_handler = ProgressHandler(self._session_map)
        self._flask_thread = Thread(target = ListenerFollower._run_server, args = (self._progress_handler, self._progress_port))
        self._flask_thread.start()

    def follow(self, jobId, pbar, timeout_sec):
        self._session_map[jobId] = {
            'pbar': pbar,
            'sofar': 0,
            'calculated': 0
        }

        # wait to finish
        if timeout_sec is not 0:
            self._flask_thread.join(timeout_sec)
            if self._flask_thread.isAlive() and timeout_sec is not None:
                print('WARNING: not completed after timeout of {} seconds - killing flask server...'.format(timeout_sec))
                self._progress_handler.shutdown()

    def cleanup(self):
        self._progress_handler.shutdown()


class PollFollower(PipelineFollower):
    """ status polling based pipeline result follower """

    POLL_INTERVAL_SEC = 1

    def __init__(self, api_server_base_url):
        self._base_url = api_server_base_url
    
    def follow(self, jobId, pbar, timeout_sec):
        if timeout_sec is not None and timeout_sec <= 0:
            return
        status_url = '{base}/exec/status/{jobId}'.format(base=self._base_url, jobId=jobId)
        progress = 0
        sofar = 0
        calculated_sofar = 0
        current_milli_time = lambda: int(round(time.time() * 1000))
        start_time = current_milli_time()
        while (timeout_sec == None) or ((current_milli_time() - start_time) < (1000 * timeout_sec)):
            time.sleep(PollFollower.POLL_INTERVAL_SEC)
            response = requests.get(status_url, headers=JSON_HEADERS)
            # print('status: {}'.format(response.status_code))
            if is_success(response):
                json_data = json.loads(response.text)
                data = json_data['data']
                progress = data['progress']
                details = data['details']
                adding = int(round(progress - sofar))
                pbar.set_postfix(kwargs=details)
                pbar.update(adding)
                calculated_sofar += adding
                sofar = progress
                if progress >= 100:
                    if (calculated_sofar < 100):
                        # fix pbar to 100% (may be less as we use 'round' to add only integers)
                        pbar.update(100 - calculated_sofar)
                    break
            else:
                report_request_error(response, 'status request')
        if progress < 100 and timeout_sec is not None:
            print('WARNING: not completed after timeout of {} seconds...'.format(timeout_sec))

