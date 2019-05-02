import setuptools
from hkube_notebook.version import __version__
from setuptools import setup
exec(open('hkube_notebook/version.py').read())
setup(name='hkube_notebook',
    version=__version__,
    description='hkube api for Jupyter Notebook',
    author='Amir Yiron',
    license='MIT',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    zip_safe=False,
)