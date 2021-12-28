.. _ref_cli:

CLI Reference
======================================

With SuperAnnotate CLI, basic tasks can be accomplished using shell commands:

.. code-block:: bash

   superannotatecli <command> <--arg1 val1> <--arg2 val2> [--optional_arg3 val3] [--optional_arg4] ...

To use the CLI a command line initialization step should be performed after the
:ref:`installation <ref_tutorial_installation>`:

.. code-block:: bash

   superannotatecli init

----------


Available commands 
________________________


.. _ref_cli_init:

Initialization and configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To initialize CLI (and SDK) with team token:

.. code-block:: bash

   superannotatecli init

----------

.. _ref_create_project:

Creating a project
~~~~~~~~~~~~~~~~~~

To create a new project:

.. code-block:: bash

   superannotatecli create-project --name <project_name> --description <project_description> --type <project_type Vector or Pixel>

----------

Creating a folder in a project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a new folder:

.. code-block:: bash

   superannotatecli create-folder --project <project_name> --name <folder_name>

----------

.. _ref_upload_images:

Uploading images
~~~~~~~~~~~~~~~~

To upload images from folder to project use:

.. code-block:: bash

   superannotatecli upload-images --project <project_name> --folder <folder_path> [--recursive] [--extensions <extension1>,<extension2>,...]

If optional argument *recursive* is given then subfolders of :file:`<folder_path>` are also recursively
scanned for available images.

Optional argument *extensions* accepts comma separated list of image extensions
to look for. If the argument is not given then value *jpg,jpeg,png,tif,tiff,webp,bmp* is assumed.

----------

.. _ref_attach_image_urls:

Attaching image URLs
~~~~~~~~~~~~~~~~~~~~

To attach image URLs to project use:

.. code-block:: bash

   superannotatecli attach-image-urls --project <project_name/folder_name> --attachments <csv_path> [--annotation_status <annotation_status>]

----------

.. _ref_upload_videos:

Uploading videos
~~~~~~~~~~~~~~~~

To upload videos from folder to project use:

.. code-block:: bash

   superannotatecli upload-videos --project <project_name> --folder <folder_path> 
                                  [--recursive] [--extensions mp4,avi,mov,webm,flv,mpg,ogg]
                                  [--target-fps <float>] [--start-time <float>]
                                  [--end-time <float>]

If optional argument *recursive* is given then subfolders of :file:`<folder_path>` are also recursively
scanned for available videos.

Optional argument *extensions* accepts comma separated list of image extensions
to look for. If the argument is not given then value *mp4,avi,mov,webm,flv,mpg,ogg* is assumed.

*target-fps* specifies how many frames per second need to extract from the videos (approximate).
If not specified all frames will be uploaded.

*start-time* specifies time (in seconds) from which to start extracting frames,
default is 0.0.

*end-time* specifies time (in seconds) up to which to extract frames. 
If it is not specified, then up to end is assumed.

----------

.. _ref_upload_preannotations:

Uploading preannotations
~~~~~~~~~~~~~~~~~~~~~~~~

To upload preannotations from folder to project use:

.. code-block:: bash

   superannotatecli upload-preannotations --project <project_name> --folder <folder_path> 
                                          [--format "COCO" or "SuperAnnotate"] 
                                          [--dataset-name "<dataset_name_for_COCO_projects>"]
                                          [--task "<task_type_for_COCO_projects>]


Optional argument *format* accepts input annotation format. It can have COCO or SuperAnnotate values.
If the argument is not given then SuperAnnotate (the native annotation format) is assumed.

Only when COCO format is specified *dataset-name* and *task* arguments are required.

*dataset-name* specifies JSON filename (without extension) in <folder_path>.

*task* specifies the COCO task for conversion. Please see 
:ref:`import_annotation_format <ref_import_annotation_format>` for more details.


----------

.. _ref_upload_annotations:

Uploading annotations
~~~~~~~~~~~~~~~~~~~~~~~~

To upload annotations from folder to project use:

.. code-block:: bash

   superannotatecli upload-annotations --project <project_name> --folder <folder_path> 
                                       [--format "COCO" or "SuperAnnotate"] 
                                       [--dataset-name "<dataset_name_for_COCO_projects>"]
                                       [--task "<task_type_for_COCO_projects>]

Optional argument *format* accepts input annotation format. It can have COCO or SuperAnnotate values.
If the argument is not given then SuperAnnotate (the native annotation format) is assumed.

Only when COCO format is specified *dataset-name* and *task* arguments are required.

*dataset-name* specifies JSON filename (without extension) in <folder_path>.

*task* specifies the COCO task for conversion. Please see 
:ref:`import_annotation_format <ref_import_annotation_format>` for more details.

----------

.. _ref_export_project:

Exporting projects
~~~~~~~~~~~~~~~~~~~~~~~~

To export project

.. code-block:: bash

   superannotatecli export-project --project <project_name> --folder <folder_path> 
                                   [--include-fuse]
                                   [--disable-extract-zip-contents] 
                                   [--annotation-statuses <comma separated list of annotation statuses to export>]

----------

.. _ref_cli_version:

SDK version information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To show the version of the current SDK installation:

.. code-block:: bash

   superannotatecli version
