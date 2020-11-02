import superannotate as sa
import os


def labelbox_convert(tmpdir):
    out_dir = tmpdir / "output"
    dataset_name = 'labelbox_example'
    sa.import_annotation_format(
        'tests/converter_test/LabelBox/input/toSuperAnnotate', str(out_dir),
        'LabelBox', dataset_name, 'Vector', 'vector_annotation', 'Web'
    )

    all_files = os.listdir(out_dir)
    json_files = set(
        [
            file.replace('___objects.json', '')
            for file in all_files if os.path.splitext(file) == '.json'
        ]
    )
    image_files = set(
        [file for file in all_files if os.path.splitext(file) == '.jpg']
    )

    if json_files != image_files:
        return 1
    return 0


def test_labelbox(tmpdir):
    assert labelbox_convert(tmpdir) == 0
