.. SuperAnnotate Python SDK documentation master file, created by
   sphinx-quickstart on Fri Aug 21 14:40:52 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. image:: images/sa_logo.png
  :width: 200
  :alt: SuperAnnotate AI
  :target: https://app.superannotate.com



.. toctree::
   :caption: Table of Contents
   :name: mastertoc
   :maxdepth: 1

   User guide <userguide/index>
   API Reference <api_reference/index>
   CLI Reference <cli_client>
   SA Server <sa_server>
   LICENSE.rst

----------

SuperAnnotate Python SDK documentation
==================================================================

SuperAnnotate Python SDK allows access to the platform without web browser:

.. code-block:: python

    from superannotate import SAClient


    sa_client =SAClient()

    project = 'Dogs'

    sa_client.create_project(
            project_name=project,
            project_description='Test project generated via SDK',
            project_type='Vector'
        )

    sa_client.create_annotation_class(
        project=project,
        name='dog',
        color='#F9E0FA',
        class_type='tag'
    )

    sa_client.attach_items(
            project=project,
            attachments=[
                {
                    'url': 'https://drive.google.com/uc?export=download&id=1ipOrZNSTlPUkI_hnrW9aUD5yULqqq5Vl',
                    'name': 'dog.jpeg'
                }
            ]
        )

    sa_client.upload_annotations(
            project=project,
            annotations=[
                {
                    'metadata': {'name': 'dog.jpeg'},
                    'instances': [
                        {'type': 'tag', 'className': 'dog'}
                    ]
                }
            ]
        )

    sa_client.get_annotations(project=project, items=['dog.jpeg'])

----------

Installation
____________


SDK is available on PyPI:

.. code-block:: bash

   pip install superannotate


The package officially supports Python 3.7+ and was tested under Linux and
Windows (`Anaconda <https://www.anaconda.com/products/individual#windows>`_) platforms.

----------

Supported Features
__________________

- Search projects
- Create/delete a project
- Upload images to a project from a local or AWS S3 folder
- Upload videos to a project from a local folder
- Upload annotations/pre-annotations to a project from local or AWS S3 folder
- Set the annotation status of the images being uploaded
- Export annotations from a project to a local or AWS S3 folder
- Share and unshare a project with a team contributor
- Invite a team contributor
- Search images in a project
- Download a single image
- Copy/move image between projects
- Get image bytes (e.g., for numpy array creation)
- Set image annotation status
- Download image annotations/pre-annotations
- Create/download project annotation classes
- Add annotations to images on platform
- Convert annotation format from/to COCO
- Add annotations to local SuperAnnotate format JSONs
- CLI commands for simple tasks
- Aggregate class/attribute distribution as histogram

----------

License
_______

This SDK is distributed under the :ref:`MIT License <ref_license>`.

----------

Questions and Issues
____________________

For questions and issues please use issue tracker on
`GitHub <https://github.com/superannotateai/superannotate-python-sdk>`_.
