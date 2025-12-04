=============
Setup Project
=============


Creating a Multimodal project
------------------------------

For Multimodal projects you **must** provide a ``form`` JSON object that
conforms to SuperAnnotate's Multimodal form template schema. The form
defines the project's UI layout and component behavior in the Multimodal
Form Editor.

.. code-block:: python

    minimal_form = {
        "components": [
            {
                "id": "component_id_0",
                "type": "select",
                "permissions": [],
                "hasTooltip": False,
                "label": "Select",
                "isRequired": False,
                "value": [],
                "options": [
                    {"value": "Partially complete, needs review", "checked": False},
                    {"value": "Incomplete", "checked": False},
                    {"value": "Complete", "checked": False},
                    {"value": "4", "checked": False}
                ],
                "exclude": False,
                "isMultiselect": True,
                "placeholder": "Select"
            },
            {
                "id": "component_id_1",
                "type": "input",
                "permissions": [],
                "hasTooltip": False,
                "label": "Text input",
                "placeholder": "Placeholder",
                "isRequired": False,
                "value": "",
                "min": 0,
                "max": 300,
                "exclude": False
            },
            {
                "id": "component_id_2",
                "type": "number",
                "permissions": [],
                "hasTooltip": False,
                "label": "Number",
                "exclude": False,
                "isRequired": False,
                "value": None,
                "min": None,
                "max": None,
                "step": 1
            }
        ],
        "code": "",
        "environments": []
    }

    response = sa_client.create_project(
        project_name="My Multimodal Project",
        project_description="Example multimodal project created via SDK",
        project_type="Multimodal",
        form=minimal_form
    )

After creating the project, you can create folders and generate items:

.. code-block:: python

    # Create a new folder in the project
    sa_client.create_folder(
        project="My Multimodal Project",
        folder_name="First Folder"
    )

    # Generate multiple items in the specific project and folder
    # If there are no items in the folder, it will generate a blank item
    # otherwise, it will generate items based on the Custom Form
    sa_client.generate_items(
        project="My Multimodal Project/First Folder",
        count=10,
        name="My Item"
    )

To upload annotations to these items:

.. code-block:: python

    annotations = [
        # list of annotation dicts
    ]

    sa_client.upload_annotations(
        project="My Multimodal Project/First Folder",
        annotations=annotations,
        keep_status=True,
        data_spec="multimodal"
    )

Creating a  Vector project
--------------------------

To create a new "Vector" project with name "Example Project 1" and description
"test":

.. code-block:: python

    project = "Example Project 1"

    sa_client.create_project(project, "test", "Vector")


Uploading images to project
===========================


To upload all images with extensions "jpg" or "png" from the
:file:`"<local_folder_path>"` to the project "Example Project 1":

.. code-block:: python

    sa_client.upload_images_from_folder_to_project(project, "<local_folder_path>")

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
==============================

To create a new folder "folder1" in the project "Example Project 1":

.. code-block:: python

    sa_client.create_folder(project, "folder1")

After that point almost all SDK functions that use project name as argument can
point to that folder with slash after the project name, e.g.,
"Example Project 1/folder1", in this case.

.. note::

   To upload images to the "folder1" instead of the root of the project:

      .. code-block:: python

         sa_client.upload_images_from_folder_to_project(project + "/folder1", "<local_folder_path>")

Working with annotation classes
===============================

An annotation class for a project can be created with SDK's:

.. code-block:: python

   sa_client.create_annotation_class(project, "Large car", color="#FFFFAA")


To create annotation classes in bulk with SuperAnnotate export format
:file:`classes.json` (documentation at:
https://superannotate.readthedocs.io/en/stable/userguide/setup_project.html#working-with-annotation-classes Ma`nagement Tools
-> Project Workflow part):

.. code-block:: python

   sa_client.create_annotation_classes_from_classes_json(project, "<path_to_classes_json>")


All of the annotation classes of a project are downloaded (as :file:`classes/classes.json`) with
:ref:`download_export <ref_download_export>` along with annotations, but they
can also be downloaded separately with:

.. code-block:: python

   sa_client.download_annotation_classes_json(project, "<path_to_local_folder>")

The :file:`classes.json` file will be downloaded to :file:`"<path_to_local_folder>"` folder.


Working with annotations
========================


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

    sa_client.upload_annotations_from_folder_to_project(project, "<path_to_local_dir>")


This will try uploading to the project all the JSON files in the folder that have :file:`"<image_name>.json"` postfix.
For pixel projects JSON files should be named :file:`"<image_name>___pixel.json"` and also for
each JSON a mask image file should be present with the name
:file:`"<image_name>___save.png"`. Image with :file:`<image_name>` should
already be present in the project for the upload to work.


Exporting projects
==================

To export the project annotations we need to prepare the export first:

.. code-block:: python

   export = sa_client.prepare_export(project, include_fuse=True)

We can download the prepared export with:

.. code-block:: python

   sa_client.download_export(project, export, "<local_folder_path>", extract_zip_contents=True)

:ref:`download_export <ref_download_export>` will wait until the export is
finished preparing and download it to the specified folder.
