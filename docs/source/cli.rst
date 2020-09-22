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

Optional argument *extensions* accepts comma separated list of image extensions to look for. If the argument is not given then value *jpg,png* is assumed.
