import time
import sys
from .engine import do_sort
import pandas as pd
import numpy as np

_input = None


def init(args):
    print('algorithm: init')
    global _input
    _input = args["input"]
    n=1000
    df = pd.DataFrame({'x': np.random.randint(0, 5, size=n),
                       'y': np.random.normal(size=n)})

    print(f'features: {len(df.columns)}')

def start(args):
    print('algorithm: start')
    print('working...')
    time.sleep(5)
    array = _input[0]
    order = _input[1]
    if order == 'asc':
        reverse = False
    elif order == 'desc':
        reverse = True
    else:
        raise Exception('order not supported')

    do_sort(array, reverse=reverse)
    # list.sort(array, reverse=reverse)
    return array


def stop(args):
    print('algorithm: stop')


def exit(args):
    print('algorithm: exit')
    code = args.get('exitCode', 0)
    print('Got exit command. Exiting with code', code)
    sys.exit(code)

# init({'input': [[3,61,89,45,8,23,2], 'asc']})
# print(start({}))