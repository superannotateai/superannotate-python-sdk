<img src="./docs/source/sa_logo.png" width="200">

# SuperAnnotate Python SDK

SuperAnnotate Python SDK allows access to the platform without
 web browser:

```python
import superannotate as sa

sa.create_project("Example Project 1", "example", "Vector")

sa.upload_images_from_folder_to_project("Example Project 1", "<path_to_my_images_folder>")
```

## Installation

SDK is available on PyPI:
 
```console
pip install superannotate
```

The package officially supports Python 3.6+ and was tested under Linux and
Windows ([Anaconda](https://www.anaconda.com/products/individual#windows)) platforms.

For more detailed installation steps and package usage please have a look at the 
[tutorial](https://superannotate.readthedocs.io/en/stable/tutorial.sdk.html).

## Supported Features

- Search projects
- Create/delete a project
- Upload images to a project from a local or AWS S3 folder
- Upload videos to a project from a local folder
- Upload annotations/pre-annotations to a project from local or AWS S3 folder
- Set the annotation status of the images being uploaded
- Export annotations from a project to a local or AWS S3 folder
- Share and unshare a project with a team contributor
- Invite a team contributor
- Search images in a project
- Download a single image
- Copy/move image between projects
- Get image bytes (e.g., for numpy array creation)
- Set image annotation status
- Download image annotations/pre-annotations
- Create/download project annotation classes
- Convert annotation format from/to COCO
- Convert annotation format from VOC, SuperVisely, LabelBox, DataLoop, VGG, VoTT, SageMaker, GoogleCloud, YOLO
- Add annotations to images on platform
- Add annotations to local SuperAnnotate format JSONs
- CLI commands for simple tasks

## Full SDK reference, tutorial available on [Read the Docs](https://superannotate.readthedocs.io)

## License

This SDK is distributed under the MIT License, see [LICENSE](./LICENSE).

## Questions and Issues

For questions and issues please use this repo's issue tracker on GitHub.
