import setuptools
from setuptools import setup
VERSION='1.0.0-dev1'

packages = setuptools.find_packages()

requires = [
    'flask>=0.12.2',
    'pipreqs',
    'tqdm>=4.28.1'

]

with open("README.md", "r") as f:
    long_description = f.read()


setup(name='hkube_notebook',
    version=VERSION,
    description='hkube api for Jupyter Notebook',
    author='Amir Yiron',
    license='MIT',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=packages,
    install_requires=requires,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    zip_safe=False,
)