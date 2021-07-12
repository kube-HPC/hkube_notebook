import os

def getIntEnv(name, defaultValue):
    strValue = os.environ.get(name, defaultValue)
    return int(strValue)


def getBoolEnv(name, defaultValue):
    strValue = os.environ.get(name, defaultValue)
    return strValue.lower() == 'true'


api = {
    "base_url": os.environ.get('API_BASE_URL', 'http://api-server:3000'),
    "verify_ssl": getBoolEnv('API_VERIFY_SSL', 'True'),
}
logging = {
    "level": os.environ.get('HKUBE_LOG_LEVEL', "INFO")
}
