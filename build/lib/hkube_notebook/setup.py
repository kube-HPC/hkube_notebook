import setuptools
from setuptools import setup

setup(name='hkube_notebook',
    version='0.2',
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