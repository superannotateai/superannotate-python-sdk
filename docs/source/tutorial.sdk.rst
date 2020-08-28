.. _ref_tutorial:

SDK Tutorial
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
prefix 'Example Project 1' with
:ref:`search_projects <ref_search_projects>`. The return value: :py:obj:`projects`
will be a python list of metadata of found projects. The metadata in
all of SDK are python dicts. In this case project metadata has keys that
identify the project in the platform. E.g. :py:obj:`projects[0]` can be:

.. code-block:: json

   {
       "id" : 111,
       "team_id" : 333,
       "name" : "Example Project 1",
       "....." : "......"
   }

Since the :ref:`sa.search_projects <ref_search_projects>` is not exact, rather prefix
based (this is because the platform allows identically named projects), one
needs to examine the :py:obj:`projects` to identify the looked for project,
e.g.,

.. code-block:: python

   for project in projects:
       if project["description"] == "my desc":
           break

(it is advised to make search prefix unique in the available projects list to be
able to choose the project with just :py:obj:`project = project[0]`)

Now that we have found the project, we can perform various tasks on it. For
example to upload images from a local folder to the project we can do:


.. code-block:: python
    
    sa.upload_images_from_folder_to_project(project, <local_folder_path>)

The first argument to :ref:`sa.upload_images_from_folder_to_project <ref_upload_images_from_folder_to_project>` is the metadata of the project which contains
all the information to identify the project on the platform.

For full list of available functions on projects, see :ref:`ref_projects`


Working with images
_____________________

To search for the images in the project:

.. code-block:: python

   images = sa.search_images("example_image1.jpg")

Here again we get python list of dict metadata for the images with name prefix
'example_image1.jpg'.
