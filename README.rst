SuperAnnotate Python SDK
===============================
|Python| |License| |Changelog|


Welcome to the SuperAnnotate Python Software Development Kit (SDK), which enables Python programmers to create software that incorporates services of the platform and effortlessly integrates SuperAnnotate into their AI process.

.. |Python| image:: https://img.shields.io/static/v1?label=python&message=3.7/3.8/3.9/3.10/3.11&color=blue&style=flat-square
    :target: https://pypi.org/project/superannotate/
    :alt: Python Versions
.. |License| image:: https://img.shields.io/static/v1?label=license&message=MIT&color=green&style=flat-square
    :target: https://github.com/superannotateai/superannotate-python-sdk/blob/master/LICENSE/
    :alt: License
.. |Changelog| image:: https://img.shields.io/static/v1?label=change&message=log&color=yellow&style=flat-square
    :target: https://github.com/superannotateai/superannotate-python-sdk/blob/master/CHANGELOG.md
    :alt: Changelog

Resources
---------------

- API Reference and User Guide available on `Read the Docs <https://superannotate.readthedocs.io/en/stable/superannotate.sdk.html>`__
- `Platform documentation <https://doc.superannotate.com/>`__


Authentication
---------------

.. code-block:: python

    from superannotate import SAClient
    # by environment variable SA_TOKEN
    sa_client = SAClient()
    # by token
    sa_client = SAClient(token='<team token>')
    # by config file
    # default path is ~/.superannotate/config.json
    sa_client = SAClient(config_path='~/.superannotate/dev_config.json')

Using superannotate
-------------------

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

Installation
------------

SuperAnnotate python SDK is available on PyPI:

.. code-block:: bash

    pip install superannotate


The package officially supports Python 3.7+ and was tested under Linux and
Windows (`Anaconda <https://www.anaconda.com/products/individual#windows>`__
) platforms.

For more detailed installation steps and package usage please have a look at the `tutorial <https://superannotate.readthedocs.io/en/stable/tutorial.sdk.html>`__


Supported Features
------------------

- search/get/create/clone/update/delete projects
- search/get/create/delete folders
- assign folders to project contributors
- upload items to a project from a local or AWS S3 folder
- attach items by URL or from an integrated storage, meanwhile keeping them secure in your cloud provider
- get integrated cloud storages
- upload annotations (also from local or AWS S3 folder)
- delete annotations
- set items annotations statuses
- get/download/export annotations from a project (also to a local or AWS S3 folder)
- invite/search team contributors or add contributors to a specific project
- search/get/copy/move items in a project
- query items using SA Query Language
- define custom metadata for items and upload custom values (query based on your custom metadata)
- upload priority scores
- get available subsets (sets of segregated items), query items in a subset or add items to a subset
- assign or anassign items to project contributors
- download an image that has been uploaded to project
- search/create/download/delete project annotation classes
- search/download models
- run predictions
- convert annotations from/to COCO format
- convert annotation from VOC, SuperVisely, LabelBox, DataLoop, VGG, VoTT, SageMaker, GoogleCloud, YOLO formats
- CLI commands for simple tasks

Questions and Issues
--------------------

For questions and issues please use this repo’s issue tracker on GitHub or contact support@superannotate.com.
