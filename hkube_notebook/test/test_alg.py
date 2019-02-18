from hkube_notebook.algorithm.manager import AlgorithmBuilder

# test create alg code
def stam(args):
    print("stam")
    return 42

def bar(args):
    print("bar")
    return 54

api_server = 'http://localhost:3000/api/v1'
#api_server = 'https://10.32.10.19/hkube/api-server/api/v1'
alg_mgr = AlgorithmBuilder(api_server)
alg_list = alg_mgr.get_all()

# create compressed alg by given implementation functions
# entryfile, tarfilename = alg_mgr.create_algfile_by_functions(bar, stam, bar, stam)
# config = alg_mgr.create_config('amir-alg', entryfile)
# alg_mgr.apply(compressed_alg_file=tarfilename, config=config)

# create compressed alg by given alg folder
folder = 'hkube_notebook/test/test_algorithm'
tarfilename = alg_mgr.create_algfile_by_folder(folder)
config = alg_mgr.create_config('test-alg', 'main.py')
alg_mgr.apply(compressed_alg_file=tarfilename, config=config)


# alg_file = '/home/amiryi/dev/hkube/Algorithm/python-sort-alg/algorithm.py.tar.gz'
# alg_config = {
#        "name": "sort-alg",
#        "env": "python",
#        "code": {
#            "entryPoint": entryfile
#        },
#        "algorithmImage": "hkube/sort-alg",
#        "cpu": 0.1,
#        "mem": "512Mi",
#        "algorithmEnv": {
#            "ENV1": "bla-bla",
#            "ENV2": "bla-bla"
#        },
#        "workerEnv": {
#            "ENV1": "bla-bla",
#            "ENV2": "bla-bla"
#        },
#        "minHotWorkers": 0,
#        "userInfo": {
#            "platform": "linux",
#            "hostname": "ubuntu-amiryi-ww",
#            "username": "amiryi"
#        }
#    }
# AlgorithmManager.apply(api_server, alg_file=tarfilename, config=alg_config)

