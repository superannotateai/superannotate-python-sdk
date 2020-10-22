#!/bin/bash

# sudo add-apt-repository ppa:deadsnakes/ppa
# sudo apt update
# sudo apt install python3.6 python3.6-venv

rm -rf venv_sa_conv
python3.6 -m venv venv_sa_conv
source venv_sa_conv/bin/activate
pip install numpy # this is to avoid pycocotools incorrect dependency resolution issue
pip install -r requirements.txt
