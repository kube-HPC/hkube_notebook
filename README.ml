# hkube_notebook
This python3 library for Jupyter Notebook enables to integrate with hkube system:
- Algorithms: add, list and delete algorithms.
- Pipelines: Create and store pipelines, get stored pipelines, etc.
- Execution: execute pipeline, track execution status by a progress bar, get the results, etc.
# Intructions for Developer
- Download the hkube project **hkube_notebook**
- Make sure you have python3 and Jupyter Notebook installed (Annaconda is recommended)
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