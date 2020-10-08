from pathlib import Path

import numpy as np
import pytest

import superannotate as sa

PROJECT_NAME_1 = "test filter instances"


def test_filter_instances(tmpdir):
    tmpdir = Path(tmpdir)

    # projects = sa.search_projects(PROJECT_NAME_1, return_metadata=True)
    # for project in projects:
    #     sa.delete_project(project)

    # project = sa.create_project(PROJECT_NAME_1, "test", "Vector")

    not_filtered = sa.filter_annotation_instances(
        "./tests/sample_project_vector"
    )

    filtered_excl = sa.filter_annotation_instances(
        "./tests/sample_project_vector",
        exclude=[{
            "className": "Personal vehicle"
        }, {
            "className": "Human"
        }]
    )

    filtered_incl = sa.filter_annotation_instances(
        "./tests/sample_project_vector",
        include=[{
            "className": "Large vehicle"
        }]
    )

    assert filtered_incl.equals(filtered_excl)

    all_filtered = sa.filter_annotation_instances(
        "./tests/sample_project_vector", include=[{
            "className": "bogus"
        }]
    )

    assert len(all_filtered) == 0

    vc = not_filtered["type"].value_counts()
    for i in vc.index:
        all_filtered = sa.filter_annotation_instances(
            "./tests/sample_project_vector", include=[{
                "type": i
            }]
        )

        assert len(all_filtered) == vc[i]
