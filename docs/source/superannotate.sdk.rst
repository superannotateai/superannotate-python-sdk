.. _ref_sdk:

API Reference
===================================

.. contents::

Remote functions
----------------

Initialization and authentication
_________________________________

.. autofunction:: superannotate.init


.. _ref_projects:

Projects
________

.. _ref_search_projects:
.. autofunction:: superannotate.search_projects
.. autofunction:: superannotate.create_project
.. autofunction:: superannotate.create_project_from_metadata
.. autofunction:: superannotate.clone_project
.. autofunction:: superannotate.delete_project
.. autofunction:: superannotate.rename_project
.. _ref_get_project_metadata:
.. autofunction:: superannotate.get_project_metadata
.. autofunction:: superannotate.get_project_image_count
.. autofunction:: superannotate.get_project_and_folder_metadata
.. autofunction:: superannotate.search_folders
.. autofunction:: superannotate.get_folder_metadata
.. autofunction:: superannotate.create_folder
.. autofunction:: superannotate.delete_folders
.. autofunction:: superannotate.upload_images_to_project
.. autofunction:: superannotate.attach_image_urls_to_project
.. autofunction:: superannotate.attach_document_urls_to_project
.. autofunction:: superannotate.attach_items_from_integrated_storage
.. autofunction:: superannotate.upload_image_to_project
.. autofunction:: superannotate.delete_annotations
.. _ref_upload_images_from_folder_to_project:
.. autofunction:: superannotate.upload_images_from_folder_to_project
.. autofunction:: superannotate.upload_video_to_project
.. autofunction:: superannotate.upload_videos_from_folder_to_project
.. autofunction:: superannotate.attach_video_urls_to_project
.. _ref_upload_annotations_from_folder_to_project:
.. autofunction:: superannotate.upload_annotations_from_folder_to_project
.. autofunction:: superannotate.upload_preannotations_from_folder_to_project
.. autofunction:: superannotate.share_project
.. autofunction:: superannotate.add_contributors_to_project
.. autofunction:: superannotate.get_project_settings
.. autofunction:: superannotate.set_project_default_image_quality_in_editor
.. autofunction:: superannotate.get_project_workflow
.. autofunction:: superannotate.set_project_workflow

----------

Exports
_______

.. autofunction:: superannotate.prepare_export
.. autofunction:: superannotate.get_annotations
.. autofunction:: superannotate.get_annotations_per_frame
.. _ref_download_export:
.. autofunction:: superannotate.download_export
.. autofunction:: superannotate.get_exports

----------

Items
______

.. autofunction:: superannotate.query
.. autofunction:: superannotate.search_items
.. autofunction:: superannotate.get_item_metadata

----------

Images
______


.. _ref_search_images:
.. autofunction:: superannotate.search_images
.. autofunction:: superannotate.search_images_all_folders
.. autofunction:: superannotate.get_image_metadata
.. autofunction:: superannotate.download_image
.. autofunction:: superannotate.set_image_annotation_status
.. autofunction:: superannotate.set_images_annotation_statuses
.. autofunction:: superannotate.download_image_annotations
.. autofunction:: superannotate.upload_image_annotations
.. autofunction:: superannotate.copy_image
.. autofunction:: superannotate.copy_images
.. autofunction:: superannotate.move_images
.. autofunction:: superannotate.pin_image
.. autofunction:: superannotate.assign_images
.. autofunction:: superannotate.delete_images
.. autofunction:: superannotate.add_annotation_bbox_to_image
.. autofunction:: superannotate.add_annotation_point_to_image
.. autofunction:: superannotate.add_annotation_comment_to_image
.. autofunction:: superannotate.upload_priority_scores

----------

Annotation Classes
__________________

.. autofunction:: superannotate.create_annotation_class
.. _ref_create_annotation_classes_from_classes_json:
.. autofunction:: superannotate.create_annotation_classes_from_classes_json
.. autofunction:: superannotate.search_annotation_classes
.. autofunction:: superannotate.download_annotation_classes_json
.. autofunction:: superannotate.delete_annotation_class

----------

Team
_________________

.. autofunction:: superannotate.get_team_metadata
.. autofunction:: superannotate.get_integrations
.. autofunction:: superannotate.invite_contributors_to_team
.. autofunction:: superannotate.search_team_contributors

----------

Neural Network
_______________

.. autofunction:: superannotate.download_model
.. autofunction:: superannotate.run_prediction
.. autofunction:: superannotate.search_models

----------


.. _ref_metadata:

Remote metadata reference
-------------------------


Projects metadata
_________________

Project metadata example:

.. code-block:: python

   {
     "name": "Example Project test",
     "description": "test vector",
     "creator_id": "admin@superannotate.com",
     "updatedAt": "2020-08-31T05:43:43.118Z",
     "createdAt": "2020-08-31T05:43:43.118Z"
     "type": "Vector",
     "attachment_name": None,
     "attachment_path": None,
     "entropy_status": 1,
     "status": 0,
     "...": "..."
   }


----------

Export metadata
_______________

Export metadata example:

.. code-block:: python

   {
     "name": "Aug 17 2020 15:44 First Name.zip",
     "user_id": "user@gmail.com",
     "status": 2,
     "createdAt": "2020-08-17T11:44:26.000Z",
     "...": "..."
   }


----------


Integration metadata
_______________

Integration metadata example:

.. code-block:: python

   {
   "name": "My S3 Bucket",
   "type": "aws",
   "root": "test-openseadragon-1212"
    }


----------


Item metadata
_______________

Item metadata example:

.. code-block:: python

  {
   "name": "example.jpeg",
   "path": "project/folder_1/meow.jpeg",
   "url": "https://sa-public-files.s3.../text_file_example_1.jpeg",
   "annotation_status": "NotStarted",
   "annotator_name": None,
   "qa_name": None,
   "entropy_value": None,
   "createdAt": "2022-02-15T20:46:44.000Z",
   "updatedAt": "2022-02-15T20:46:44.000Z"
    }

----------


Image metadata
_______________


Image metadata example:

.. code-block:: python

   {
      "name": "000000000001.jpg",
      "annotation_status": "Completed",
      "prediction_status": "NotStarted",
      "segmentation_status": "NotStarted",
      "annotator_id": None,
      "annotator_name": None,
      "qa_id": None,
      "qa_name": None,
      "entropy_value": None,
      "approval_status": None,
      "createdAt": "2020-08-18T07:30:06.000Z",
      "updatedAt": "2020-08-18T07:30:06.000Z"
      "is_pinned": 0,
      "...": "...",
   }


----------

.. _ref_class:

Annotation class metadata
_________________________


Annotation class metadata example:

.. code-block:: python

  {
    "id": 4444,
    "name": "Human",
    "color": "#e4542b",
    "attribute_groups": [
       {
          "name": "tall",
          "attributes": [
             {
                "name": "yes"
             },
             {
                "name": "no"
             }
          ]
       },
       {
         "name": "age",
         "attributes": [
             {
               "name": "young"
             },
             {
               "name": "old"
             }
         ]
       }
    ],

    "...": "..."
  }



----------

Team contributor metadata
_________________________

Team contributor metadata example:

.. code-block:: python

  {
    "id": "admin@superannotate.com",
    "first_name": "First Name",
    "last_name": "Last Name",
    "email": "admin@superannotate.com",
    "user_role": 6
    "...": "...",
  }



----------

Annotation JSON helper functions
--------------------------------

.. _ref_converter:

Converting annotation format to and from src.superannotate format
_________________________________________________________________


.. _ref_import_annotation_format:
.. autofunction:: superannotate.import_annotation
.. autofunction:: superannotate.export_annotation
.. autofunction:: superannotate.convert_project_type
.. autofunction:: superannotate.convert_json_version



----------

Working with annotations
________________________

.. _ref_aggregate_annotations_as_df:
.. autofunction:: superannotate.validate_annotations
.. autofunction:: superannotate.aggregate_annotations_as_df

----------

Aggregating class distribution from annotations
_____________________________________________________________

.. autofunction:: superannotate.class_distribution

----------

Utility functions
--------------------------------

.. autofunction:: superannotate.consensus
.. autofunction:: superannotate.benchmark