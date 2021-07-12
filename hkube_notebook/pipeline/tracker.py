from abc import ABC
from .progress import ProgressHandler
from tqdm.autonotebook import tqdm
from threading import Thread
import requests
import socket
import random
import time
import json
from ..api_utils import report_request_error, is_success, JSON_HEADERS
from enum import Enum

class TrackerType(Enum):
    LISTENER = 'ListenerTracker',
    POLLING = 'PollingTracker'

class PipelineTracker(ABC):
    """ pipeline result tracker base class """

    def prepare(self):
        pass
    
    def follow(self, jobId, timeout_sec):
        pass

    def cleanup(self):
        pass

    @classmethod
    def updatePbarByStatus(cls, pbar, status):
        if status == 'failed':
            pbar.update(-1) # force pbar to be red
        return status in ['completed', 'failed', 'stopped']


class ListenerTracker(PipelineTracker):
    """ webhook based pipeline result tracker """

    def __init__(self, executor, name, progress_port):
        # mapping: progress_address => (progress_bar, sofar)
        self._executor = executor
        self._session_map = dict()
        self._progress_port = progress_port
        self._pbar = tqdm(total=100)   # create new pregress bar
        self._pbar.set_description(desc=name)
        self._jobId = None


    # flask server func
    @classmethod
    def _run_server(cls, listener_tracker):
        listener_tracker._progress_handler.run(listener_tracker._progress_port)
        print('ListenerTracker thread finished. jobId: {}'.format(listener_tracker._jobId))
        listener_tracker.cleanup()

    def prepare(self):
        # actually run flask progress server by thread
        self._progress_handler = ProgressHandler(self._session_map, PipelineTracker)
        self._flask_thread = Thread(target = ListenerTracker._run_server, args = (self,))
        self._flask_thread.start()

    def follow(self, jobId, timeout_sec):
        self._jobId = jobId
        self._session_map[jobId] = {
            'pbar': self._pbar,
            'sofar': 0,
            'calculated': 0
        }

        # wait to finish
        if timeout_sec is not 0:
            self._flask_thread.join(timeout_sec)
            if self._flask_thread.is_alive() and timeout_sec is not None and timeout_sec > 0:
                print('WARNING: not completed after timeout of {} seconds - killing flask server...'.format(timeout_sec))
                self.cleanup()

    def cleanup(self):
        self._progress_handler.shutdown()
        self._executor.clean_tracker(self._jobId)


class PollingTracker(PipelineTracker):
    """ status polling based pipeline result tracker """

    POLL_INTERVAL_SEC = 1

    def __init__(self, executor, name):
        self._executor = executor
        self._stop = False
        self._pbar = tqdm(total=100)   # create new pregress bar
        self._pbar.set_description(desc=name)
        self._jobId = None

    @classmethod
    def _status_tracker(cls, tracker):
        """ Polling tracker function """
        progress = 0
        sofar = 0
        calculated_sofar = 0
        current_milli_time = lambda: int(round(time.time() * 1000))
        start_time = current_milli_time()
        while (not tracker.is_stopping()) and ((tracker._timeout_sec is None) or 
                (tracker._timeout_sec == 0) or ((current_milli_time() - start_time) < (1000 * tracker._timeout_sec))):
            time.sleep(PollingTracker.POLL_INTERVAL_SEC)
            json_data = tracker._executor._get_status(jobId=tracker._jobId)
            if json_data is not None:
                if not 'data' in json_data.keys():
                    continue
                data = json_data['data']
                status = json_data['status']
                progress = data['progress']
                details = data['details']
                adding = int(round(progress - sofar))
                tracker._pbar.set_postfix(kwargs=details)
                tracker._pbar.update(adding)
                calculated_sofar += adding
                sofar = progress
                if progress >= 100:
                    if (calculated_sofar < 100):
                        # fix pbar to 100% (may be less as we use 'round' to add only integers)
                        tracker._pbar.update(100 - calculated_sofar)
                        tracker._pbar.close()
                    break
                if PipelineTracker.updatePbarByStatus(pbar=tracker._pbar, status=status):
                    tracker._pbar.close()
                    break
        if progress < 100 and tracker._timeout_sec is not None and tracker._timeout_sec > 0:
            print('WARNING: not completed after timeout of {} seconds...'.format(tracker._timeout_sec))
        print('PollingTracker thread finished, jobId: {}'.format(tracker._jobId))


    def follow(self, jobId, timeout_sec):
        self._jobId = jobId
        self._timeout_sec = timeout_sec
        # run status tracker thread
        self._status_thread = Thread(target = PollingTracker._status_tracker, args = (self,))
        self._status_thread.start()
        # wait to finish
        if timeout_sec is not 0:
            self._status_thread.join(timeout_sec)
            if self._status_thread.isAlive() and timeout_sec is not None:
                print('WARNING: not completed after timeout of {} seconds - killing status server...'.format(timeout_sec))
                self.cleanup()


    def cleanup(self):
        self._stop = True
        self._executor.clean_tracker(self._jobId)

    def is_stopping(self):
        return self._stop