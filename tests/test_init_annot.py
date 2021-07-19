import time
from pathlib import Path

import cv2

import superannotate as sa

name = "Example Project test meta init"
project_type = "Vector"
description = "test vector"
from_folder = Path("./tests/sample_project_vector_for_checks")


def test_meta_init(tmpdir):
    projects = sa.search_projects(name, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    time.sleep(2)

    project = sa.create_project(name, description, project_type)
    time.sleep(2)
    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status="InProgress"
    )

    for image in from_folder.glob("*.jpg"):
        size = cv2.imread(str(image)).shape
        annot = sa.get_image_annotations(project, image.name)["annotation_json"]
        print(annot)
        assert annot["metadata"]["width"] == size[1]
        assert annot["metadata"]["height"] == size[0]
        assert annot["metadata"]["name"] == image.name
        assert len(annot["metadata"]) == 3

    sa.download_export(project, sa.prepare_export(project), tmpdir)
