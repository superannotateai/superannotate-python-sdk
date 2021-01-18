import superannotate as sa
from pathlib import Path
import json


def compare_jsons(json_gen, input_dir):
    for path in json_gen:
        final_json = json.load(open(str(path)))
        input_path = input_dir.joinpath(path.name)
        init_json = json.load(open(str(input_path)))

        for init, final in zip(init_json['instances'], final_json['instances']):
            for key in init.keys():
                if key == 'parts':
                    continue
                init_value = init[key]
                final_value = final[key]
                assert init_value == final_value


def test_pixel_vector_pixel(tmpdir):
    input_dir = Path()
    input_dir = input_dir.joinpath(
        'tests', 'converter_test', 'COCO', 'input', 'fromSuperAnnotate',
        'cats_dogs_pixel_instance_segm'
    )
    temp_dir = Path(tmpdir) / 'output'
    final_dir = Path(tmpdir) / 'output2'

    sa.convert_project_type(input_dir, temp_dir)
    sa.convert_project_type(temp_dir, final_dir)

    gen = final_dir.glob('*.json')
    compare_jsons(gen, input_dir)


def test_vector_pixel_vector(tmpdir):
    input_dir = Path(
        'tests'
    ) / 'converter_test' / 'COCO' / 'input' / 'fromSuperAnnotate' / 'cats_dogs_vector_instance_segm'
    temp_dir = Path(tmpdir) / 'output'
    final_dir = Path(tmpdir) / 'output2'

    sa.convert_project_type(input_dir, temp_dir)
    sa.convert_project_type(temp_dir, final_dir)

    gen = input_dir.glob('*.json')
    compare_jsons(gen, input_dir)