.. _tutorial_sdk:

SDK user guide
===========================

.. contents::

Installation
____________


.. code-block:: bash

   pip install superannotate


for COCO format converters support need to install:

.. code-block:: bash

   pip install 'git+https://github.com/cocodataset/panopticapi.git'
   pip install 'git+https://github.com/philferriere/cocoapi.git#egg=pycocotools&subdirectory=PythonAPI'

The package officially supports Python 3.5+.

Authentication token
____________________

To get the authentication visit team setting for which you want to have SDK
Copy the token to a new JSON file, under the key "token", e.g, your JSON should
look like this:

.. code-block:: json

   {
     "token" : "<your token from superannotate.com>"
   }


Initialization
______________

Include the package:

.. code-block:: python

   import superannotate as sa

Then initialize it with the config file created in the previous step:

.. code-block:: python

   sa.init(<path_to_config_json>)


Working with projects
_____________________

To search for the projects you can run:


.. code-block:: python

   projects = sa.search_projects("Example Project 1")

Here a search through all the team's projects will be performed with name 
prefix 'Example Project 1'.
:ref:`sa.search_projects <search_projects>`. :py:varprojects always returns a python list of all
found projects. S 

