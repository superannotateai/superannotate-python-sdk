==========
SAClient interface
==========

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
.. automethod:: superannotate.SAClient.get_project_by_id
.. automethod:: superannotate.SAClient.get_project_metadata
.. automethod:: superannotate.SAClient.get_project_image_count
.. automethod:: superannotate.SAClient.search_folders
.. automethod:: superannotate.SAClient.assign_folder
.. automethod:: superannotate.SAClient.unassign_folder
.. automethod:: superannotate.SAClient.get_folder_by_id
.. automethod:: superannotate.SAClient.get_folder_metadata
.. automethod:: superannotate.SAClient.create_folder
.. automethod:: superannotate.SAClient.delete_folders
.. automethod:: superannotate.SAClient.upload_images_to_project
.. automethod:: superannotate.SAClient.attach_items_from_integrated_storage
.. automethod:: superannotate.SAClient.upload_image_to_project
.. automethod:: superannotate.SAClient.upload_annotations
.. automethod:: superannotate.SAClient.delete_annotations
.. _ref_upload_images_from_folder_to_project:
.. automethod:: superannotate.SAClient.upload_images_from_folder_to_project
.. automethod:: superannotate.SAClient.upload_video_to_project
.. automethod:: superannotate.SAClient.upload_videos_from_folder_to_project
.. _ref_upload_annotations_from_folder_to_project:
.. automethod:: superannotate.SAClient.upload_annotations_from_folder_to_project
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
.. automethod:: superannotate.SAClient.get_item_by_id
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
.. automethod:: superannotate.SAClient.set_approval_statuses
.. automethod:: superannotate.SAClient.set_approval

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
.. automethod:: superannotate.SAClient.add_items_to_subset

----------

Images
______


.. _ref_search_images:
.. automethod:: superannotate.SAClient.download_image
.. automethod:: superannotate.SAClient.download_image_annotations
.. automethod:: superannotate.SAClient.upload_image_annotations
.. automethod:: superannotate.SAClient.pin_image
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