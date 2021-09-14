import time
from pathlib import Path

import pytest

import superannotate as sa
from superannotate.exceptions import SABaseException
import subprocess

PROJECT_NAME_TEXT = "test attach text urls"
PATH_TO_URLS = Path("./tests/attach_urls.csv")
PROJECT_TYPE = "Document"



def test_attach_text_cli():
    project_name_cli = "cli text"
    projects = sa.search_projects(project_name_cli, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    time.sleep(1)
    project = sa.create_project(project_name_cli, "test", PROJECT_TYPE)
    time.sleep(1)
    subprocess.run(
        f'superannotatecli attach-document-urls --project "{project_name_cli}" --attachments {PATH_TO_URLS}',
        check=True,
        shell=True
    )
    time.sleep(1)





def test_attach_text_urls():
    projects = sa.search_projects(PROJECT_NAME_TEXT, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    time.sleep(1)
    project = sa.create_project(PROJECT_NAME_TEXT, "test", PROJECT_TYPE)
    time.sleep(1)

    uploaded, could_not_upload, existing_images = sa.attach_document_urls_to_project(
        project, PATH_TO_URLS
    )

    assert len(uploaded) == 7
    assert len(could_not_upload) == 0
    assert len(existing_images) == 1

    with pytest.raises(SABaseException) as e:
        sa.export_annotation("./tests/attached_export_dir_sample","some/","object_test","COCO","Video")
        assert str(
            e
        ) == f"The function does not support projects containing {PROJECT_TYPE} attached with URLs"



    with pytest.raises(SABaseException) as e:
        sa.import_annotation("./tests/attached_export_dir_sample", "some/", "object_test", "COCO", "Video")
        assert str(
            e
        ) == f"The function does not support projects containing {PROJECT_TYPE} attached with URLs"


    with pytest.raises(SABaseException) as e:
        sa.aggregate_annotations_as_df("./tests/attached_export_dir_sample")
        assert str(
            e
        ) == f"The function does not support projects containing {PROJECT_TYPE} attached with URLs"
        sa.download_image_annotations(PROJECT_NAME_TEXT,"some","some")
        assert str(
            e
        ) == f"The function does not support projects containing {PROJECT_TYPE} attached with URLs"
