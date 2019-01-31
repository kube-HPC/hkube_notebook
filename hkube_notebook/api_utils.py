import json

JSON_HEADERS = {'Content-Type': 'application/json'}
FORM_URLENCODED_HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}
FORM_DATA_HEADERS = {'Content-Type': 'multipart/form-data'}

def report_request_error(response, operation):
    json_data = json.loads(response.text)
    if 'error' in json_data:
            error = json_data['error']
            msg = error['message']
    else:
        msg = '<unknown>'
    print('ERROR: {oper} failed: {err} (code: {code})'.format(
        oper=operation, err=msg, code=response.status_code))

def is_success(response):
    return response.status_code >= 200 and response.status_code < 300
