import superannotate as sa
from pathlib import Path
import json


def test_json_version_conversion(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'sa_json_versions' / 'version2'
    temp_dir = Path(tmpdir) / 'tmp_dir'
    output_dir = Path(tmpdir) / 'output_dir'

    converted_files_old = sa.convert_json_version(input_dir, temp_dir, 1)
    converted_files_new = sa.convert_json_version(temp_dir, output_dir, 2)

    assert len(converted_files_old) == len(converted_files_new)
    files_list = input_dir.glob('*.json')

    metadata_keys = ['height', 'width', 'status', 'pinned']
    comments_keys = ['x', 'y', 'resolved']
    for file in files_list:
        input_data = json.load(open(file))
        output_data = json.load(open(output_dir / file.name))
        for key in metadata_keys:
            assert input_data['metadata'][key] == output_data['metadata'][key]

        assert len(input_data['instances']) == len(output_data['instances'])

        assert len(input_data['comments']) == len(output_data['comments'])
        for in_com, out_com in zip(
            input_data['comments'], output_data['comments']
        ):
            assert len(in_com['correspondence']) == len(
                out_com['correspondence']
            )
            for key in comments_keys:
                assert in_com[key] == out_com[key]

        assert len(input_data['tags']) == len(output_data['tags'])
        for in_tag, out_tag in zip(input_data['tags'], output_data['tags']):
            assert in_tag == out_tag
