.. _ref_sdk:

SDK Reference
===========================

.. contents::


Initialization and authentication
_________________________________

.. autofunction:: superannotate.init

----------

.. _ref_projects:

Projects
________

.. note::

  Project metadata example:

  .. code-block:: python

     {
       "name": "Example Project test",
       "description": "test vector",
       "creator_id": "hovnatan@superannotate.com",
       "id": 3628,
       "updatedAt": "2020-08-31T05:43:43.118Z",
       "createdAt": "2020-08-31T05:43:43.118Z"
       "team_id": 315,
       "type": 1,
       "attachment_name": None,
       "attachment_path": None,
       "entropy_status": 1,
       "status": 0,
     }


.. _ref_search_projects:
.. autofunction:: superannotate.search_projects
.. autofunction:: superannotate.create_project
.. autofunction:: superannotate.delete_project
.. autofunction:: superannotate.get_project_metadata
.. autofunction:: superannotate.get_project_image_count
.. autofunction:: superannotate.upload_images_to_project
.. _ref_upload_images_from_folder_to_project:
.. autofunction:: superannotate.upload_images_from_folder_to_project
.. autofunction:: superannotate.upload_annotations_from_folder_to_project
.. autofunction:: superannotate.upload_preannotations_from_folder_to_project
.. autofunction:: superannotate.share_project
.. autofunction:: superannotate.unshare_project

----------

Exports
_______

.. autofunction:: superannotate.prepare_export
.. _ref_download_export:
.. autofunction:: superannotate.download_export
.. autofunction:: superannotate.get_exports

----------

Images
______



.. note::

   Image metadata example:

   .. code-block:: python

      {
        "name": "000000000001.jpg",
        "annotation_status": 1,
        "prediction_status": 1,
        "segmentation_status": 1,
        "annotator_id": None,
        "annotator_name": None,
        "qa_id": None,
        "qa_name": None,
        "entropy_value": None,
        "approval_status": None,
        "createdAt": "2020-08-18T07:30:06.000Z",
        "updatedAt": "2020-08-18T07:30:06.000Z"
        "project_id": 2734,
        "id": 523862,
        "is_pinned": 0,
        "team_id": 315,
        "...": "...",
      }

.. _ref_search_images:
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
.. _ref_create_annotation_classes_from_classes_json:
.. autofunction:: superannotate.create_annotation_classes_from_classes_json
.. autofunction:: superannotate.search_annotation_classes
.. autofunction:: superannotate.download_annotation_classes_json

----------

Users
_____

.. autofunction:: superannotate.search_team_contributors
