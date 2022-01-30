# Changelog 
All release higlighths of this project will be documented in this file.
## 4.2.9 - Dec 12 2022
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
