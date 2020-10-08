from pathlib import Path

import numpy as np
import pytest

import superannotate as sa

PROJECT_NAME_1 = "test filter instances"

PROJECT_DIR = "./tests/sample_project_vector"


def test_filter_instances(tmpdir):
    tmpdir = Path(tmpdir)

    # projects = sa.search_projects(PROJECT_NAME_1, return_metadata=True)
    # for project in projects:
    #     sa.delete_project(project)

    # project = sa.create_project(PROJECT_NAME_1, "test", "Vector")

    not_filtered = sa.filter_annotation_instances(PROJECT_DIR)

    filtered_excl = sa.filter_annotation_instances(
        PROJECT_DIR,
        exclude=[{
            "className": "Personal vehicle"
        }, {
            "className": "Human"
        }]
    )

    filtered_incl = sa.filter_annotation_instances(
        PROJECT_DIR, include=[{
            "className": "Large vehicle"
        }]
    )

    assert filtered_incl.equals(filtered_excl)

    all_filtered = sa.filter_annotation_instances(
        PROJECT_DIR, include=[{
            "className": "bogus"
        }]
    )

    assert len(all_filtered) == 0

    vc = not_filtered["type"].value_counts()
    for i in vc.index:
        all_filtered = sa.filter_annotation_instances(
            PROJECT_DIR, include=[{
                "type": i
            }]
        )

        assert len(all_filtered) == vc[i]

    vcc = not_filtered["class"].value_counts()
    for i in vcc.index:
        if len(not_filtered[not_filtered["class"] == i]["type"].unique()) > 1:
            break

    vcc_different_types = not_filtered[not_filtered["class"] == i
                                      ]["type"].value_counts()

    t_c = sa.filter_annotation_instances(
        PROJECT_DIR,
        include=[{
            "className": i,
            "type": vcc_different_types.index[0]
        }]
    )
    assert len(t_c) == len(
        not_filtered[(not_filtered["type"] == vcc_different_types.index[0]) &
                     (not_filtered["class"] == i)]
    )
    # print(not_filtered[not_filtered["className"] == "Human
