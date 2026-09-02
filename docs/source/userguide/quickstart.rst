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

The package officially supports Python 3.10+ and was tested under Linux and
Windows (`Anaconda <https://www.anaconda.com/products/individual#windows>`_) platforms.

For certain video related functions to work, ffmpeg package needs to be installed.
It can be installed on Ubuntu with:

.. code-block:: bash

   sudo apt-get install ffmpeg

----------


Initialization and authorization
================================

To use the SDK, you need to create a config file with an API key. The API key is available to team owners and team admins
on the team setup page, for more details please visit our documentation at https://doc.superannotate.com/docs/api-keys.

**API key types**

- **Team API key** — scoped to one team. Works with ``SAClient``.
- **Personal (team-user) API key** — scoped to one team, tied to your user. Works with ``SAClient``.
- **Organization API key** — not scoped to a team, so the team to operate in must be supplied alongside it:

  .. code-block:: python

     SAClient(token="<Organization API key>", team_id=<team_id>)

  Instead of passing ``team_id``, you can set ``SA_TEAM_ID`` as an environment variable or in your config file. An explicit ``team_id`` argument takes precedence. Omitting the team entirely raises ``AppException``.
  To work across several teams, or when the team isn't known in advance, use ``SAORGClient`` instead — see below.


SAClient can be used with or without arguments
______________________________________________

**Without arguments**

.. code-block:: python

   from superannotate import SAClient


   sa_client = SAClient()

*Method 1:* SA_TOKEN is defined as an environment variable.

*Method 2:* Generate a default location (~/.superannotate/config.ini) config file. :ref:`CLI init <ref_cli_init>` should be used:

.. code-block:: bash

   superannotatecli init --token <API key>
                         [--logging_level <NOTSET/INFO/DEBUG/WARNING/ERROR/CRITICAL (Default=INFO)>]
                         [--logging_path <Default=/Users/username/.superannotate/logs>]


**Arguments provided**

*Method 1:* Use the token as an argument:

.. code-block:: python

   from superannotate import SAClient


   sa_client = SAClient(token="<API key>")

An Organization API key carries no team, so it is passed together with the team to
operate in:

.. code-block:: python

   sa_client = SAClient(token="<Organization API key>", team_id=<team id>)


*Method 2:* Create a custom config file:

.. code-block:: python

   from superannotate import SAClient


   sa_client = SAClient(config_path="~/.superannotate/dev-config.ini")


Custom config.ini example:

.. code-block:: ini

    [DEFAULT]
    SA_TOKEN = <API key>
    ; Only an Organization API key needs it; other keys carry their own team.
    SA_TEAM_ID = <team id>
    LOGGING_LEVEL = INFO
    LOGGING_PATH = /Users/username/data/superannotate_logs

----------


Creating a project
==================

To create a new "Vector" project with name "Example Project 1" and description
"test":

.. code-block:: python

    project = "Example Project 1"

    sa_client.create_project(project, "test", "Vector")

----------


Uploading images to project
===========================


To upload all images with extensions "jpg" or "png" from the
:file:`"<local_folder_path>"` to the project "Example Project 1":

.. code-block:: python

    sa_client.upload_images_from_folder_to_project(project, "<local_folder_path>")

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

   sa_client.download_image(project, image, "<path_to_local_dir>")

To download image annotations:

.. code-block:: python

   sa_client.download_image_annotations(project, image, "<path_to_local_dir>")

Upload back to the platform with:

.. code-block:: python

   sa_client.upload_image_annotations(project, image, "<path_to_json>")

---------


Working with team contributors
==============================

A team contributor can be invited to the team with:

.. code-block:: python

   sa_client.invite_contributors_to_team(emails=["admin@superannotate.com"], admin=False)


----------


SAORGClient: organization-scoped access
========================================

``SAORGClient`` authorizes the SDK at the organization level rather than within a single team. Use it when a script operates across several teams, or when the team isn't known in advance.

.. code-block:: python

   from superannotate import SAORGClient


   org_client = SAORGClient(token="<Organization API key>")
   # List the teams in the organization
   org_client.list_teams()

   # Get a team-scoped client for one of them
   sa_client = org_client.get_team_client(team_id=12345)
   sa_client.list_projects()

``get_team_client(team_id)`` returns a standard ``SAClient`` bound to that team. It supports the full team-level SDK surface, and no Team API key is created.
As with ``SAClient``, if no ``token`` argument is given, ``SAORGClient`` reads ``SA_TOKEN`` from the environment or from your config file.

**Important notes:**

- ``SAORGClient`` requires an Organization API key. Passing a Team or Personal API
  key raises ``AppException``.
- The team is fixed when ``get_team_client()`` is called. To work in a different
  team, call ``get_team_client()`` again with the other ID.

For the full list of organization-level methods, see the
:ref:`full method reference <ref_org_client>`.
