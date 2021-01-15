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


def test_vott_convert_object(tmpdir):
    project_name = "vott_object"
    input_dir = Path(
        "tests"
    ) / "converter_test" / "VoTT" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "VoTT", "", "Vector", "object_detection"
    )

    description = 'vott object detection'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_vott_convert_instance(tmpdir):
    project_name = "vott_vector_instance"
    input_dir = Path(
        "tests"
    ) / "converter_test" / "VoTT" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "VoTT", "", "Vector", "instance_segmentation"
    )

    description = 'vott instance segmentation'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_vott_convert_vector(tmpdir):
    project_name = "vott_vector"

    input_dir = Path(
        "tests"
    ) / "converter_test" / "VoTT" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "VoTT", "", "Vector", "vector_annotation"
    )

    description = 'vott vector annotation'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)
