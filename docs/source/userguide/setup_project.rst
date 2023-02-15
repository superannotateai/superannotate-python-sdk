=============
Setup Project
=============


Creating a project
------------------

To create a new "Vector" project with name "Example Project 1" and description
"test":

.. code-block:: python

    project = "Example Project 1"

    sa.create_project(project, "test", "Vector")


Uploading images to project
---------------------------


To upload all images with extensions "jpg" or "png" from the
:file:`"<local_folder_path>"` to the project "Example Project 1":

.. code-block:: python

    sa.upload_images_from_folder_to_project(project, "<local_folder_path>")

See the full argument options for
:py:func:`upload_images_from_folder_to_project` :ref:`here <ref_upload_images_from_folder_to_project>`.


.. note::

   Python SDK functions that accept project argument will accept both project
   name or :ref:`project metadata <ref_metadata>` (returned either by
   :ref:`get_project_metadata <ref_get_project_metadata>` or
   :ref:`search_projects <ref_search_projects>` with argument :py:obj:`return_metadata=True`).
   If project name is used it should be unique in team's project list. Using project metadata will give
   performance improvement.


Creating a folder in a project
______________________________

To create a new folder "folder1" in the project "Example Project 1":

.. code-block:: python

    sa.create_folder(project, "folder1")

After that point almost all SDK functions that use project name as argument can
point to that folder with slash after the project name, e.g.,
"Example Project 1/folder1", in this case.

.. note::

   To upload images to the "folder1" instead of the root of the project:

      .. code-block:: python

         sa.upload_images_from_folder_to_project(project + "/folder1", "<local_folder_path>")

Working with annotation classes
_______________________________

An annotation class for a project can be created with SDK's:

.. code-block:: python

   sa.create_annotation_class(project, "Large car", color="#FFFFAA")


To create annotation classes in bulk with SuperAnnotate export format
:file:`classes.json` (documentation at:
https://app.superannotate.com/documentation Management Tools
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
________________________


The SuperAnnotate format annotation JSONs have the general form:

.. code-block:: json

    {
        "metadata":{
            "name":"example_image_1.jpg",
            "width":1024,
            "height":683,
            "status":"Completed",
        },
        "instances":[
            {
                "type":"bbox",
                "classId":72274,
                "probability":100,
                "points":{
                    "x1":437.16,
                    "x2":465.23,
                    "y1":341.5,
                    "y2":357.09
                },
                "className":"Jake"
            },
            {
                "type":"polygon",
                "classId":72274,
                "probability":100,
                "points":[
                    281.98,
                    383.75,
                    282.55,
                ],
                "className":"Finn"
            }
        ],
    }

the "className" fields here will identify the annotation class of an annotation
object (polygon, points, etc.). The project
you are uploading to should contain annotation class with that name.

:ref:`To upload annotations to platform: <ref_upload_annotations_from_folder_to_project>`

.. code-block:: python

    sa.upload_annotations_from_folder_to_project(project, "<path_to_local_dir>")


This will try uploading to the project all the JSON files in the folder that have :file:`"<image_name>.json"` postfix.
For pixel projects JSON files should be named :file:`"<image_name>___pixel.json"` and also for
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

   sa.download_export(project, export, "<local_folder_path>", extract_zip_contents=True)

:ref:`download_export <ref_download_export>` will wait until the export is
finished preparing and download it to the specified folder.

