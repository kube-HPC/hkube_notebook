from hkube_notebook.algorithm.manager import AlgorithmBuilder
from hkube_notebook.config import config
import os
# test create alg code
def stam(args):
    print("stam")
    return 42

def bar(args):
    print("bar")
    return 54

api_server = '{0}/hkube/api-server/api/v1'.format(config.api['base_url'])
alg_mgr = AlgorithmBuilder(api_server)
alg_list = alg_mgr.get_all()

# a self contained function
def my_start(args):
    import numpy as np
    import pandas as pd
    import time
    n = 1000
    df = pd.DataFrame({'x': np.random.randint(0, 5, size=n), 'y': np.random.normal(size=n)})
    print('COLUMNS', df.columns)

    input = args["input"]
    print(f'algorithm: start, input: {input}')
    print('working...')
    time.sleep(5)
    array = input[0]
    order = input[1]
    if order == 'asc':
        reverse = False
    elif order == 'desc':
        reverse = True
    else:
        raise Exception('order not supported')

    list.sort(array, reverse=reverse)
    return array

# create compressed alg by given implementation functions
entryfile, tarfilename = alg_mgr.create_algfile_by_functions(my_start)
config = alg_mgr.create_config('sort-alg', entryfile)
alg_mgr.apply(compressed_alg_file=tarfilename, config=config)

# create compressed alg by given alg folder
folder = 'hkube_notebook/test/test_algorithm'
tarfilename = alg_mgr.create_algfile_by_folder(folder)
config = alg_mgr.create_config('test-alg', 'main.py')
alg_mgr.apply(compressed_alg_file=tarfilename, config=config)
