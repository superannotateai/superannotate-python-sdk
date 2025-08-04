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

----------


Initialization and authorization
================================

To use the SDK, you need to create a config file with a team-specific authentication token. The token is available
to team admins on the team settings page at https://doc.superannotate.com/docs/token-for-python-sdk#generate-a-token-for-python-sdk.

SAClient can be used with or without arguments
______________________________________________

**Without arguments**

.. code-block:: python

   from superannotate import SAClient


   sa_client = SAClient()

*Method 1:* SA_TOKEN is defined as an environment variable.

*Method 2:* Generate a default location (~/.superannotate/config.ini) config file. :ref:`CLI init <ref_cli_init>` should be used:

.. code-block:: bash

   superannotatecli init --token <token>
                         [--logging_level <NOTSET/INFO/DEBUG/WARNING/ERROR/CRITICAL (Default=INFO)>]
                         [--logging_path <Default=/Users/username/.superannotate/logs>]


**Arguments provided**

*Method 1:* Use the token as an argument:

.. code-block:: python

   from superannotate import SAClient


   SAClient(token="<token>")


*Method 2:* Create a custom config file:

.. code-block:: python

   from superannotate import SAClient


   sa_client = SAClient(config_path="~/.superannotate/dev-config.ini")


Custom config.ini example:

.. code-block:: ini

    [DEFAULT]
    SA_TOKEN = <token>
    LOGGING_LEVEL = INFO
    LOGGING_PATH = /Users/username/data/superannotate_logs

----------


Using Managers (Recommended)
=============================

The SDK provides manager interfaces that organize functionality into logical groups:

.. code-block:: python

    from superannotate import SAClient

    sa = SAClient()

    # Using managers for better organization
    project = sa.projects.create("Example Project 1", "test", "Vector")
    items = sa.items.list("Example Project 1")
    users = sa.users.list(project="Example Project 1")

Available managers:

* ``sa.projects`` - Project operations (create, list, clone, delete, rename)
* ``sa.folders`` - Folder operations (create, list, delete)
* ``sa.items`` - Item operations (list, attach, delete)
* ``sa.annotations`` - Annotation operations (upload, get, delete)
* ``sa.users`` - User operations (list, get metadata, invite, add to projects)

For detailed information, see the :doc:`managers` guide.

----------


Creating a project
==================

To create a new "Vector" project with name "Example Project 1" and description
"test":

.. code-block:: python

    project = "Example Project 1"

    # Using managers (recommended)
    sa.projects.create(project, "test", "Vector")

    # Or using direct methods (still supported)
    sa.create_project(project, "test", "Vector")

----------


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

----------


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

---------


Working with team contributors
==============================

A team contributor can be invited to the team with:

.. code-block:: python

   sa.invite_contributors_to_team(emails=["admin@superannotate.com"], admin=False)
