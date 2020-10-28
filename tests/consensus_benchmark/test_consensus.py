from pathlib import Path
import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

test_root = Path().resolve() / 'tests'


def test_consensus():
    annot_types = ['polygon', 'bbox', 'point']
    project_names = ['consensus_1', 'consensus_2', 'consensus_3']
    df_column_names = [
        'creatorEmail', 'imageName', 'instanceId', 'area', 'className',
        'attributes', 'projectName', 'score'
    ]
    export_path = test_root / 'consensus_benchmark'
    for annot_type in annot_types:
        res_df = sa.consensus(
            project_names, export_root=export_path, annot_type=annot_type
        )
        #test content of projectName column
        assert sorted(res_df['projectName'].unique()) == project_names

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
        project_names, export_root=export_path, image_list=image_names
    )

    assert sorted(res_images['imageName'].unique()) == sorted(image_names)
