#!/bin/bash

python -m venv venv_sa_conv
source venv_sa_conv/bin/activate
pip install numpy # this is to avoid pycocotools incorrect dependency resolution issue
pip install -r requirements.txt
