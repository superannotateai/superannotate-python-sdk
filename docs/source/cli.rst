.. _ref_cli:

CLI Reference
======================================

With SuperAnnotate CLI, basic tasks can be accomplished using shell commands:

.. code-block:: bash

   superannotate <command> <--arg1 val1> <--arg2 val2> [--optional_arg3 val3] [--optional_arg4] ...

To use the CLI a command line initialization step should be performed after the
:ref:`installation <ref_tutorial_installation>`:

.. code-block:: bash

   superannotate init

----------


Available commands 
________________________


.. _ref_cli_init:

Initialization and configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To initialize CLI (and SDK) with team token:

.. code-block:: bash

   superannotate init

----------

.. _ref_upload_images:

Uploading images
~~~~~~~~~~~~~~~~

To upload images from folder to project use:

.. code-block:: bash

   superannotate upload-images --project <project_name> --folder <folder_path> [--recursive] [--extensions jpg,png]

If optional argument *recursive* is given then subfolders of :file:`<folder_path>` are also recursively
scanned for available images.

Optional argument *extensions* accepts comma separated list of image extensions
to look for. If the argument is not given then value *jpg,png* is assumed.

----------

.. _ref_upload_videos:

Uploading videos
~~~~~~~~~~~~~~~~

To upload videos from folder to project use:

.. code-block:: bash

   superannotate upload-videos --project <project_name> --folder <folder_path> 
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

   superannotate upload-preannotations --project <project_name> --folder <folder_path> 
                                       [--format "COCO" or "SA"]


Optional argument *format* accepts input preannotation format. It can have COCO or SuperAnnotate values.
If the argument is not given then SuperAnnotate (the native preannotation format) assumed.

----------

.. _ref_upload_annotations:

Uploading annotations
~~~~~~~~~~~~~~~~~~~~~~~~

To upload annotations from folder to project use:

.. code-block:: bash

   superannotate upload-preannotations --project <project_name> --folder <folder_path> 
                                       [--recursive]

If optional argument *recursive* is given then subfolders of :file:`<folder_path>` are also recursively
scanned for available preannotations.


----------

.. _ref_cli_version:

SDK version information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To show the version of the current SDK installation:

.. code-block:: bash

   superannotate version
