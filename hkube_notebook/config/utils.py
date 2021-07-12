from hkube_notebook.config import config
def api_server_url(options={}):
    base_url = options.get('base_url',config.api['base_url'])
    path = options.get('path',config.api['path'])
    return '{0}/{1}'.format(base_url,path)