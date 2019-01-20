import json

def report_request_error(response, operation):
    json_data = json.loads(response.text)
    if 'error' in json_data:
            error = json_data['error']
            msg = error['message']
    else:
        msg = '<unknown>'
    print('ERROR: {oper} failed: {err} (code: {code})'.format(
        oper=operation, err=msg, code=response.status_code))