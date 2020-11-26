#!/bin/bash

PYTHON_VER="3.7"

# ubuntu install dependencies
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python${PYTHON_VER} python${PYTHON_VER}-venv python${PYTHON_VER}-dev

rm -rf venv_sa_conv
python${PYTHON_VER} -m venv venv_sa_conv
source venv_sa_conv/bin/activate

pip install -r requirements.txt
pip install 'git+https://github.com/cocodataset/panopticapi.git'
pip install 'git+https://github.com/philferriere/cocoapi.git#egg=pycocotools&subdirectory=PythonAPI'

pip install -e .
# pip install superannotate

# for testing
pip install pytest pytest-xdist coverage pytest-cov pylint pylint-json2html

# for docs
pip install sphinx sphinx_rtd_theme

# for on PyPI distribution
pip install twine
