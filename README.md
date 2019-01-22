# hkube_notebook
This python3 library for Jupyter Notebook enables to integrate with hkube system:
- Algorithms: add, list and delete algorithms.
- Pipelines: Create and store pipelines, get stored pipelines, etc.
- Execution: execute pipeline, track execution status by a progress bar, get the results, etc.
# Intructions for Developer
- Download the hkube project **hkube_notebook**
- Make sure you have python3 and Jupyter Notebook installed (Anaconda is recommended)
- Make sure python3 is in your path
- Update pip3 and install dependecies:
```sh
$ python3 -m pip install --upgrade pip
$ python3 -m pip install flask=0.12.2
$ python3 -m pip install tqdm=4.28.1
```
- Install the library using the following shell commands (notice that library version is taken from setup.py):
```sh
$ cd hkube_notebook
$ python3 setup.py develop
$ # make sure hkube_notebook is installed
$ python3 -m pip list | grep hkube
```
- Run Jupyter Notebook server, open a new python session, import the library and start work
```python
import hkube_notebook
```
- Example and test notebook: *hkube_notebook.ipynb*
- Tested: Python 3.6.8 from Anaconda
# Upload package to python registry
See: https://packaging.python.org/tutorials/packaging-projects/
- Install/update tools:
```sh
$ python3 -m pip install --user --upgrade setuptools wheel
$ python3 -m pip install --user --upgrade twine
```
- Create account for python test registry at: https://test.pypi.org/account/register/
- Create distribution and upload it to test registry:
```sh
$ # create a 'dist' diectory with whl and gz files:
$ python3 setup.py sdist bdist_wheel
$ # upload to test registry:
$ twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```
# Install package in user python3 env
- In user python environment:
```sh
$ python3 -m pip install --index-url https://test.pypi.org/simple/ hkube_notebook
$ # now install missing dependency packages...
```


