from pathlib import Path

import superannotate as sa

PROJECT_NAME_1 = "test filter instances"

PROJECT_DIR = "./tests/sample_project_vector"


def test_filter_instances(tmpdir):
    tmpdir = Path(tmpdir)

    # projects = sa.search_projects(PROJECT_NAME_1, return_metadata=True)
    # for project in projects:
    #     sa.delete_project(project)

    # project = sa.create_project(PROJECT_NAME_1, "test", "Vector")

    not_filtered = sa.aggregate_annotations_as_df(PROJECT_DIR)

    filtered_excl = sa.filter_annotation_instances(
        not_filtered,
        exclude=[{
            "className": "Personal vehicle"
        }, {
            "className": "Human"
        }]
    )

    filtered_incl = sa.filter_annotation_instances(
        not_filtered,
        include=[{
            "className": "Large vehicle"
        }, {
            "className": "Plant"
        }]
    )

    assert filtered_incl.equals(filtered_excl)

    all_filtered = sa.filter_annotation_instances(
        not_filtered, include=[{
            "className": "bogus"
        }]
    )

    assert len(all_filtered) == 0

    vc = not_filtered["type"].value_counts()
    for i in vc.index:
        all_filtered = sa.filter_annotation_instances(
            not_filtered, include=[{
                "type": i
            }]
        )

        assert len(all_filtered) == vc[i]

    vcc = not_filtered["className"].value_counts()
    for i in vcc.index:
        if len(
            not_filtered[not_filtered["className"] == i]["type"].unique()
        ) > 1:
            break

    vcc_different_types = not_filtered[not_filtered["className"] == i
                                      ]["type"].value_counts()

    t_c = sa.filter_annotation_instances(
        not_filtered,
        include=[{
            "className": i,
            "type": vcc_different_types.index[0]
        }]
    )
    assert len(t_c) == len(
        not_filtered[(not_filtered["type"] == vcc_different_types.index[0]) &
                     (not_filtered["className"] == i)]
    )
    # print(not_filtered[not_filtered["className"] == "Human


def test_df_to_annotations(tmpdir):
    tmpdir = Path(tmpdir)

    df = sa.aggregate_annotations_as_df(PROJECT_DIR)
    sa.df_to_annotations(df, tmpdir)
    df_new = sa.aggregate_annotations_as_df(tmpdir)
    # print(df_new["image_name"].value_counts())
    # print(df["image_name"].value_counts())
    for _index, row in enumerate(df.iterrows()):
        found = False
        for _, row_2 in enumerate(df_new.iterrows()):
            if row_2[1].equals(row[1]):
                found = True
                break
        assert found
    for project in sa.search_projects("test df to annotations 2"):
        sa.delete_project(project)
    project = sa.create_project("test df to annotations 2", "test", "Vector")
    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )
    sa.create_annotation_classes_from_classes_json(
        project, "./tests/sample_project_vector/classes/classes.json"
    )
    sa.upload_annotations_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )


def test_df_to_annotations_full(tmpdir):
    tmpdir = Path(tmpdir)

    df = sa.aggregate_annotations_as_df(
        PROJECT_DIR, include_classes_wo_annotations=True
    )
    sa.df_to_annotations(df, tmpdir)
    df_new = sa.aggregate_annotations_as_df(
        tmpdir, include_classes_wo_annotations=True
    )
    # print(df_new["image_name"].value_counts())
    # print(df["image_name"].value_counts())
    for _index, row in enumerate(df.iterrows()):
        for _, row_2 in enumerate(df_new.iterrows()):
            if row_2[1].equals(row[1]):
                break
        else:
            assert False

    fil1 = sa.filter_annotation_instances(
        df_new,
        include=[
            {
                "className": "Personal vehicle",
                "attributes": [{
                    "name": "4",
                    "groupName": "Num doors"
                }]
            }
        ],
        exclude=[{
            "type": "polygon"
        }]
    )
    filtered_export = (tmpdir / "filtered")
    filtered_export.mkdir()
    sa.df_to_annotations(fil1, filtered_export)
    for project in sa.search_projects("test df to annotations 3"):
        sa.delete_project(project)
    project = sa.create_project("test df to annotations 3", "test", "Vector")
    sa.upload_images_from_folder_to_project(project, PROJECT_DIR)
    sa.create_annotation_classes_from_classes_json(
        project, filtered_export / "classes" / "classes.json"
    )
    sa.upload_annotations_from_folder_to_project(project, filtered_export)
