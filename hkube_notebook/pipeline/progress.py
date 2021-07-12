import json
import logging
import time
from flask import Flask, request, abort
from threading import Thread
import requests
import socket
import random
from hkube_notebook.config import config

class ProgressHandler(object):
    """ Manage flask server for handling progress messages """

    def __init__(self, session_map: dict, trackerClass):
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        self._app = Flask('progress_server')
        self._port = 0
        self._host = socket.gethostname()
        self._session_map = session_map
        self._trackerClass = trackerClass

            # shutdown handler
        @self._app.route('/webhook/shutdown', methods=['PUT'])
        def shutdown():
            self._shutdown()
            return '', 200
        
        # progress func
        @self._app.route('/webhook/progress', methods=['POST'])
        def webhook():
            if request.method == 'POST':
                # start handling
                try:
                    req_data = json.loads(request.data)
                    jobId = req_data['jobId']
                    if jobId not in self._session_map:
                        print('WARNING: webhook/progress unknown jobId')
                        return '', 200
                    status = req_data['status']
                    entry = self._session_map[jobId]
                    mypbar = entry['pbar']
                    mysofar = entry['sofar']
                    #print('3 - {}, mysofar={}'.format(jobId, mysofar))
                    #print(data)
                    if not 'data' in request.json.keys():
                        return '', 200
                    data = request.json['data']
                    progress = data['progress']
                    details = data['details']
                    adding = int(round(progress - mysofar))
                    entry['calculated'] += adding
                    # print('####### progress={}, adding={}, mysofar={} #######'.format(progress, adding, mysofar))
                    mypbar.set_postfix(kwargs=details)
                    mypbar.update(adding)
                    entry['sofar'] = progress
                    if progress >= 100:
                        if (entry['calculated'] < 100):
                            # fix pbar to 100% (may be less as we use 'round' to add only integers)
                            adding = 100 - entry['calculated']
                            mypbar.update(100 - entry['calculated'])
                            entry['calculated'] += adding
                    if self._trackerClass.updatePbarByStatus(pbar=mypbar, status=status):
                        mypbar.close()
                        self._shutdown()
                    
                except Exception as error:
                    print('ERROR in progress webhook: {}'.format(error))
                    return '', 200
                return '', 200
            else:
                abort(400)


    def run(self, port):
        """ run flask server """
        self._port = port
        print('>>>>> running flask {}:{}'.format(self._host, self._port))
        try:
            self._app.run(host=self._host, port=self._port)
            print('flask server ended')
            return True
        except Exception as error:
            print('ERROR: failed to run progress webhook on port {port}: {err}'.format(port=port, err=error))
            return False

    
    def _shutdown(self):
        """ Internal server shutdown """
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        print('shutdown flask server...')
        func()

    def shutdown(self):
        """ External shutdown of the server """
        shutdown_url = "http://{host}:{port}/webhook/shutdown".format(host=self._host, port=self._port)
        try:
            requests.put(shutdown_url, verify=config.api['verify_ssl'])
        except Exception:
            pass
        return