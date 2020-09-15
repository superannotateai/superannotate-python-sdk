.. _ref_tutorial:

Tutorial
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

The package officially supports Python 3.6+.

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
that contains "Example Project 1". Full documentation of the function can be found at 
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

   Since the the SuperAnnotate platform allows identically named projects, one
   needs to examine the :py:obj:`projects` to identify the looked for project,
   if identically named or identically prefix named projects exist, e.g.,

   .. code-block:: python

      for project in projects:
          if project["description"] == "my desc":
              break

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


All of the annotation classes of a project are downloaded (as :file:`classes/classes.json`) with
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

You can add an annotation to local annotations JSON with:

.. code-block:: python

   sa.add_annotation_bbox_to_json("<path_to_json>", [10, 10, 100, 100],
                                  "Human")



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


Converting annotation format
______________________________

After exporting project annotations (in SuperAnnotate format), it is possible
to convert them to other annotation formats:

.. code-block:: python

    sa.export_annotation_format("<input_folder>", "<output_folder>", "COCO", "<dataset_name>", "<project_type>",
                                "<task>", "<platform>")

.. note::
    
  Right now we support only COCO annotation format conversion.

You can find more information annotation format conversion :ref:`here <ref_converter>`. We provide some examples in our github repository. In the root folder of our github repository, you can run following commands to do conversions.

.. code-block:: python

   import superannotate as sa

    # From SA panoptic format to COCO panoptic format
    sa.export_annotation_format("tests/converter_test/COCO/input/fromSuperAnnotate/cats_dogs_panoptic_segm", "tests/converter_test/COCO/output/panoptic","COCO","panoptic_test", "Pixel","panoptic_segmentation","Web")

    # From COCO keypoints detection format to SA keypoints detection desktop application format 
    sa.import_annotation_format("tests/converter_test/COCO/input/toSuperAnnotate/keypoint_detection", "tests/converter_test/COCO/output/keypoints", "COCO", "person_keypoints_test", "Vector", "keypoint_detection", "Desktop")

    # Pascal VOC annotation format to SA Web platform annotation format
    sa.import_annotation_format("tests/converter_test/VOC/input/fromPascalVOCToSuperAnnotate/VOC2012", "tests/converter_test/VOC/output/instances", "VOC", "instances_test", "Pixel", "instance_segmentation", "Web")

    # LabelBox annotation format to SA Desktop application annotation format
    sa.import_annotation_format("tests/converter_test/LabelBox/input/toSuperAnnotate/", "tests/converter_test/LabelBox/output/objects/", "LabelBox", "labelbox_example", "Vector", "object_detection", "Desktop")


Working with images
_____________________

To search for the images in the project:

.. code-block:: python

   images = sa.search_images(project, "example_image1.jpg")

Return value is list of images with names that have prefix "example_image1.jpg".
The list is ordered ascending direction by name, so if we are looking for exact name match:

.. code-block:: python

   image = images[0]

.. note::

   The image names in SuperAnnotate platform projects are 
   unique.


To download the image one can use:

.. code-block:: python

   sa.download_image(project, image, "<path_to_local_dir>")

To download image annotations:

.. code-block:: python

   sa.download_image_annotations(project, image, "<path_to_local_dir>")

After the image annotations are downloaded, you can add annotations to it:

.. code-block:: python

   sa.add_annotation_bbox_to_json("<path_to_json>", [10, 10, 100, 100],
                                  "Human")

and upload back to the platform with:

.. code-block:: python

   sa.upload_annotations_from_json_to_image(project, image, "<path_to_json>")

Last two steps can be combined into one:

.. code-block:: python

   sa.add_annotation_bbox_to_image(project, image, [10, 10, 100, 100], "Human")

but if bulk changes are made to many images it is much faster to add all required
annotations using :ref:`add_annotation_bbox_to_json
<ref_add_annotation_bbox_to_json>` 
then upload them using
:ref:`upload_annotations_from_folder_to_project
<ref_upload_images_from_folder_to_project>`.


----------


Working with team contributors
______________________________

A team contributor can be invited to the team with:

.. code-block:: python

   sa.invite_contributor_to_team(email="hovnatan@superannotate.com", admin=False)


This invitation should be accepted by the contributor. After which, the
contributor can be searched and chosen:

.. code-block:: python

   found_contributors = sa.search_team_contributors(email="hovnatan@superannotate.com')
   hk_c = found_contributors[0]

Now to share a project with the found contributor as an QA:

.. code-block:: python

   sa.share_project(project, hk_c, user_role="QA")
