import json
from pathlib import Path
import superannotate as sa


def compare_jsons(input_dir, output_dir):
    input_paths = input_dir.glob('*.json')
    for input_path in input_paths:
        init_json = json.load(open(input_path))

        output_path = output_dir / input_path.name
        final_json = json.load(open(output_path))

        for init, final in zip(init_json['instances'], final_json['instances']):
            for key in init.keys():
                init_value = init[key]
                final_value = final[key]
                assert init_value == final_value


def test_platfrom_converter(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "fromSuperAnnotate" / "cats_dogs_vector_instance_segm"
    tmp_dir = Path(tmpdir) / 'desktop_format'
    output_dir = Path(tmpdir) / 'output_dir'

    sa.convert_platform(input_dir, tmp_dir, "Desktop")
    sa.convert_platform(tmp_dir, output_dir, 'Web')
