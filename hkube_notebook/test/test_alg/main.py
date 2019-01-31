import time
import sys
# from .engine import do_sort
import dask.dataframe as dd

_input = None


def init(args):
    print('algorithm: init')
    global _input
    _input = args["input"]
    _df = dd.read_csv('data.csv')

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

    # do_sort(array, reverse=reverse)
    list.sort(array, reverse=reverse)
    return array


def stop(args):
    print('algorithm: stop')


def exit(args):
    print('algorithm: exit')
    code = args.get('exitCode', 0)
    print('Got exit command. Exiting with code', code)
    sys.exit(code)
