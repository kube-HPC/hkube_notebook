# hkube_notebook
This python3 library for Jupyter Notebook enables to integrate with hkube system:
- create pipelines, store pipelines, get all stored pipelines, etc.
- execute pipelines, track pipeline status by a progress bar, get the results
# Intructions for Developer
- Download the hkube project **hkube_notebook**
- Make sure you have python3 and Jupyter Notebook installed (Annaconda is recommended)
- Make sure python3 is in your path
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
- Also check the example notebook *hkube_notebook.ipynb*
