==========
Quickstart
==========

Installation
============


SDK is available on PyPI:

.. code-block:: bash

   pip install superannotate

The package officially supports Python 3.6+ and was tested under Linux and
Windows (`Anaconda <https://www.anaconda.com/products/individual#windows>`_) platforms.

For certain video related functions to work, ffmpeg package needs to be installed.
It can be installed on Ubuntu with:

.. code-block:: bash

   sudo apt-get install ffmpeg

For Windows and Mac OS based installations to use :py:obj:`benchmark` and :py:obj:`consensus`
functions you might also need to install beforehand :py:obj:`shapely` package,
which we found to work properly only under Anaconda distribution, with:

.. code-block:: bash

   conda install shapely


----------

Config file
____________________

To use the SDK, a config file with team specific authentication token needs to be
created.  The token is available to team admins on
team setting page at https://app.superannotate.com/team.

Default location config file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To generate a default location (:file:`~/.superannotate/config.json`) config file::

    ~/(home directory)
    └── .superannotate
        ├── config.json


:ref:`CLI init <ref_cli_init>` can be used:

.. code-block:: bash

   superannotatecli init

Custom config file
~~~~~~~~~~~~~~~~~~~~~~

To create a custom config file a new JSON file with key "token" can be created:

.. code-block:: json

   {
     "token" : "<team token>"
   }

----------

Initialization and authorization
________________________________

Include the package in your Python code:

.. code-block:: python

   from superannotate import SAClient

SDK is ready to be used if default location config file was created using
the :ref:`CLI init <ref_cli_init>`. Otherwise to authenticate SDK with the :ref:`custom config file <ref_custom_config_file>`:

.. code-block:: python

   sa = SAClient(config_path="<path_to_config_json>")



.. _basic-use:

Basic Use
=========

Creating a project
-----------------

To create a new "Vector" project with name "Example Project 1" and description
"test":

.. code-block:: python

    project = "Example Project 1"

    sa.create_project(project, "test", "Vector")


Uploading images to project
-----------------



To upload all images with extensions "jpg" or "png" from the
:file:`"<local_folder_path>"` to the project "Example Project 1":

.. code-block:: python

    sa.upload_images_from_folder_to_project(project, "<local_folder_path>")

See the full argument options for
:py:func:`upload_images_from_folder_to_project` :ref:`here <ref_upload_images_from_folder_to_project>`.

For full list of available functions on projects, see :ref:`ref_projects`.

.. note::

   Python SDK functions that accept project argument will accept both project
   name or :ref:`project metadata <ref_metadata>` (returned either by
   :ref:`get_project_metadata <ref_get_project_metadata>` or
   :ref:`search_projects <ref_search_projects>` with argument :py:obj:`return_metadata=True`).
   If project name is used it should be unique in team's project list. Using project metadata will give
   performance improvement.


