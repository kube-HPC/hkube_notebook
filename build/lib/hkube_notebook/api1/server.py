import json
import logging
import time
from tqdm import tqdm_notebook, tqdm
from flask import Flask, request, abort
from threading import Thread
import requests
import socket
import random

class ProgressHandler(object):
    """ Manage flask server for handling progress messages """

    def __init__(self, session_map: dict):
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        self._app = Flask('progress_server')
        self._port = 0
        self._host = socket.gethostname()
        self._session_map = session_map

            # shutdown handler
        @self._app.route('/webhook/shutdown', methods=['PUT'])
        def shutdown():
            self._shutdown()
        
        # progress func
        @self._app.route('/webhook/progress', methods=['POST'])
        def webhook():
            if request.method == 'POST':
                #print('post')
                # start handling
                try:
                    # jobId = request.json['jobId']
                    #print('1 - {}'.format(jobId))
                    address = request.headers['Host']
                    #print('2 - {}, address={}'.format(jobId, address))
                    entry = self._session_map[address]
                    mypbar = entry['pbar']
                    mysofar = entry['sofar']
                    #print('3 - {}, mysofar={}'.format(jobId, mysofar))
                    if not 'data' in request.json.keys():
                        return '', 200
                    data = request.json['data']
                    #print(data)
                    progress = data['progress']
                    details = data['details']
                    adding = int(round(progress - mysofar))
                    #print('####### progress={}, adding={}, mysofar={} #######'.format(progress, adding, mysofar))
                    #mypbar.set_description(desc=details)
                    mypbar.set_postfix(kwargs=details)
                    mypbar.update(adding)
                    entry['sofar'] = progress
                    if progress >= 100:
                        #mypbar.close()
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
        self._app.run(host=self._host, port=self._port)   
    
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
            requests.put(shutdown_url)
        except Exception:
            pass
        return