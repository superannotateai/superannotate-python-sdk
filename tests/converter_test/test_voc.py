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


def test_voc_vector_instance(tmpdir):
    project_name = "voc2sa_vector_instance"

    input_dir = Path(
        "tests"
    ) / "converter_test" / "VOC" / "input" / "fromPascalVOCToSuperAnnotate" / "VOC2012"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "VOC", "", "Vector", "instance_segmentation"
    )

    description = 'voc vector instance segmentation'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_voc_vector_object(tmpdir):
    project_name = "voc2sa_vector_object"

    input_dir = Path(
        "tests"
    ) / "converter_test" / "VOC" / "input" / "fromPascalVOCToSuperAnnotate" / "VOC2012"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "VOC", "", "Vector", "object_detection"
    )

    description = 'voc vector object detection'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_voc_pixel(tmpdir):
    project_name = "voc2sa_pixel_instance"
    input_dir = Path(
        "tests"
    ) / "converter_test" / "VOC" / "input" / "fromPascalVOCToSuperAnnotate" / "VOC2012"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "VOC", "", "Pixel", "instance_segmentation"
    )

    description = 'voc pixel instance segmentation'
    ptype = 'Pixel'
    upload_project(out_dir, project_name, description, ptype)
