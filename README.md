<img src="./docs/source/sa_logo.png" width="200">

# SuperAnnotate Python SDK

**SuperAnnotate Python SDK allows access to the platform without
 web browser**

```python
import superannotate as sa

sa.init(<path_to_my_config_json>)

projects = sa.search_projects("Example Project 1")

example_project = projects[0]
sa.upload_images_from_folder(example_project, <path_to_my_images_folder>)
```

## Installation

SDK is available on PyPI:
 
```console
pip install superannotate
```

for COCO format converters support need to install:

```console
pip install 'git+https://github.com/cocodataset/panopticapi.git'
pip install 'git+https://github.com/philferriere/cocoapi.git#egg=pycocotools&subdirectory=PythonAPI'
```


The package officially supports Python 3.5+.

## Supported Features

- Search projects
- Create/delete a project
- Upload images to a project from local or AWS S3 folder
- Upload annotations/pre-annotations to a project from local or AWS S3 folder
- Set the annotation status of the images being uploaded
- Export annotations from a project to a local or AWS S3 folder
- Share and unshare a project with a team contributor
- Search images in a project
- Download a single image
- Get image bytes (e.g., for numpy array creation)
- Set image annotation status
- Download image annotations/pre-annotations
- Create/download project annotation classes

## API Reference, User Guide available on [Read the Docs](https://superannotate.readthedocs.io)

## License

This SDK is distributed under the MIT License, see [LICENSE](./LICENSE)

## Questions and Issues

For questions and issues please use this repo's Issue tracker on Github.
