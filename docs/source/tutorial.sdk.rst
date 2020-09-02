.. _ref_tutorial:

SDK Tutorial
===========================

.. contents::

Installation
____________


SDK is available on PyPI:

.. code-block:: bash

   pip install superannotate

for COCO annotation format converters support also need to install:

.. code-block:: bash

   pip install 'git+https://github.com/cocodataset/panopticapi.git'
   pip install 'git+https://github.com/philferriere/cocoapi.git#egg=pycocotools&subdirectory=PythonAPI'

The package officially supports Python 3.5+.

Authentication token
____________________

SDK authentication tokens are team specific. They are available to team admins on
team setting page at https://annotate.online/team. Generate then copy the token from
that page to a new JSON file, under the key "token":

.. code-block:: json

   {
     "token" : "<team token>"
   }


Initialization and authorization
________________________________

Include the package:

.. code-block:: python

   import superannotate as sa

Initialize and authenticate SDK with the config file created in the previous step:

.. code-block:: python

   sa.init("<path_to_config_json>")


Working with projects
_____________________

To search for the projects you can run:


.. code-block:: python

   projects = sa.search_projects("Example Project 1")

Here a search through all the team's projects will be performed with name
prefix "Example Project 1". Full documentation of the function can be found at 
:ref:`search_projects <ref_search_projects>`. The return value: :py:obj:`projects`
will be a Python list of metadata of found projects. We can choose the first result 
as our project for further work:

.. code-block:: python

   project = projects[0]

.. note::

   The metadata of SDK objects, i.e., projects, exports, images, annotation 
   classes, users, are Python dicts.
   In this case project metadata has keys that identify the project in the
   platform. 

   For more information please look at :ref:`ref_metadata`.

.. warning::

   Since the :ref:`sa.search_projects <ref_search_projects>` searches projects with prefix
   based (this is because the platform allows identically named projects), one
   needs to examine the :py:obj:`projects` to identify the looked for project,
   e.g.,

   .. code-block:: python

      for project in projects:
          if project["description"] == "my desc":
              break

   It is advised to make search prefix unique in the available projects list to be
   able to choose the project with just :py:obj:`project = project[0]`.

Now that we have found the project, we can perform various tasks on it. For
example, to upload images from a local folder to the project:


.. code-block:: python

    sa.upload_images_from_folder_to_project(project, "<local_folder_path>")

which will upload all images with extensions "jpg" or "png" from the
:file:`"<local_folder_path>"` to the project. See the full argument options for
:py:func:`upload_images_from_folder_to_project` :ref:`here <ref_upload_images_from_folder_to_project>`.

For full list of available functions on projects, see :ref:`ref_projects`.


Working with annotation classes
_______________________________________________

An annotation class for a project can be created with SDK's:

.. code-block:: python

   sa.create_annotation_class(project, "Large car", color="#FFFFAA")


To create annotation classes in bulk with SuperAnnotate export format 
:file:`classes.json` (documentation at:
https://annotate.online/documentation Management Tools
-> Project Workflow part): 

.. code-block:: python

   sa.create_annotation_classes_from_classes_json(project, "<path_to_classes_json>")


Downloading annotation classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All of the annotation classes are downloaded (as :file:`classes/classes.json`) with 
:ref:`download_export <ref_download_export>` along with annotations, but they 
can also be downloaded separately with:

.. code-block:: python

   sa.download_annotation_classes_json(project, "<path_to_local_folder>")

The :file:`classes.json` file will be downloaded to :file:`"<path_to_local_folder>"` folder.


Working with annotations
_______________________________________________


The SuperAnnotate format annotation JSONs have the general form:

.. code-block:: json

  [ 
    {
      "className": "Human",
      "points" : "...",
      "..." : "..."
    },
    {
      "className": "Cat",
      "points" : "...",
      "..." : "..."
    },
    {
      "..." : "..."
    }
  ]

the "className" fields here will identify the annotation class of an annotation
object (polygon, points, etc.). The project
you are uploading to should contain annotation class with that name.

To upload annotations to platform:

.. code-block:: python

    sa.upload_annotations_from_folder_to_project(project, "<path_to_local_dir>")

This will try uploading to the project all the JSON files in the folder that have specific 
file naming convention. For vector
projects JSONs should be named :file:`"<image_name>___objects.json"`. For pixel projects
JSON files should be named :file:`"<image_name>___pixel.json"` and also for 
each JSON a mask image file should be present with the name 
:file:`"<image_name>___save.png"`. Image with :file:`<image_name>` should 
already be present in the project for the upload to work.


Exporting projects
__________________

To export the project annotations we need to prepare the export first:

.. code-block:: python

   export = sa.prepare_export(project, include_fuse=True)

We can download the prepared export with:

.. code-block:: python

   export = sa.download_export(export, "<local_folder_path>", extract_zip_contents=True)

:ref:`download_export <ref_download_export>` will wait until the export is
finished preparing and download it to the specified folder.


Working with images
_____________________

To search for the images in the project:

.. code-block:: python

   images = sa.search_images(project, "example_image1.jpg")

Here again we get a Python list of dict metadatas for the images with name prefix
"example_image1.jpg". The image names in SuperAnnotate platform projects are 
unique, so if full name was given to :ref:`search_images <ref_search_images>` 
the returned list will have a single item we were looking for:

.. code-block:: python

   image = images[0]

To download the image one can use:

.. code-block:: python

   sa.download_image(image, "<path_to_local_dir>")

To download image annotations:

.. code-block:: python

   sa.download_image_annotations(image, "<path_to_local_dir>")


----------


Working with team contributors
______________________________


A team contributor can be searched and chosen with:

.. code-block:: python

   found_users = sa.search_team_contributors(email="hovnatan@superannotate.com')
   hk_user = found_users[0]

Now to share a project with the found user as an QA, one can use:

.. code-block:: python

   sa.share_project(project, hk_user, user_role="QA")
