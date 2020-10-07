from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import superannotate as sa

PROJECT_NAME_1 = "test filter instances"


def test_filter_instances(tmpdir):
    tmpdir = Path(tmpdir)

    # projects = sa.search_projects(PROJECT_NAME_1, return_metadata=True)
    # for project in projects:
    #     sa.delete_project(project)

    # project = sa.create_project(PROJECT_NAME_1, "test", "Vector")

    sa.filter_annotation_instances("./tests/sample_project_vector")


