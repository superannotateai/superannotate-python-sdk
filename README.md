# Documentation

## Installation

    pip install --user superannotate

    # for COCO format converters
    pip install --user 'git+https://github.com/cocodataset/panopticapi.git'
    pip install --user 'git+https://github.com/philferriere/cocoapi.git#egg=pycocotools&subdirectory=PythonAPI'


## Python SDK

With Python SDK you can perform various tasks on SuperAnnotate platform, such as uploading images,
exporting annotations, assigning image to a team contributor using locally written Python scripts.

First follow the installation above. To start using Python SDK import
superannotate module

    import superannotate as sa

[Python SDK](README_sdk.md)

