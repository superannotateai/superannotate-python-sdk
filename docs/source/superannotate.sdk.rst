.. _sdk:

SDK functions
===========================

.. contents::


Initialization and authentication
_________________________________

.. autofunction:: superannotate.init

----------

Projects
________

.. autofunction:: superannotate.search_projects
.. autofunction:: superannotate.create_project
.. autofunction:: superannotate.delete_project
.. autofunction:: superannotate.get_project_metadata
.. autofunction:: superannotate.get_project_image_count
.. autofunction:: superannotate.upload_images_to_project
.. autofunction:: superannotate.upload_images_from_folder_to_project
.. autofunction:: superannotate.upload_annotations_from_folder_to_project
.. autofunction:: superannotate.upload_preannotations_from_folder_to_project
.. autofunction:: superannotate.share_project
.. autofunction:: superannotate.unshare_project

----------

Exports
_______

.. autofunction:: superannotate.prepare_export
.. autofunction:: superannotate.download_export
.. autofunction:: superannotate.get_exports

----------

Images
______

.. autofunction:: superannotate.search_images
.. autofunction:: superannotate.get_image_metadata
.. autofunction:: superannotate.get_image_bytes
.. autofunction:: superannotate.download_image
.. autofunction:: superannotate.set_image_annotation_status
.. autofunction:: superannotate.get_image_annotations
.. autofunction:: superannotate.get_image_preannotations
.. autofunction:: superannotate.download_image_annotations
.. autofunction:: superannotate.download_image_preannotations

----------

Annotation Classes
__________________

.. autofunction:: superannotate.create_annotation_class
.. autofunction:: superannotate.create_annotation_classes_from_classes_json
.. autofunction:: superannotate.search_annotation_classes
.. autofunction:: superannotate.download_annotation_classes_json

----------

Users
_____

.. autofunction:: superannotate.search_users
