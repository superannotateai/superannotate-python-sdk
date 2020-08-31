.. SuperAnnotate Python SDK documentation master file, created by
   sphinx-quickstart on Fri Aug 21 14:40:52 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. image:: sa_logo.png
  :width: 200
  :alt: SuperAnnotate AI

|

.. toctree::
   :maxdepth: 1

   tutorial.sdk.rst
   superannotate.sdk.rst
   metadata_ref.rst

SuperAnnotate Python SDK (beta) documentation
==================================================================

SuperAnnotate Python SDK allows access to the platform without web browser:

.. code-block:: python

   import superannotate as sa

   sa.init(<path_to_my_config_json>)

   projects = sa.search_projects("Example Project 1")

   example_project = projects[0]
   sa.upload_images_from_folder(example_project, <path_to_my_images_folder>)


Supported Features
__________________

- Search projects
- Create/delete a project
- Upload images to a project from local or AWS S3 folder
- Upload annotations/pre-annotations to a project from local or AWS S3 folder
- Set the annotation status of the images being uploaded
- Export annotations from a project to a local or AWS S3 folder
- Share and unshare a project with a team contributor
- Search images in a project
- Download a single image
- Get image bytes (e.g., for numpy array creation)
- Set image annotation status
- Download image annotations/pre-annotations
- Create/download project annotation classes

License
_______

This SDK is distributed under the MIT License.

Questions and Issues
____________________

For questions and issues please use issue tracker on
`Github <https://github.com/superannotateai/superannotate-python-sdk>`_.
