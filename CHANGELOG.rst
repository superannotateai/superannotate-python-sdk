.. _ref_history:

=======
History
=======

All release highlights of this project will be documented in this file.

4.4.34 - April 11, 2025
_______________________

**Added**

    - ``SAClient.get_integrations`` Added id, createdAt, updatedAt, and creator_id in integration metadata.
    - ``SAClient.list_workflows`` Retrieves all workflows for your team along with their metadata.

**Updated**
    - ``SAClient.get_project_metadata``

**Removed**
    - ``SAClient.get_project_workflow``
    - ``SAClient.set_project_workflow``

4.4.33 - April 1, 2025
______________________

**Added**

    - ``SAClient.get_user_scores`` Retrieves score metadata for a user on a specific item within a project.
    - ``SAClient.user_scores`` Assigns or updates score metadata for a user on a specific item in a project.

**Updated**

    - ``SAClient.prepare_export`` Added option for JSONL download type.
    - ``SAClient.download_annotations`` Added data_spec parameter enabling annotation downloads in JSONL format for multimodal projects.
    - ``SAClient.list_items`` Introduced a new parameter to filter results by item category.
    - ``SAClient.list_users`` Now retrieves a list of users with their scores and includes filtering options. Added an optional project parameter to fetch project-level scores instead of team-level scores.
    - ``SAClient.item_context`` Added information about the ItemContext nested class.
    - ``SAClient.list_projects`` Enhanced docstrings for to improve clarity and usability.

4.4.32 - March 4, 2025
______________________

**Fixed**

    - ``SAClient.item_context`` Fixed an issue where setting a component value would overwrite existing comments and other associated data.

4.4.31 - Feb 27, 2025
_____________________

**Added**

    - Guide for Converting CSV and JSONL Formats.
    - New SDK Functionality Table.

**Updated**

    - ``SAClient.attach_items_from_integrated_storage`` now supports Databricks integration, enabling efficient
        data fetching and mapping from Databricks into SuperAnnotate.

4.4.30 - Feb 13, 2025
_____________________

**Added**

    - ``SAClient.list_users`` method lists contributors with optional custom field filtering.
    - ``SAClient.get_user_metadata`` method retrieves contributor metadata, including option for custom fields.
    - ``SAClient.set_user_custom_field`` method sets a custom field for a contributor.
    - ``SAClient.pause_user_activity`` method pauses a contributor's activity on specified projects.
    - ``SAClient.resume_user_activity`` method resumes a contributor's activity on specified projects.
    - ``SAClient.list_projects`` method lists projects with optional custom field filtering.
    - ``SAClient.set_project_custom_field`` method sets a custom field for a project.

**Updated**

    - ``SAClient.upload_annotations`` added ability to specify the format for processing and transforming annotations before upload, including Multimodal projects.
    - ``SAClient.get_annotations`` added ability to specify the format for processing and transforming annotations before retrieving them.
    - ``SAClient.list_items`` added ability to retrieve item categories.
    - ``SAClient.get_project_metadata`` added ability to retrieve custom fields of projects.


4.4.29 - Dec 26, 2024
________________________
**Added**

    - ``SAClient.get_component_config`` Retrieves the configuration for a given project and component ID.

4.4.28 - Dec 13, 2024
________________________
**Added**

    - ``SAClient.item_context`` creates an “ItemContext” for managing item annotations and metadata.

4.4.27 - Nov 14, 2024
________________________
**Fixed**

    - ``SAClient.attach_items`` fixed chunks handling.


4.4.26 - Oct 29, 2024
________________________

**Added**

    - ``SAClient.copy_items/move_items`` method, added the ability to copy/move categories and duplicate strategies ("skip", "replace", "replace_annotations_only").

**Updated**

    - Fixed `SAClient.get_annotations() To handle annotations that contain all UTF-8 characters.`
    - Renamed project type GenAI to Multimodal

4.4.25 - Oct 7, 2024
________________________

**Added**

    - ``SAClient.create_project`` method, a new ``workflow`` argument has been added to define the workflow for the project.
    - ``SAClient.get_project_steps`` method, added instead of ``get_project_workflow`` function.
    - ``SAClient.set_project_steps`` method, added instead of ``set_project_workflow`` function.
    - ``SAClient.list_items`` method has been added to search for items using advanced filtering criteria.


**Updated**

    - ``SAClient.create_project`` method, removed ``workflows`` argument, use ``set_project_steps`` function instead.
    - ``SAClient.clone_project`` method, removed ``copy_workflow`` argument, use ``set_project_steps`` function instead.
    - ``SAClient.get_project_metadata`` method, removed ``include_workflow`` argument, use ``get_project_steps`` function instead.
    - ``SAClient.get_project_workflow`` method deprecated, use ``get_project_steps`` function instead.
    - ``SAClient.set_project_workflow`` method deprecated, use ``set_project_steps`` function instead.

4.4.24 - July 2, 2024
_______________________

**Removed**

    - ``SAClient.download_model()``
    - ``SAClient.run_prediction()``
    - ``SAClient.search_models()``


4.4.23 - July 4, 2024
_______________________


**Updated**

    - ``SAClient.prepare_export`` added the ability to export GenAI project data to a CSV file.

**Fixed**

    - ``SAClient.upload_priority_scores`` fixed an issue arising from empty arguments

4.4.22 - Jun 13, 2024
_______________________


**Updated**

    - Dependencies, updated ``packaging``, ``superannotate-schemas``.
    - ``SAClient.search_folders`` by multiple statuses.


4.4.21 - May 23, 2024
_______________________


**Updated**

    - Dependencies, removed ``SAClientemail-validator``.
    - ``SAClient.add_items_to_subset`` added GenAI projects support.



4.4.20 - April 11, 2024
_______________________


**Updated**

    - ``SAClient.get_annotations()`` added the ability to retrieve data by project/item IDs.
    - ``SAClient.upload_images_to_project()`` fixed an issue with providing two paths with the same image name.



4.4.19 - February 08, 2024
__________________________


**Updated**

    - ``SAClient.attach_items()`` added the ability to attach items from custom integrated storage.


4.4.18 - January 18, 2024
__________________________


**Updated**

    - Improved error handling.

**Removed**

    -  dependency from ``jsonschema``.

4.4.17 - December 21, 2023
__________________________

**Added**

    - ``SAClient.upload_annotations()`` added default values to the annotations during the upload.

**Updated**

    - Fixed `SAClient.search_project() search with special characters.`
    - ``pandas`` dependency  ``pandas~=2.0``

4.4.16 - November 12, 2023
__________________________

**Added**

    - ``SAClient.download_annotations()`` support for integrated storages.

**Updated**

    - Documentation updates
    - ``pillow`` dependency ``pillow>=9.5,~=10.0``.
    - ``opencv`` dependency  replaced by ``opencv-python-headless~=4.7``.
    - ``pydantic`` dependency ``pydantic>=1.10,!=2.0.*``.

4.4.15 - August 20, 2023
________________________

**Added**

    - Support for `relationship` class types in the document project.


4.4.14 - August 20, 2023
________________________

**Added**

    - New project type support `CustomEditor`.

**Updated**

    - ``SAClient.get_item_by_id()`` Fixed.
    - ``SAClient.consensus()`` Deprecation.

4.4.13 - June 04, 2023
_______________________

**Updated**

    - ``SAClient.download_annotations()`` Replaced `___objects.json` and `___pixel.json` postfixes to `.json`.
    - ``SAClient.set_approval_statuses()`` Added Document project support.
    - ``SAClient.convert_project_type()`` Added required argument `convert_to`.
    - ``SAClient.import_annotation()`` Replaced `___objects.json` and `___pixel.json` postfixes to `.json`.
    - ``SAClient.download_export()`` Replaced `___objects.json` and `___pixel.json` postfixes to `.json`.

**Removed**

    -  ``SAClient.convert_json_version()`` method.

4.4.12 - April 23, 2023
_______________________

**Updated**

    - ``SAClient.get_annotations_per_frame()`` Added interpolation of polygonal and polyline annotations.

**Fixed**

    - ``SAClient.add_contributors_to_project()`` method.
    - ``SAClient.run_prediction()`` method.

**Removed**

    -  ``SAClient.create_project_from_metadata()`` method.
    -  ``SAClient.get_project_image_count()`` method.

4.4.11 - April 2, 2023
______________________

**Added**

    -  ``SAClient.set_project_status()`` method.
    -  ``SAClient.set_folder_status()`` method.

**Updated**

    -  ``SAClient.create_annotation_class()`` added OCR type attribute group support in the vector projects.
    -  ``SAClient.create_annotation_classes_from_classes_json()`` added OCR type attribute group support in the vector projects.

4.4.10 - March 12, 2023
_______________________

**Updated**

    - Configuration file creation flow
    - ``SAClient.search_projects()`` method, removed ``include_complete_image_count`` argument, use ``include_complete_item_count`` instead.
    - ``SAClient.get_project_metadata()`` method, removed ``include_complete_image_count`` argument, use ``include_complete_item_count`` instead.
    - ``SAClient.create_project()`` method to support classes, workflows and instructions_link.

**Fixed**

    - ``SAClient.clone_project()`` method to address the issue of FPS mode is not being copied.

**Deprecated**

    - ``SAClient.create_project_from_metadata()`` method, use ``SAClient.create_project()`` instead.
    - ``SAClient.get_project_image_count()`` method, use ``SAClient.get_project_metadata()`` instead.

**Removed**

    - ``SAClient.class_distribution()`` method
    - ``SAClient.benchmark()`` method

4.4.9 - January 29, 2023
________________________

**Added**

    - ``SAClient.set_approval_statuses`` method function to change the approval status of items (images, audio / videos) in bulk.

**Updated**

    - ``SAClient.convert_project_type`` method updated from Pixel to Vector converter, added polygon holes handling.

4.4.8 - December 25, 2022
____________________________

**Added**

    - New project types ``Tiled``, ``PointCloud``, ``Other``.
    - ``SAClient.get_project_by_id`` method to get project metadata by id.
    - ``SAClient.get_folder_by_id`` method to get folder metadata by id.
    - ``SAClient.get_item_by_id`` method to get item metadata by id.

**Updated**

    - ``SAClient.consensus`` method to compute agreement scores between tag type annotations.

4.4.7 - December 04, 2022
_________________________

**Updated**

    - ``SAClient.search_folders`` method to add a new ``status`` argument for searching folders via status.
    - Schemas for ``Annotation Classes`` and ``Video Annotation`` to support **text** and **numeric input** attribute group types.

**Fixed**

    - ``SAClient.query`` method to address invalid exceptions.
    - ``SAClient.download_export`` method to address the issue with downloading for Windows OS.
    - ``SAClient.attach_items_from_integrated_storage`` method to address "integration not found" error.
    - ``SAClient.aggregate_annotations_as_df`` method to support files without "___objects" in their naming.

**Removed**

    - ``SAClient.add_annotation_bbox_to_image`` method, use ``SAClient.upload_annotations`` instead.
    - ``SAClient.add_annotation_point_to_image`` method, use ``SAClient.upload_annotations`` instead.
    - ``SAClient.add_annotation_comment_to_image`` method, use ``SAClient.upload_annotations`` instead.

4.4.6 - November 23, 2022
_________________________

**Updated**

    - ``SAClient.aggregate_annotations_as_df`` method to aggregate "comment" type instances.
    - ``SAClient.add_annotation_bbox_to_image``, ``SAClient.add_annotation_point_to_image``, ``SAClient.add_annotation_comment_to_image`` methods to add deprecation warnings.

**Fixed**

    - Special characters are being encoded after annotation upload (Windows)
    - ``SAClient.assign_folder`` method to address the invalid argument name.
    - ``SAClient.upload_images_from_folder_to_project`` method to address uploading of more than 500 items.
    - ``SAClient.upload_annotations_from_folder_to_project`` method to address the issue of a folder size being more than 25,5 MB.
    - ``SAClient.download_image`` method to address the KeyError 'id' when ``include_annotations`` is set to ``True``.

**Removed**

    - ``SAClient.upload_preannotations_from_folder_to_project`` method
    - ``SAClient.copy_image`` method

4.4.5 - October 23, 2022
________________________

**Added**

    - ``SAClient.add_items_to_subset`` method to associate given items with a Subset.
    - ``SAClient.upload_annotations`` method to upload annotations in SA format from the system memory.

**Updated**

    - ``SAClient.upload_annotations_from_folder_to_project`` & ``SAClient.upload_image_annotations`` methods to add ``keep_status`` argument to prevent the annotation status from changing to **In Progress** after the annotation upload.
    - Item metadata to add a new key for holding the id of an item.
    - ``SAClient.upload_preannotations_from_folder_to_project`` to add a deprecation warning message.
    - ``SAClient.copy_image`` to add a deprecation warning message.

**Fixed**

    - ``SAClient.validate_annotations`` method.
    - ``SAClient.search_items``, ``SAClient.get_item_metadata`` methods to address defects related to pydantic 1.8.2.
    - A defect related to editor to address the issue of uploading a tag instance without attributes.

4.4.4 - September 11, 2022
__________________________

**Updated**

    - Improvements on working with large files.

**Fixed**

    - ``SAClient.upload_annotations_from_folder_to_project()`` method to address the issue of the disappearing progress bar.
    - ``SAClient.run_prediction()`` method to address the issue of the OCR model.
    - ``SAClient.validate_annotations()`` method to address the issue of missing log messages.
    - ``SAClient.create_project_from_metadata()`` method to address the issue of returning deprecated ``is_multiselect`` key.
    - ``SAClient.get_annotations()`` method to address the issue of returning error messages as annotation dicts.

4.4.2, 4.4.3 - August 21, 2022
______________________________

**Updated**

    - the **schema** of ``classes JSON`` to support new values for the ``"group_type"`` key for a given attribute group. ``"group_type": "radio" | "checklist" | "text" | "numeric"``.
    - the **schema** of ``video annotation JSON`` to support instances that have a ``"tag"`` type.

**Fixed**

    - ``SAClient.get_annotations()`` method to address the issue of working with the large projects.
    - ``SAClient.get_annotations_per_frame()`` method to address the issue of throwing an error on small videos when the fps is set to 1.
    - ``SAClient.upload_annotations_from_folder_to_project()`` to address the issue of timestamp values represented in seconds for the ``"lastAction"``.
    - ``SAClient.download_export()`` method to address the issue of empty logs.
    - ``SAClient.clone_project()`` method to address the issue of having a corrupted project clone, when the source project has a keypoint workflow.

4.4.1 - July 24, 2022
_____________________

**Added**

    - ``SAClient.create_custom_fields()`` method to create/add new custom fields to a project’s custom field schema.
    - ``SAClient.get_custom_fields()`` method to get a project’s custom field schema.
    - ``SAClient.delete_custom_fields()`` method to remove existing custom fields from a project’s custom field schema.
    - ``SAClient.upload_custom_values()`` method to attach custom field-value pairs to items.
    - ``SAClient.delete_custom_values()`` method to remove custom field-value pairs from items.

**Updated**

    - The **schema** of ``classes JSON`` to support the new ``"default_value"`` key to set a default attribute(s) for a given attribute group.
    - ``SAClient.get_item_metadata()`` method to add a new input argument ``include_custom_metadata`` to return custom metadata in the result items.
    - ``SAClient.search_items()`` method to add a new input argument ``include_custom_metadata`` to return custom metadata in the result items.
    - ``SAClient.query()`` method to return custom metadata in the result items.

**Fixed**

    - ``SAClient`` class to address the system crash that occurs on instantiation via ``config.json`` file.
    - ``SAClient.query()`` method to address the issue of not returning more than 50 items.
    - ``SAClient.upload_annotations_from_folder_to_project()`` to address the issue of some fields not being auto populated after the upload is finished.
    - ``SAClient.get_folder_metadata()``, ``SAClient.search_folders()`` to address the issue of transforming the ‘+’ sign in a folder to a whitespace.

**Removed**

    - ``superannotate.assign_images()`` function. Please use the ``SAClient.assign_items()`` method instead.
    - ``superannotate.unassign_images()`` function. Please use the ``SAClient.unassign_items()`` method instead.
    - ``superannotate.delete_images()`` function. Please use the ``SAClient.delete_items()`` method instead.

4.4.0 - July 03, 2022
_____________________

**Added**

    - ``superannotate.SAClient()`` class to instantiate team-level authentication and inheriting methods to access the back-end.
    - ``SAClient.download_annotations()`` method to download annotations without preparing an Export object.
    - ``SAClient.get_subsets()`` method to get the existing subsets for a given project.
    - ``SAClient.assign_items()`` method to assign items in a given project to annotators or quality specialists.
    - ``SAClient.unassign_items()`` method to remove assignments from items.
    - ``SAClient.delete_items()`` method to delete items in a given project.

**Updated**

    - ``JSON Schema`` for video annotations to version ``1.0.45`` to show **polygon** and **polyline** annotations.
    - ``SAClient.get_annotations_per_frame()`` method to show **polygon** and **polyline** annotations.
    - ``SAClient.get_annotations_per_frame()`` method to pick instances closer to a given **frame start** instead of the **median**.
    - ``SAClient.query()`` method to add the ``subset`` argument to support querying in a subset.

**Fixed**

    - ``SAClient.set_annotation_statuses()`` method to address the issue occurring with more than 500 items.
    - ``SAClient.get_annotations()`` method to address the ``PayloadError`` occurring with more than 20000 items.
    - ``SAClient.get_annotations()`` method to address the missing ``'duration'`` and ``'tags'`` keys for newly uploaded and unannotated videos.
    - ``SAClient.get_annotations_per_frame()`` method to address missing ``'duration'`` and ``'tags'`` keys for newly uploaded and unannotated videos.
    - ``SAClient.get_annotations_per_frame()`` method to address the wrong ``classId`` value for unclassified instances.

**Removed**

    - ``superannotate.init()`` function. Please instantiate ``superannotate.SAClient()`` class to authenticate.
    - ``superannotate.set_image_annotation_status()`` function. Please use the ``SAClient.set_annotation_statuses()`` method instead.
    - ``superannotate.set_images_annotations_statuses()`` function. Please use the ``SAClient.set_annotation_statuses()`` method instead.

4.3.4 - May 22, 2022
____________________

**Updated**

    - ``JSON Schema`` for video annotations to version ``x`` to reflect point annotations.
    - ``superannotate.download_export()`` function to preserve SA folder structure while downloading to S3 bucket.
    - ``superannotate.get_item_metadata()`` function to have string type values instead of int type for the ``approval_status`` key.
    - ``superannotate.get_item_metadata()`` function to change the value for the ``path`` key in the item metadata from ``project/folder/item`` format to ``project/folder``.
    - ``superannotate.get_item_metadata()`` function to add the ``is_pinned`` key in the returned metadata.
    - ``superannotate.clone_project()`` function to have ``NotStarted`` project status for the newly created project.

**Fixed**

    - ``superannotate.query()`` function to address the missing value for the ``path`` key.
    - ``superannotate.import_annotation()`` function to address the extension issue with JPEG files while converting from ``VOC`` to SA.
    - ``superannotate.import_annotation()`` function to address int type pointlabels in the converted ``JSON`` from ``COCO`` to SA.
    - ``superannotate_get_annotations()`` & ``superannotate.add_annotation_comment_to_image()`` to address the issue with ``asyncio`` occurring on Windows.
    - ``superannotate.set_image_annotation_status()`` function add a deprecation warning.
    - ``superannotate.set_images_annotation_statuses()`` function add a deprecation warning.

**Removed**

    - ``share_projects()`` function.
    - ``superannotate.attach_image_urls_to_project()`` function. Please use the ``superannotate.attach_items()`` function instead.
    - ``superannotate.attach_document_urls_to_project()`` function. Please use the ``superannotate.attach_items()`` function instead.
    - ``superannotate.attach_video_urls_to_project()`` function. Please use the ``superannotate.attach_items()`` function instead.
    - ``superannotate.copy_images()`` function. Please use the ``superannotate.copy_items()`` function instead.
    - ``superannotate.move_images()`` function. Please use the ``superannotate.move_items()`` function instead.

4.3.3 - May 01 2022
___________________

**Added**

    - ``attach_items()`` function to link items (images, videos, and documents) from external storages to SuperAnnotate using URLs.
    - ``copy_items()`` function to copy items (images, videos, and documents) in bulk between folders in a project.
    - ``move_items()`` function to move items (images, videos, and documents) in bulk between folders in a project.
    - ``set_annotation_statuses()`` function to change the annotation status of items (images, videos, and documents) in bulk.

**Updated**

    - ``aggregate_annotations_as_df()`` function now supports Text Projects.

**Fixed**

    - ``validate_annotations()`` function to accept only numeric type values for the ``points`` field.
    - ``prepare_export()`` function to address the issue when the entire project is prepared when a wrong folder name is provided.
    - ``search_team_contributors()`` function to address the error message when ``email`` parameter is used.
    - ``get_item_metadata()`` to address the issue with approved/disapproved items.

**Removed**

    - ``get_project_and_folder_metadata()`` function.
    - ``get_image_metadata()`` function. Please use ``get_item_metadata()`` instead.
    - ``search_images()`` function. Please use ``search_items()`` instead.
    - ``search images_all_folders()`` function. Please use ``search_items()`` instead.

4.3.2 - April 10 2022
_____________________

**Added**

    - ``query()`` function to run SAQuL queries via SDK.
    - ``search_items()`` function to search items by various filtering criteria for all supported project types. ``search_images()`` and ``search_images_all_folders()`` functions will be deprecated.
    - ``get_item_metadata()`` function to get item metadata for all supported project types. ``get_image_metadata()`` will be deprecated.

**Updated**

    - ``search_projects()`` function to add new parameter that gives an option to filter projects by project ``status``.
    - ``get_annotation_per_frame()`` function to add a unique identifier for each annotation instance.

**Fixed**

    - pixel annotations to address the issue with the hex code.
    - ``sa.validate_annotations()`` function to address the incorrect error message.
    - ``create_project_from_metadata()`` function to address the issue with instructions.

**Removed**

    - ``get_image_annotations()`` function. Please use ``get_annotations()``
    - ``upload_images_from_public_urls()`` function.

4.3.1 - March 20 2022
_____________________

**Added**

    - ``get_integrations()`` to list all existing integrations with cloud storages.
    - ``attach_items_from_integrated_storage()`` to attach items from an integrated cloud storage.
    - ``upload_priority_scores()`` to set priority scores for a given list of items.

**Updated**

    - ``JSON Schema`` to version ``1.0.40`` to add instance type differentiation for text annotations and ``"exclude"`` key for subtracted polygon instances for image annotations.
    - ``validate_annotations()`` to validate text and image annotations based on JSON schema version ``1.0.40``.
    - ``get_annotations()`` to get annotation instances based on JSON schema version ``1.0.40``.
    - ``prepare_export()`` to prepare for the download annotations with based on JSON schema version ``1.0.40``.
    - ``upload_annotations_from_folder_to_project()`` & ``upload_preannotations_from_folder_to_project()`` to handle upload based on JSON schema version ``1.0.40``.
    - ``create_project()`` to add ``"status"`` key in returned metadata.
    - ``get_project_metadata()`` to add ``"status"`` key.
    - ``create_project_from_project_metadata()`` to make ``"description"`` key not required.
    - ``clone_project()`` to add generic ``"description"``.

**Fixed**

    - ``sa.get_annotations_per_frame()`` to take correct attributes.
    - ``sa.get_annotations_per_frame()`` & ``get_annotations()`` to eliminate duplicate instances.

4.3.0 - Feb 27 2022
___________________

**Added**

    - ``get_annotations`` to load annotations for the list of items.
    - ``get_annotations_per_frame`` to generate frame by frame annotations for the given video.

**Updated**

    - ``get_image_annotations()`` to reference ``get_annotations()``.
    - ``create_annotation_class()`` to add ``class_type`` in parameters to specify class type on creation.
    - ``create_annotation_classes_from_classes_json()`` to handle class type in classes JSON.
    - ``search_annotation_classes()`` to return class type in metadata.
    - ``upload_annotations_from_folder_to_project()`` to handle tag annotations.
    - ``upload_preannotations_from_folder_to_project()`` to handle tag annotations.
    - ``upload_image_annotations()`` to handle tag annotations.
    - ``validate_annotations()`` to validate vector annotation schema with tag instances.
    - ``aggregate_annotations_as_df()`` to handle tag annotations in annotations df.
    - ``class_distribution()`` to handle class distribution of tag instances.
    - ``upload_images_from_public_urls()`` for deprecation log.

**Fixed**

    - ``upload_images_from_folder_to_project()`` to upload images without invalid rotation.
    - ``upload-annotations`` CLI to upload annotations to specified folder.
    - ``create_project_from_metadata()`` to setup image quality and workflow from given metadata.
    - ``get_project_metadata()`` to return information on project contributors.
    - ``get_project_metadata()`` to return number of completed images in project root.
    - ``get_project_workflow()`` to return ``className`` in project workflow.
    -  file handler permissions in GColab at ``import`` stage of the package.

4.2.9 - Jan 30 2022
___________________

**Added**

    - ``superannotate_schemas`` as a stand alone package on annotation schemas.

**Updated**

    - ``upload_annotations_from_folder_to_project()`` to reference the ``validate_annotations()``.
    - ``upload_videos_from_folder_to_project()`` to remove code duplications.
    - ``clone_project()`` to set upload state of clone project to initial.

**Fixed**

    - ``validate_annotations()`` to fix rotated bounding box schema.

**Removed**

    - Third party logs from logging mechanism.

4.2.8 - Jan 9 2022
__________________

**Added**

    - ``invite_contributers_to_team()`` for bulk team invite.
    - ``add_contributors_to_project()`` for bulk project sharing.

**Updated**

    - ``upload_images_from_folder_to_project()`` for non existing S3 path handling.
    - ``upload_annotations_from_folder_to_project()`` for template name and class processing on template annotation upload.
    - ``add_annotation_comment_to_image()`` for unrecognized author processing.
    - ``add_annotation_point_to_image()`` for valid point addition on empty state.
    - ``add_annotation_bbox_to_image()`` for valid bbox addition on empty state.
    - ``add_annotation_comment_to_image()`` for valid comment addition on empty state.

**Fixed**

    - ``superannotatecli upload_images`` to accept default list of image extensions.

**Removed**

    - ``invite_contributor_to_team()`` use ``invite_contributors_to_team()`` instead.

4.2.7 - Dec 12 2021
___________________

**Added**

    - Logging mechanism.

**Updated**

    - Cloning projects with attached URLs.
    - Improve relation between image status and annotations.
    - Deprecate functions of zero usage.

**Fixed**

    - Small bug fix & enhancements.

4.2.6 - Nov 21 2021
___________________

**Added**

    - Validation schemas for annotations.
    - Dataframe aggregation for video projects.

**Fixed**

    - Minor bug fixes and enhancements.

4.2.4 - Nov 2 2021
__________________

**Fixed**

    - Minor bug fixes and enhancements.

4.2.3 - Oct 31 2021
___________________

**Fixed**

    - Minor bug fixes and enhancements.

4.2.2 - Oct 22 2021
___________________

**Fixed**

    - Minor bug fixes and enhancements.

4.2.1 - Oct 13 2021
___________________

**Fixed**

    - ``init`` functionality.
    - ``upload_annotation`` functionality.

4.2.0 - Oct 10 2021
___________________

**Added**

    - ``delete_annotations()`` for bulk annotation delete.

**Updated**

    - Project/folder limitations.

**Fixed**

    - Refactor and major bug fix.

4.1.9 - Sep 22 2021
___________________

**Added**

    - Text project support.

4.1.8 - Aug 15 2021
___________________

**Added**

    - Video project release.

4.1.7 - Aug 1 2021
__________________

**Fixed**

    - Video upload refinements.

4.1.6 - Jul 19 2021
___________________

**Added**

    - Training/Test data with folder structure.
    - Token validation.

**Updated**

    - Add success property on mixpanel events.

**Fixed**

    - Upload template enhancements.

4.1.5 - Jun 16 2021
___________________

**Added**

    - Folder assignment.

**Updated**

    - COCO keypoint enhancements.

4.1.4 - May 26 2021
___________________

**Added**

    - Mixpanel Integration.

**Updated**

    - Image upload enhancements.
    - Video upload enhancements.
    - Annotation upload enhancements.
    - Consensus enhancements.
    - Image copy/move enhancements.
    - COCO import/export enhancements.
    - AWS region enhancements.

4.1.3 - Apr 19 2021
___________________

**Added**

    - Folder limitations.

4.1.2 - Apr 1 2021
__________________

**Fixed**

    - Video upload to folder.

4.1.1 - Mar 31 2021
___________________

**Added**

    - Attach image URLs.

4.1.0 - Mar 22 2021
___________________

**Added**

    - Folder structure on platform.

4.0.1 - Mar 15 2021
___________________

**Updated**

    - The FPS change during video upload has more stable frame choosing algorithm now.

4.0.0 - Feb 28 2021
___________________

**Updated**

    - Improved image storage structure on platform, which requires this upgrade in SDK. This change in platform is backward incompatible with previous versions of SDK.

Changelog not maintained before version 4.0.0.
