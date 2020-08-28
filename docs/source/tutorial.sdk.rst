.. _tutorial_sdk:

SDK user guide
===========================

.. contents::

Installation
____________


pip install superannotate


for COCO format converters support need to install:

```console
pip install 'git+https://github.com/cocodataset/panopticapi.git'
pip install 'git+https://github.com/philferriere/cocoapi.git#egg=pycocotools&subdirectory=PythonAPI'
```

The package officially supports Python 3.5+.

Authentication token
____________________

To get the authentication visit team setting for which you want to have SDK
Copy the token to a new JSON file, under the key "token", e.g, your JSON should 
look like this:

{
  "token" : "<your token from superannotate.com>"
}


Initialization
______________

Include the package:

import superannotate as sa

Then initialize it with 

sa.init(<path_to_config_json>)


Working with projects
_____________________

To sear
 
