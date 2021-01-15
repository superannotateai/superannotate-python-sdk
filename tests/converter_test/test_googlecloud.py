from pathlib import Path
import superannotate as sa


def upload_project(project_path, project_name, description, ptype):
    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, description, ptype)

    sa.create_annotation_classes_from_classes_json(
        project, project_path / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, project_path)
    sa.upload_annotations_from_folder_to_project(project, project_path)


def test_googlecloud_convert_web(tmpdir):
    project_name = "googlcloud_object"

    input_dir = Path(
        "tests"
    ) / "converter_test" / "GoogleCloud" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "GoogleCloud", "image_object_detection", "Vector",
        "object_detection"
    )

    description = 'googlecloud object detection'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)
