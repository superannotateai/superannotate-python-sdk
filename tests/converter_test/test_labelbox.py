from pathlib import Path

import superannotate as sa
import os


def test_labelbox_convert_vector(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'LabelBox' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / "output_vector"
    dataset_name = 'labelbox_example'
    sa.import_annotation_format(
        input_dir, out_dir, 'LabelBox', dataset_name, 'Vector',
        'vector_annotation', 'Web'
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

    assert json_files == image_files


def test_labelbox_convert_object(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'LabelBox' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / "output_object"
    dataset_name = 'labelbox_example'
    sa.import_annotation_format(
        input_dir, out_dir, 'LabelBox', dataset_name, 'Vector',
        'object_detection', 'Web'
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

    assert json_files == image_files


def test_labelbox_convert_instance(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'LabelBox' / 'input' / 'toSuperAnnotate'
    out_dir = Path(tmpdir) / "output_insance"
    dataset_name = 'labelbox_example'
    sa.import_annotation_format(
        input_dir, out_dir, 'LabelBox', dataset_name, 'Vector',
        'instance_segmentation', 'Desktop'
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

    assert json_files == image_files
