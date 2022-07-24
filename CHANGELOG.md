# Changelog 
All release highlights of this project will be documented in this file.
## 4.4.1 - July 24, 2022
### Added
- `SAClient.create_custom_fields()` _method_ to create/add new custom fields to a project’s custom field schema.
- `SAClient.get_custom_fields()` _method_ to get a project’s custom field schema.
- `SAClient.delete_custom_fields()` _method_ to remove existing custom fields from a project’s custom field schema.
- `SAClient.upload_custom_values()` _method_ to attach custom field-value pairs to items.
- `SAClient.delete_custom_values()` _method_ to remove custom field-value pairs from items.
### Updated
- the **schema** of `classes JSON` to support the new `"default_value"` key to set a default attribute(s) for a given attribute group.
- `SAClient.get_item_metadata()` _method_ to add a new input argument `include_custom_metadata` to return custom metadata in the result items.
- `SAClient.search_items()` _method_ to add a new input argument `include_custom_metadata` to return custom metadata in the result items.
- `SAClient.query()` _method_ to return custom metadata in the result items.
### Fixed
- `SAClient` _class_ to address the system crash that occurs on instantiation via `config.json` file.
- `SAClient.query()` _method_ to address the issue of not returning more than 50 items.
- `SAClient.upload_annotations_from_folder_to_project()` to address the issue of some fields not being auto populated after the upload is finished.
- `SAClient.get_folder_metadata()`, `SAClient.search_folders()` to address the issue of transforming the ‘+’ sign in a folder to a whitespace.
### Removed
- `superannotate.assign_images()` _function_. Please use the `SAClient.assign_items()` _method_ instead.
- `superannotate.unassign_images()` _function_. Please use the `SAClient.unassign_items()` _method_ instead.
- `superannotate.delete_images()` _function_. Please use the `SAClient.delete_items()` _method_ instead.
###
## 4.4.0 - July 03, 2022
### Added
- `superannotate.SAClient()` _class_ to instantiate team-level authentication and inheriting methods to access the back-end.
- `SAClient.download_annotations()` _method_ to download annotations without preparing an Export object.
- `SAClient.get_subsets()` _method_ to get the existing subsets for a given project.
- `SAClient.assign_items()` _method_ to assign items in a given project to annotators or quality specialists.
- `SAClient.unassign_items()` _method_ to remove assignments from items.
- `SAClient.delete_items()` _method_ to delete items in a given project.
### Updated
- `JSON Schema` for video annotations to version `1.0.45` to show **polygon** and **polyline** annotations.
- `SAClient.get_annotations_per_frame()` _method_ to show **polygon** and **polyline** annotations.
- `SAClient.get_annotations_per_frame()` _method_ to pick instances closer to a given **frame start** instead of the **median**.
- `SAClient.query()` _method_ to add the `subset` argument to support querying in a subset.
### Fixed
- `SAClient.set_annotation_statuses()` _method_ to address the issue occurring with more than 500 items.
- `SAClient.get_annotations()` _method_ to address the `PayloadError` occurring with more than 20000 items.
- `SAClient.get_annotations()` _method_ to address the missing `'duration'` and `'tags'` keys for newly uploaded and unannotated videos.
- `SAClient.get_annotations_per_frame()` _method_ to address missing `'duration'` and `'tags'` keys for newly uploaded and unannotated videos.
- `SAClient.get_annotations_per_frame()` _method_ to address the wrong `classId` value for unclassified instances.
### Removed
- `superannotate.init()` _function_. Please instantiate `superannotate.SAClient()` _class_ to authenticate.
- `superannotate.set_image_annotation_status()` _function_. Please use the `SAClient.set_annotation_statuses()` _method_ instead.
- `superannotate.set_images_annotations_statuses()` _function_. Please use the `SAClient.set_annotation_statuses()` _method_ instead.
## 4.3.4 - May 22, 2022
### Updated
- `JSON Schema` for video annotations to version `x` to reflect point annotations.
- `superannotate.download_export()` function to preserve SA folder structure while downloading to S3 bucket.
- `superannotate.get_item_metadata()` function to have string type values instead of int type for the `approval_status` key.
- `superannotate.get_item_metadata()` function to change the value for the `path` key in the item metadata from `project/folder/item` format to `project/folder`.
- `superannotate.get_item_metadata()` function to add the `is_pinned` key in the returned metadata.
- `superannotate.clone_project()` function to have `NotStarted` project status for the newly created project.
### Fixed
- `superannotate.query()` function to address the missing value for the `path` key.
- `superannotate.import_annotation()` function to address the extension issue with JPEG files while converting from `VOC` to SA.
- `superannotate.import_annotation()` function to address int type pointlabels in the converted `JSON` from `COCO` to SA.
- `superannotate_get_annotations()` & `superannotate.add_annotation_comment_to_image()` to address the issue with `asyncio` occuring on Windows.
- `superannotate.set_image_annotation_status()` function add a deprecation warning.
- `superannotate.set_images_annotation_statuses()` function add a deprecation warning.
### Removed
- `share_projects()` function.
- `superannotate.attach_image_urls_to_project()` function. Please use the `superannotate.attach_items()` function instead.
- `superannotate.attach_document_urls_to_project()` function. Please use the `superannotate.attach_items()` function instead.
- `superannotate.attach_video_urls_to_project()` function. Please use the `superannotate.attach_items()` function instead.
- `superannotate.copy_images()` function. Please use the `superannotate.copy_items()` function instead.
- `superannotate.move_images()` function. Please use the `superannotate.move_items()` function instead.
###
## 4.3.3 - May 01 2022
### Added
- `attach_items()` function to link items (images, videos, and documents) from external storages to SuperAnnotate using URLs.
- `copy_items()` function to copy items (images, videos, and documents) in bulk between folders in a project.
- `move_items()` function to move items (images, videos, and documents) in bulk between folders in a project.
- `set_annotation_statuses()` function to change the annotation status of items (images, videos, and documents) in bulk.
### Updated
- `aggregate_annotations_as_df()` function now supports Text Projects.
### Fixed
- `validate_annotations()` function to accept only numeric type values for the `points` field.
- `prepare_export()` function to address the issue when the entire project is prepared when a wrong folder name is provided.
- `search_team_contributors()` function to address the error message when `email` parameter is used.
- `get_item_metadata()` to address the issue with approved/disapproved items.
### Removed
- `get_project_and_folder_metadata()` function.
- `get_image_metadata()` function. Please use `get_item_metadata()` instead.
- `search_images()` function. Please use `search_items()` instead.
- `search images_all_folders()` function. Please use `search_items()` instead.
###
## 4.3.2 - April 10 2022
### Added
- `query()` function to run SAQuL queries via SDK.
- `search_items()` function to search items by various filtering criteria for all supported project types. `search_images()` and `search_images_all_folders()` functions will be deprecated.
- `get_item_metadata()` function to get item metadata for all supported project types. `get_image_metadata()` will be deprecated.
### Updated
- `search_projects()` function to add new parameter that gives an option to filter projects by project `status`.
- `get_annotation_per_frame()` function to add a unique identifier for each annotation instance.
### Fixed
- pixel annotations to address the issue with the hex code.
- `sa.validate_annotations()` function to address the incorrect error message.
- `create_project_from_metadata()` function to address the issue with instructions.
### Removed
- `get_image_annotations()` function. Please use `get_annotations()`
- `upload_images_from_public_urls()` function.
###
## 4.3.1 - March 20 2022
### Added
- `get_integrations()` to list all existing integrations with cloud storages.
- `attach_items_from_integrated_storage()` to attach items from an integrated cloud storage.
- `upload_priority_scores()` to set priority scores for a given list of items.
### Updated
- `JSON Schema` to version `1.0.40` to add instance type differentiation for text annotations and `"exclude"` key for subtracted polygon instances for image annotations. 
- `validate_annotations()` to validate text and image annotations based on JSON schema version `1.0.40`.
- `get_annotations()` to get annotation instances based on JSON schema version `1.0.40`.
- `prepare_export()` to prepare for the download annotations with based on JSON schema version `1.0.40`.
- `upload_annotations_from_folder_to_project()` & `upload_preannotations_from_folder_to_project()` to handle upload based on JSON schema version `1.0.40`.
- `create_project()` to add `"status"` key in returned metadata.
- `get_project_metadata()` to add `"status"` key.
- `create_project_from_project_metadata()` to make `"description"` key not required.
- `clone_project()` to add generic `"description"`.
### Fixed
- `sa.get_annotations_per_frame()` to take correct attributes.
- `sa.get_annotations_per_frame()` & `get_annotations()` to eliminate duplicate instances.
###
## 4.3.0 - Feb 27 2022
### Added
- `get_annotations` to load annotations for the list of items.
- `get_annotations_per_frame` to generate frame by frame annotations for the given video.
### Updated
- `get_image_annotations()` to reference `get_annotations()`.
- `create_annotation_class()` to add `class_type` in parameters to specify class type on creation.
- `create_annotation_classes_from_classes_json()` to handle class type in classes JSON. 
- `search_annotation_classes()` to return class type in metadata. 
- `upload_annotations_from_folder_to_project()` to handle tag annotations.
- `upload_preannotations_from_folder_to_project()` to handle tag annotations.
- `upload_image_annotations()` to handle tag annotations.
- `validate_annotations()` to validate vector annotation schema with tag instances.
- `aggregate_annotations_as_df()` to handle tag annotations in annotations df.
- `class_distribution()` to handle class distribution of tag instances.
- `upload_images_from_public_urls()` for deprecation log.
### Fixed
- `upload_images_from_folder_to_project()` to upload images without invalid rotation.
- `upload-annotations` CLI to upload annotations to specified folder.
- `create_project_from_metadata()` to setup image quality and workflow from given metadata.
- `get_project_metadata()` to return information on project contributors.
- `get_project_metadata()` to return number of completed images in project root.
- `get_project_workflow()` to return `className` in project workflow.
-  file handler permissions in GColab at `import` stage of the package.
###
## 4.2.9 - Jan 30 2022
### Added
- `superannotate_schemas` as a stand alone package on annotation schemas.
### Updated
- `upload_annotations_from_folder_to_project()` to reference the `validate_annotations()`.
- `upload_videos_from_folder_to_project()` to remove code duplications.
- `clone_project()` to set upload state of clone project to inital. 
### Fixed
- `validate_annotations()` to fix rotated bounding box schema. 
### Removed
- Third party logs from logging mechanism.
###
## 4.2.8 - Jan 9 2022
### Added
- `invite_contributers_to_team()` for bulk team invite.
- `add_contributors_to_project()` for bulk project sharing.
### Updated
- `upload_images_from_folder_to_project()` for non existing S3 path handling.
- `upload_annotations_from_folder_to_project()` for template name and class processing on template annotation upload.
- `add_annotation_comment_to_image()` for unrecognized author processing.
- `add_annotation_point_to_image()` for valid point addition on empty state.
- `add_annotation_bbox_to_image()` for valid bbox addition on empty state.
- `add_annotation_comment_to_image()` for valid comment addition on empty state.
### Fixed
- `superannotatecli upload_images` to accept default list of image extensions.
### Removed
- `invite_contributor_to_team()` use `invite_contributors_to_team()` instead.
###
## 4.2.7 - Dec 12 2021
### Added
- Logging mechanism.
### Updated
- Cloning projects with attached URLs.
- Improve relation between image status and annotations.
- Deprecate functions of zero usage.
### Fixed
- Small bug fix & enhancements.
###
## 4.2.6 - Nov 21 2021
### Added
- Validation schemas for annotations. 
- Dataframe aggregation for video projects.
### Fixed
- Minor bug fixes and enhancements.  
###
## 4.2.4 - Nov 2 2021
### Fixed
- Minor bug fixes and enhancements.  
###
## 4.2.3 - Oct 31 2021
### Fixed
- Minor bug fixes and enhancements.  
###
## 4.2.2 - Oct 22 2021
### Fixed
- Minor bug fixes and enhancements.  
###
## 4.2.1 - Oct 13 2021
### Fixed
- `init` functionality.
- `upload_annotation` functionality.
###
## 4.2.0 - Oct 10 2021
### Added
- `delete_annotations()` for bulk annotation delete. 
### Updated
- Project/folder limitations.
### Fixed
- Refactor and major bug fix.
## 4.1.9 - Sep 22 2021
### Added
- Text project support.
## 4.1.8 - Aug 15 2021
### Added
- Video project release.
###
## 4.1.7 - Aug 1 2021 
### Fixed
- Video upload refinements.
###
## 4.1.6 - Jul 19 2021
### Added
- Training/Test data with folder structure.
- Token validation.
### Updated
- Add success property on mixpanel events.
### Fixed
- Upload template enhancements.
###
## 4.1.5 - Jun 16 2021
### Added
- Folder assignment.
### Updated
- COCO keypoint enhancements.
###
## 4.1.4 - May 26 2021
### Added
- Mixpanel Integration.
### Updated
- Image upload enhancements.
- Video upload enhancements.
- Annotation upload enhancements.
- Consensus enhancements.
- Image copy/move enhancements.
- COCO import/export enhancements.
- AWS region enhancements.
###
## 4.1.3 - Apr 19 2021
### Added
- Folder limitations.
###
## 4.1.2 - Apr 1 2021
### Fixed
- Video upload to folder.
###
## 4.1.1 - Mar 31 2021
### Added
- Attach image URLs.
###
## 4.1.0 - Mar 22 2021
### Added
- Folder structure on platform. 
###
## 4.0.1 - Mar 15 2021
### Updated
- The FPS change during video upload has more stable frame choosing algorithm now.
###
## 4.0.0 - Feb 28 2021
### Updated
- Improved image storage structure on platform, which requires this upgrade in SDK. This change in platform is backward incompatible with previous versions of SDK.
###
Changelog not maintained before version 4.0.0.
