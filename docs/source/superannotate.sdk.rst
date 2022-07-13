.. _ref_sdk:

API Reference
===================================

.. contents::

Remote functions
----------------

Instantiation and authentication
_________________________________

.. autoclass:: superannotate.SAClient


Projects
________

.. _ref_search_projects:
.. automethod:: superannotate.SAClient.search_projects
.. automethod:: superannotate.SAClient.create_project
.. automethod:: superannotate.SAClient.create_project_from_metadata
.. automethod:: superannotate.SAClient.clone_project
.. automethod:: superannotate.SAClient.delete_project
.. automethod:: superannotate.SAClient.rename_project
.. _ref_get_project_metadata:
.. automethod:: superannotate.SAClient.get_project_metadata
.. automethod:: superannotate.SAClient.get_project_image_count
.. automethod:: superannotate.SAClient.search_folders
.. automethod:: superannotate.SAClient.get_folder_metadata
.. automethod:: superannotate.SAClient.create_folder
.. automethod:: superannotate.SAClient.delete_folders
.. automethod:: superannotate.SAClient.upload_images_to_project
.. automethod:: superannotate.SAClient.attach_items_from_integrated_storage
.. automethod:: superannotate.SAClient.upload_image_to_project
.. automethod:: superannotate.SAClient.delete_annotations
.. _ref_upload_images_from_folder_to_project:
.. automethod:: superannotate.SAClient.upload_images_from_folder_to_project
.. automethod:: superannotate.SAClient.upload_video_to_project
.. automethod:: superannotate.SAClient.upload_videos_from_folder_to_project
.. _ref_upload_annotations_from_folder_to_project:
.. automethod:: superannotate.SAClient.upload_annotations_from_folder_to_project
.. automethod:: superannotate.SAClient.upload_preannotations_from_folder_to_project
.. automethod:: superannotate.SAClient.add_contributors_to_project
.. automethod:: superannotate.SAClient.get_project_settings
.. automethod:: superannotate.SAClient.set_project_default_image_quality_in_editor
.. automethod:: superannotate.SAClient.get_project_workflow
.. automethod:: superannotate.SAClient.set_project_workflow

----------

Exports
_______

.. automethod:: superannotate.SAClient.prepare_export
.. automethod:: superannotate.SAClient.get_annotations
.. automethod:: superannotate.SAClient.get_annotations_per_frame
.. _ref_download_export:
.. automethod:: superannotate.SAClient.download_export
.. automethod:: superannotate.SAClient.get_exports

----------

Items
______

.. automethod:: superannotate.SAClient.query
.. automethod:: superannotate.SAClient.search_items
.. automethod:: superannotate.SAClient.download_annotations
.. automethod:: superannotate.SAClient.attach_items
.. automethod:: superannotate.SAClient.copy_items
.. automethod:: superannotate.SAClient.move_items
.. automethod:: superannotate.SAClient.delete_items
.. automethod:: superannotate.SAClient.assign_items
.. automethod:: superannotate.SAClient.unassign_items
.. automethod:: superannotate.SAClient.get_item_metadata
.. automethod:: superannotate.SAClient.set_annotation_statuses

----------

Custom Metadata
______

.. automethod:: superannotate.SAClient.create_custom_fields
.. automethod:: superannotate.SAClient.get_custom_fields
.. automethod:: superannotate.SAClient.delete_custom_fields
.. automethod:: superannotate.SAClient.upload_custom_values
.. automethod:: superannotate.SAClient.delete_custom_values

----------

Subsets
______

.. automethod:: superannotate.SAClient.get_subsets

----------

Images
______


.. _ref_search_images:
.. automethod:: superannotate.SAClient.download_image
.. automethod:: superannotate.SAClient.download_image_annotations
.. automethod:: superannotate.SAClient.upload_image_annotations
.. automethod:: superannotate.SAClient.copy_image
.. automethod:: superannotate.SAClient.pin_image
.. automethod:: superannotate.SAClient.add_annotation_bbox_to_image
.. automethod:: superannotate.SAClient.add_annotation_point_to_image
.. automethod:: superannotate.SAClient.add_annotation_comment_to_image
.. automethod:: superannotate.SAClient.upload_priority_scores

----------

Annotation Classes
__________________

.. automethod:: superannotate.SAClient.create_annotation_class
.. _ref_create_annotation_classes_from_classes_json:
.. automethod:: superannotate.SAClient.create_annotation_classes_from_classes_json
.. automethod:: superannotate.SAClient.search_annotation_classes
.. automethod:: superannotate.SAClient.download_annotation_classes_json
.. automethod:: superannotate.SAClient.delete_annotation_class

----------

Team
_________________

.. automethod:: superannotate.SAClient.get_team_metadata
.. automethod:: superannotate.SAClient.get_integrations
.. automethod:: superannotate.SAClient.invite_contributors_to_team
.. automethod:: superannotate.SAClient.search_team_contributors

----------

Neural Network
_______________

.. automethod:: superannotate.SAClient.download_model
.. automethod:: superannotate.SAClient.run_prediction
.. automethod:: superannotate.SAClient.search_models

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
     "status": "NotStarted",
     "...": "..."
   }


----------

Setting metadata
_________________

Setting metadata example:

.. code-block:: python

   {
    "attribute": "FrameRate",
    "value": 3
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
______________________

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

Priority score
_______________


Priority score example:

.. code-block:: python

   {
        "name" : "image1.png",
        "priority": 0.567
    }


----------

Attachment
_______________


Attachment example:

.. code-block:: python

   {
      "url": "https://sa-public-files.s3.../text_file_example_1.jpeg",
      "name": "example.jpeg"
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
.. automethod:: superannotate.SAClient.validate_annotations
.. automethod:: superannotate.SAClient.aggregate_annotations_as_df

----------

Aggregating class distribution from annotations
_____________________________________________________________

.. autofunction:: superannotate.class_distribution

----------

Utility functions
--------------------------------

.. autofunction:: superannotate.SAClient.consensus
.. autofunction:: superannotate.SAClient.benchmark
