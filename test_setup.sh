#!/bin/bash

TEST_ENV=test_sa_env

rm -rf "$TEST_ENV"
python3 -m venv "$TEST_ENV"
source "$TEST_ENV"/bin/activate

pip install -e .
pip install 'git+https://github.com/cocodataset/panopticapi.git'
pip install 'git+https://github.com/philferriere/cocoapi.git#egg=pycocotools&subdirectory=PythonAPI'
