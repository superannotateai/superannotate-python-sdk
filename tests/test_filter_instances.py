from pathlib import Path

import superannotate as sa

PROJECT_NAME_1 = "test filter instances"

PROJECT_DIR = "./tests/sample_project_vector"


def test_filter_comments(tmpdir):
    tmpdir = Path(tmpdir)

    # projects = sa.search_projects(PROJECT_NAME_1, return_metadata=True)
    # for project in projects:
    #     sa.delete_project(project)

    # project = sa.create_project(PROJECT_NAME_1, "test", "Vector")

    not_filtered = sa.aggregate_annotations_as_df(
        PROJECT_DIR, include_comments=True
    )

    filtered_excl = sa.filter_images_by_comments(
        not_filtered, False, False, False
    )

    assert sorted(filtered_excl) == []

    filtered_excl = sa.filter_images_by_comments(
        not_filtered, include_unresolved_comments=True
    )

    assert sorted(filtered_excl) == [
        "example_image_1.jpg", "example_image_2.jpg"
    ]

    filtered_excl = sa.filter_images_by_comments(not_filtered, False)

    assert filtered_excl == []

    filtered_excl = sa.filter_images_by_comments(
        not_filtered,
        include_unresolved_comments=False,
        include_resolved_comments=True
    )

    assert filtered_excl == ["example_image_1.jpg"]

    filtered_excl = sa.filter_images_by_comments(
        not_filtered,
        include_unresolved_comments=False,
        include_resolved_comments=True,
        include_without_comments=True
    )

    assert sorted(filtered_excl) == [
        "example_image_1.jpg", "example_image_3.jpg", "example_image_4.jpg"
    ]

    filtered_excl = sa.filter_images_by_comments(
        not_filtered,
        include_unresolved_comments=False,
        include_resolved_comments=False,
        include_without_comments=True
    )

    assert sorted(filtered_excl) == [
        "example_image_3.jpg", "example_image_4.jpg"
    ]


def test_filter_tags(tmpdir):

    not_filtered = sa.aggregate_annotations_as_df(
        PROJECT_DIR, include_tags=True
    )

    filtered_excl = sa.filter_images_by_tags(not_filtered)

    assert sorted(filtered_excl) == [
        "example_image_2.jpg", "example_image_3.jpg", "example_image_4.jpg"
    ]

    filtered_excl = sa.filter_images_by_tags(not_filtered, include=["tag1"])

    assert sorted(filtered_excl) == [
        "example_image_2.jpg", "example_image_4.jpg"
    ]

    filtered_excl = sa.filter_images_by_tags(not_filtered, exclude=["tag2"])

    assert sorted(filtered_excl) == ["example_image_4.jpg"]

    filtered_excl = sa.filter_images_by_tags(
        not_filtered, include=["tag1", "tag2"], exclude=["tag3"]
    )

    assert sorted(filtered_excl) == [
        "example_image_2.jpg", "example_image_4.jpg"
    ]


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

    assert len(df) == len(df_new)
    # print(df_new["imageName"].value_counts())
    # print(df["imageName"].value_counts())
    # print(len(df.columns))
    # print(len(df_new.columns))

    # print(df[df["imageName"] == "example_image_1.jpg"]["instanceId"])
    # print(df_new[(df_new["imageName"] == "example_image_1.jpg")]["instanceId"])
    for _index, row in enumerate(df.iterrows()):
        for _, row_2 in enumerate(df_new.iterrows()):
            if row_2[1].equals(row[1]):
                break
            # if row_2[1]["imageName"] == "example_image_1.jpg":
            #     print(row_2[1])
        else:
            assert False, print("Error on ", row[1])

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
        PROJECT_DIR, include_classes_wo_annotations=True, include_comments=True
    )
    sa.df_to_annotations(df, tmpdir)
    df_new = sa.aggregate_annotations_as_df(
        tmpdir, include_classes_wo_annotations=True, include_comments=True
    )
    for project in sa.search_projects("test df to annotations 4"):
        sa.delete_project(project)
    project = sa.create_project("test df to annotations 4", "test", "Vector")
    sa.upload_images_from_folder_to_project(project, PROJECT_DIR)
    sa.create_annotation_classes_from_classes_json(
        project, tmpdir / "classes" / "classes.json"
    )
    sa.upload_annotations_from_folder_to_project(project, tmpdir)
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
