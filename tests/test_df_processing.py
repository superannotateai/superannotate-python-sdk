from pathlib import Path

import pytest

import superannotate as sa

PROJECT_NAME_1 = "test df processing"

PROJECT_DIR = "./tests/sample_project_vector"


def test_filter_instances(tmpdir):
    tmpdir = Path(tmpdir)

    # projects = sa.search_projects(PROJECT_NAME_1, return_metadata=True)
    # for project in projects:
    #     sa.delete_project(project)

    # project = sa.create_project(PROJECT_NAME_1, "test", "Vector")

    df = sa.aggregate_annotations_as_df(PROJECT_DIR)
    df = df[~(df.duplicated(["instanceId", "imageName"]))]
    df = df[df.duplicated(["trackingId"], False) & df["trackingId"].notnull()]
    assert len(df) == 2
    assert set([df.iloc[0]["imageName"], df.iloc[1]["imageName"]]) == set(
        ["example_image_1.jpg", "example_image_2.jpg"]
    )
