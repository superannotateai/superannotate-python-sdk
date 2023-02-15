==========
Quickstart
==========

This introduction provides a quick overview of how to get SuperAnnotate Python SDK up and running on your local machine.

Installation
============

.. _ref_quickstart:

SDK is available on PyPI:

.. code-block:: bash

   pip install superannotate

The package officially supports Python 3.7+ and was tested under Linux and
Windows (`Anaconda <https://www.anaconda.com/products/individual#windows>`_) platforms.

For certain video related functions to work, ffmpeg package needs to be installed.
It can be installed on Ubuntu with:

.. code-block:: bash

   sudo apt-get install ffmpeg

To use the :py:obj:`consensus` function on Windows and Mac platforms, you might also need to install the shapely package
beforehand. The package works well only under the Anaconda distribution with:

.. code-block:: bash

   conda install shapely


----------

Initialization and authorization
================================

Config file
~~~~~~~~~~~

To use the SDK, you need to create a config file with a team-specific authentication token. The token is available
to team admins on the team settings page at https://app.superannotate.com/team.

Default location config file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To generate a default location (:file:`~/.superannotate/config.json`) config file::

    ~/(home directory)
    └── .superannotate
        ├── config.ini


:ref:`CLI init <ref_cli_init>` can be used:

.. code-block:: bash

   superannotatecli init <token>

Custom config file
~~~~~~~~~~~~~~~~~~
.. _ref_custom_config_file:

To create a custom config file a new INI file with key "token" can be created:

.. code-block:: ini

    [DEFAULT]
    SA_TOKEN = <token>
    LOGGING_LEVEL = INFO
    LOGGING_PATH = ~/.superannotate/logs


Include the package in your Python code:

.. code-block:: python

   from superannotate import SAClient

SDK is ready to be used if default location config file was created using
the :ref:`CLI init <ref_cli_init>`. Otherwise to authenticate SDK with the :ref:`custom config file <ref_custom_config_file>`:

.. code-block:: python

   sa = SAClient(config_path="<path_to_config_file>")



.. _basic-use:

Creating a project
==================

To create a new "Vector" project with name "Example Project 1" and description
"test":

.. code-block:: python

    project = "Example Project 1"

    sa.create_project(project, "test", "Vector")


Uploading images to project
===========================


To upload all images with extensions "jpg" or "png" from the
:file:`"<local_folder_path>"` to the project "Example Project 1":

.. code-block:: python

    sa.upload_images_from_folder_to_project(project, "<local_folder_path>")

See the full argument options for
:py:func:`upload_images_from_folder_to_project` :ref:`here <ref_upload_images_from_folder_to_project>`.

:ref:`For full list of available functions on projects, see <ref_projects>`.

.. note::

   Python SDK functions that accept project argument will accept both project
   name or :ref:`project metadata <ref_metadata>` (returned either by
   :ref:`get_project_metadata <ref_get_project_metadata>` or
   :ref:`search_projects <ref_search_projects>` with argument :py:obj:`return_metadata=True`).
   If project name is used it should be unique in team's project list. Using project metadata will give
   performance improvement.


Working with images
===================


To download the image one can use:

.. code-block:: python

   image = "example_image1.jpg"

   sa.download_image(project, image, "<path_to_local_dir>")

To download image annotations:

.. code-block:: python

   sa.download_image_annotations(project, image, "<path_to_local_dir>")

Upload back to the platform with:

.. code-block:: python

   sa.upload_image_annotations(project, image, "<path_to_json>")




Working with team contributors
==============================

A team contributor can be invited to the team with:

.. code-block:: python

   sa.invite_contributors_to_team(emails=["admin@superannotate.com"], admin=False)
