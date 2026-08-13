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
    :target: https://github.com/superannotateai/superannotate-python-sdk/blob/master/CHANGELOG.rst
    :alt: Changelog

Resources
---------------

- API Reference and User Guide available on `Read the Docs <https://superannotate.readthedocs.io/en/stable/index.html>`__
- `Platform documentation <https://doc.superannotate.com/>`__


Authentication
---------------

.. code-block:: python

    from superannotate import SAClient
    # by environment variable SA_TOKEN
    sa_client = SAClient()
    # by token
    sa_client = SAClient(token='<API key>')
    # by config file
    # default path is ~/.superannotate/config.ini
    sa_client = SAClient(config_path='~/.superannotate/dev_config.ini')


config.ini example
------------------
.. code-block:: python

    [DEFAULT]
    SA_TOKEN = <API key>
    LOGGING_LEVEL = INFO
    LOGGING_PATH = /Users/username/data/superannotate_logs


Using superannotate
-------------------

.. code-block:: python

    from superannotate import SAClient


    sa_client = SAClient()

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


The package officially supports Python 3.10+ and was tested under Linux and
Windows (`Anaconda <https://www.anaconda.com/products/individual#windows>`__
) platforms.


Questions and Issues
--------------------

For questions and issues please use this repo’s issue tracker on GitHub or contact support@superannotate.com.
