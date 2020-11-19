import os
import json
import superannotate as sa


def test_conversion(tmpdir):
    input_dir = "tests/converter_test/COCO/input/fromSuperAnnotate/cats_dogs_vector_instance_segm"
    temp_dir = tmpdir / 'output_Desktop'
    final_dir = tmpdir / 'output_Web'

    sa.convert_platform(str(input_dir), str(temp_dir), "Web")
    sa.convert_platform(str(temp_dir), str(final_dir), "Desktop")

    init_jsons = [file for file in os.listdir(input_dir) if '.json' in file]
    final_jsons = [file for file in os.listdir(final_dir) if '.json' in file]
    assert set(init_jsons) == set(final_jsons)

    init_file_names = set(
        [file.replace('___objects.json', '') for file in init_jsons]
    )
    temp_file_names = set(
        json.load(open(os.path.join(temp_dir, 'annotations.json'))).keys()
    )
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
