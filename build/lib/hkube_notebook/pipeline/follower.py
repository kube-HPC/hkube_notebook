from abc import ABC
from .progress import ProgressHandler
from ..pipeline import JSON_HEADERS
from threading import Thread
import requests
import socket
import random
import time
import json
from .api_utils import report_request_error
from enum import Enum

class FollowerType(Enum):
    LISTENER = 'ListenerFollower',
    POLLER = 'PollFollower'

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
        progress_handler.run(port)

    def prepare(self):
        # actually run flask progress server by thread
        self._progress_handler = ProgressHandler(self._session_map)
        self._flask_thread = Thread(target = ListenerFollower._run_server, args = (self._progress_handler, self._progress_port))
        self._flask_thread.start()

    def follow(self, jobId, pbar, timeout_sec):
        self._session_map[jobId] = {
            'pbar': pbar,
            'sofar': 0
        }
        # wait to finish
        self._flask_thread.join(timeout_sec)
        if self._flask_thread.isAlive():
            print('WARNING: not completed after timeout of {} seconds - killing flask server...'.format(timeout_sec))
            self._progress_handler.shutdown()

    def cleanup(self):
        self._progress_handler.shutdown()


class PollFollower(PipelineFollower):
    """ status polling based pipeline result follower """

    POLL_INTERVAL_SEC = 2

    def __init__(self, api_server_base_url):
        self._base_url = api_server_base_url
    
    def follow(self, jobId, pbar, timeout_sec):
        status_url = '{base}/exec/status/{jobId}'.format(base=self._base_url, jobId=jobId)
        progress = 0
        sofar = 0
        current_milli_time = lambda: int(round(time.time() * 1000))
        start_time = current_milli_time()
        while (current_milli_time() - start_time) < (1000 * timeout_sec):
            time.sleep(PollFollower.POLL_INTERVAL_SEC)
            response = requests.get(status_url, headers=JSON_HEADERS)
            print('status: {}'.format(response.status_code))
            if response.status_code == 200:
                json_data = json.loads(response.text)
                data = json_data['data']
                progress = data['progress']
                adding = int(round(progress - sofar))
                pbar.update(adding)
                sofar = progress
                if progress == 100:
                    break
            else:
                report_request_error(response, 'status request')
        if progress < 100:
            print('WARNING: not completed after timeout of {} seconds...'.format(timeout_sec))

