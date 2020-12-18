import json
from pathlib import Path
import superannotate as sa


def test_conversion(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "fromSuperAnnotate" / "cats_dogs_vector_instance_segm"
    temp_dir = Path(tmpdir) / 'output_Desktop'
    final_dir = Path(tmpdir) / 'output_Web'

    sa.convert_platform(input_dir, temp_dir, "Web")
    sa.convert_platform(temp_dir, final_dir, "Desktop")

    init_gen = input_dir.glob('*.json')
    init_jsons = [file.name for file in init_gen]

    final_gen = final_dir.glob('*.json')
    final_jsons = [file.name for file in final_gen]

    assert set(init_jsons) == set(final_jsons)

    init_file_names = set(
        [file.replace('___objects.json', '') for file in init_jsons]
    )
    temp_file_names = set(json.load(open(temp_dir / 'annotations.json')).keys())
    final_file_names = set(
        [file.replace('___objects.json', '') for file in final_jsons]
    )

    assert init_file_names == temp_file_names
    assert init_file_names == final_file_names

    project_name = "platform_conversion"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, final_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, input_dir)
    sa.upload_annotations_from_folder_to_project(project, final_dir)
