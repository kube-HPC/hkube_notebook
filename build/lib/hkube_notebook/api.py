import json
import logging
import time
from tqdm import tqdm_notebook, tqdm
from flask import Flask, request, abort
from threading import Thread
import requests
import socket

# localhost = socket.gethostbyname(socket.gethostname())
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

# localhost = get_ip_address()
localhost = socket.gethostname()

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

port2info: dict = dict()
    
MAX_RESULTS = 10

def hkube_run_stored_pipeline(name, api_host, api_port, progress_port, input, timeout_sec=10):
    app = Flask('progress_server')
    pbar = tqdm_notebook(total=100)
    progress = '{}:{}'.format(localhost, progress_port)
    port2info[progress] = {
        'pbar': pbar,
        'sofar': 0
    }

    def external_flask_shutdown(port):
        shutdown_url = "http://{host}:{port}/webhook/shutdown".format(host=localhost, port=port)
        try:
            requests.put(shutdown_url)
        except Exception:
            pass
        return
    
    def flask_shutdown():
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        print('shutdown flask...')
        func()
    
    # shutdown handler
    @app.route('/webhook/shutdown', methods=['PUT'])
    def shutdown():
        flask_shutdown()
    
    # progress func
    @app.route('/webhook/progress', methods=['POST'])
    def webhook():
        global port2info
        if request.method == 'POST':
            #print('post')
            # start handling
            try:
                jobId = request.json['jobId']
                #print('1 - {}'.format(jobId))
                address = request.headers['Host']
                #print('2 - {}, address={}'.format(jobId, address))
                entry = port2info[address]
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
                    flask_shutdown()
            except Exception as error:
                print('ERROR in progress webhook: {}'.format(error))
                return '', 200
            return '', 200
        else:
            abort(400)
    
    # flask server func
    def run_flask(app, port):
        print('>>>>> running flask {}:{}'.format(localhost, port))
        app.run(host=localhost, port=port)
        
    # run flask by thread
    flask_thread = Thread(target = run_flask, args = (app, progress_port))
    flask_thread.start()
    
    # prepare pipeline
    base_url = 'http://{host}:{port}/api/v1'.format(host=api_host, port=api_port)
    url = base_url + '/exec/stored'
    data = {
      "name": name,
      "options": {
        "batchTolerance": 100,
        "progressVerbosityLevel": "debug"
      },
      "flowInput": input,
      "webhooks": {
            "progress": "http://{host}:{port}/webhook/progress".format(host=localhost, port=progress_port)
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
        print('Pipeline "{name}" ERROR: {msg}'.format(name=name, msg=msg))
        external_flask_shutdown(progress_port)
        return
        
    jobId = json_data['jobId']
    print('request status={} - pipeline jobId: {}'.format(response.status_code, jobId))
    
    # wait to finish
    flask_thread.join(timeout_sec)
    if flask_thread.isAlive():
        print('WARNING: not completed after timeout of {} seconds - killing flask server...'.format(timeout_sec))
        external_flask_shutdown(progress_port)
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
        print('pipeline "{}" status: {}'.format(name, status))
        if status == 'completed':
            pbar.update(1)
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
                pbar.update(-1)
            except Exception:
                pass
            print('error: {}'.format(json_data['error']))
    else:
        print('Failed to get results for jobId: {}'.format(jobId))
    pbar.close()
    print('<<<<< finished')