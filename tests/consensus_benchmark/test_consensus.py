from pathlib import Path

import superannotate as sa

test_root = Path().resolve() / 'tests'
project_name = "consensus_enhanced"


def test_consensus():
    annot_types = ['polygon', 'bbox', 'point']
    folder_names = ['consensus_1', 'consensus_2', 'consensus_3']
    df_column_names = [
        'creatorEmail', 'imageName', 'instanceId', 'area', 'className',
        'attributes', 'folderName', 'score'
    ]
    export_path = test_root / 'consensus_benchmark' / 'consensus_test_data'
    if len(sa.search_projects(project_name)) != 0:
        sa.delete_project(project_name)

    sa.create_project(project_name, "test bench", "Vector")
    for i in range(1, 4):
        sa.create_folder(project_name, "consensus_" + str(i))
    sa.create_annotation_classes_from_classes_json(
        project_name, export_path / 'classes' / 'classes.json'
    )
    sa.upload_images_from_folder_to_project(
        project_name, export_path / "images", annotation_status="Completed"
    )
    for i in range(1, 4):
        sa.upload_images_from_folder_to_project(
            project_name + '/consensus_' + str(i),
            export_path / "images",
            annotation_status="Completed"
        )
    sa.upload_annotations_from_folder_to_project(project_name, export_path)
    for i in range(1, 4):
        sa.upload_annotations_from_folder_to_project(
            project_name + '/consensus_' + str(i),
            export_path / ('consensus_' + str(i))
        )

    for annot_type in annot_types:
        res_df = sa.consensus(project_name, folder_names, annot_type=annot_type)
        #test content of projectName column
        assert sorted(res_df['folderName'].unique()) == folder_names

        #test structure of resulting DataFrame
        assert sorted(res_df.columns) == sorted(df_column_names)

        #test lower bound of the score
        assert (res_df['score'] >= 0).all()

        #test upper bound of the score
        assert (res_df['score'] <= 1).all()

    image_names = [
        'bonn_000000_000019_leftImg8bit.png',
        'bielefeld_000000_000321_leftImg8bit.png'
    ]

    #test filtering images with given image names list
    res_images = sa.consensus(
        project_name,
        folder_names,
        export_root=export_path,
        image_list=image_names
    )

    assert sorted(res_images['imageName'].unique()) == sorted(image_names)
