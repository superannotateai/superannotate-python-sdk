.. _ref_sdk:

API Reference
===================================

.. contents::

Remote functions
----------------

Initialization and authentication
_________________________________

.. autofunction:: superannotate.init

----------

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
.. autofunction:: superannotate.rename_folder
.. autofunction:: superannotate.upload_images_to_project
.. autofunction:: superannotate.attach_image_urls_to_project
.. autofunction:: superannotate.upload_images_from_public_urls_to_project
.. autofunction:: superannotate.upload_images_from_google_cloud_to_project
.. autofunction:: superannotate.upload_images_from_azure_blob_to_project
.. autofunction:: superannotate.upload_image_to_project
.. _ref_upload_images_from_folder_to_project:
.. autofunction:: superannotate.upload_images_from_folder_to_project
.. autofunction:: superannotate.upload_video_to_project
.. autofunction:: superannotate.upload_videos_from_folder_to_project
.. autofunction:: superannotate.attach_video_urls_to_project
.. _ref_upload_annotations_from_folder_to_project:
.. autofunction:: superannotate.upload_annotations_from_folder_to_project
.. autofunction:: superannotate.upload_preannotations_from_folder_to_project
.. autofunction:: superannotate.share_project
.. autofunction:: superannotate.unshare_project
.. autofunction:: superannotate.get_project_settings
.. autofunction:: superannotate.set_project_settings
.. autofunction:: superannotate.get_project_default_image_quality_in_editor
.. autofunction:: superannotate.set_project_default_image_quality_in_editor
.. autofunction:: superannotate.get_project_workflow
.. autofunction:: superannotate.set_project_workflow

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


.. _ref_search_images:
.. autofunction:: superannotate.search_images
.. autofunction:: superannotate.search_images_all_folders
.. autofunction:: superannotate.get_image_metadata
.. autofunction:: superannotate.get_image_bytes
.. autofunction:: superannotate.download_image
.. autofunction:: superannotate.set_image_annotation_status
.. autofunction:: superannotate.set_images_annotation_statuses
.. autofunction:: superannotate.get_image_annotations
.. autofunction:: superannotate.get_image_preannotations
.. autofunction:: superannotate.download_image_annotations
.. autofunction:: superannotate.download_image_preannotations
.. autofunction:: superannotate.upload_image_annotations
.. autofunction:: superannotate.copy_image
.. autofunction:: superannotate.copy_images
.. autofunction:: superannotate.move_image
.. autofunction:: superannotate.move_images
.. autofunction:: superannotate.pin_image
.. autofunction:: superannotate.assign_images
.. autofunction:: superannotate.delete_image
.. autofunction:: superannotate.delete_images
.. autofunction:: superannotate.add_annotation_bbox_to_image
.. autofunction:: superannotate.add_annotation_polygon_to_image
.. autofunction:: superannotate.add_annotation_polyline_to_image
.. autofunction:: superannotate.add_annotation_point_to_image
.. autofunction:: superannotate.add_annotation_ellipse_to_image
.. autofunction:: superannotate.add_annotation_template_to_image
.. autofunction:: superannotate.add_annotation_cuboid_to_image
.. autofunction:: superannotate.add_annotation_comment_to_image
.. autofunction:: superannotate.create_fuse_image

----------

Annotation Classes
__________________

.. autofunction:: superannotate.create_annotation_class
.. _ref_create_annotation_classes_from_classes_json:
.. autofunction:: superannotate.create_annotation_classes_from_classes_json
.. autofunction:: superannotate.get_annotation_class_metadata
.. autofunction:: superannotate.search_annotation_classes
.. autofunction:: superannotate.download_annotation_classes_json
.. autofunction:: superannotate.delete_annotation_class

----------

Team contributors
_________________

.. autofunction:: superannotate.get_team_metadata
.. autofunction:: superannotate.invite_contributor_to_team
.. autofunction:: superannotate.delete_contributor_to_team_invitation

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
     "creator_id": "hovnatan@superannotate.com",
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
     "name": "Aug 17 2020 15:44 Hovnatan.zip",
     "user_id": "hovnatan@gmail.com",
     "status": 2,
     "createdAt": "2020-08-17T11:44:26.000Z",
     "...": "..."
   }


----------

Image metadata
_______________


Image metadata example:

.. code-block:: python

   {
      "name": "000000000001.jpg",
      "annotation_status": "Completed",
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
    "id": "hovnatan@superannotate.com",
    "first_name": "Hovnatan",
    "last_name": "Karapetyan",
    "email": "hovnatan@superannotate.com",
    "user_role": 6
    "...": "...",
  }



----------

Annotation JSON helper functions
--------------------------------

.. _ref_converter:

Converting annotation format to and from SuperAnnotate format
_____________________________________________________________


.. _ref_import_annotation_format:
.. autofunction:: superannotate.import_annotation
.. autofunction:: superannotate.export_annotation
.. autofunction:: superannotate.convert_project_type
.. autofunction:: superannotate.coco_split_dataset
.. autofunction:: superannotate.convert_json_version



----------

Working with annotations
________________________

.. _ref_add_annotation_bbox_to_json:
.. autofunction:: superannotate.add_annotation_bbox_to_json
.. autofunction:: superannotate.add_annotation_polygon_to_json
.. autofunction:: superannotate.add_annotation_polyline_to_json
.. autofunction:: superannotate.add_annotation_point_to_json
.. autofunction:: superannotate.add_annotation_ellipse_to_json
.. autofunction:: superannotate.add_annotation_template_to_json
.. autofunction:: superannotate.add_annotation_cuboid_to_json
.. autofunction:: superannotate.add_annotation_comment_to_json
.. _ref_aggregate_annotations_as_df:
.. autofunction:: superannotate.aggregate_annotations_as_df
.. autofunction:: superannotate.df_to_annotations
.. _ref_filter_annotation_instances:
.. autofunction:: superannotate.filter_annotation_instances
.. autofunction:: superannotate.filter_images_by_comments
.. autofunction:: superannotate.filter_images_by_tags

----------

Aggregating class/attribute distribution from annotations
_____________________________________________________________

.. autofunction:: superannotate.class_distribution
.. autofunction:: superannotate.attribute_distribution

----------

Utility functions
--------------------------------

.. autofunction:: superannotate.dicom_to_rgb_sequence
.. autofunction:: superannotate.consensus
.. autofunction:: superannotate.benchmark
