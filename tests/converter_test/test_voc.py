from pathlib import Path
import superannotate as sa


def test_voc_vector_instance(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "VOC" / "input" / "fromPascalVOCToSuperAnnotate" / "VOC2012"
    out_dir = Path(tmpdir) / "instance_vector"
    sa.import_annotation(
        input_dir, out_dir, "VOC", "", "Vector", "instance_segmentation", "Web"
    )

    project_name = "voc2sa_vector_instance"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_voc_vector_object(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "VOC" / "input" / "fromPascalVOCToSuperAnnotate" / "VOC2012"
    out_dir = Path(tmpdir) / "object_vector"
    sa.import_annotation(
        input_dir, out_dir, "VOC", "", "Vector", "object_detection", "Desktop"
    )


def test_voc_pixel(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "VOC" / "input" / "fromPascalVOCToSuperAnnotate" / "VOC2012"
    out_dir = Path(tmpdir) / "instance_pixel"
    sa.import_annotation(
        input_dir, out_dir, "VOC", "", "Pixel", "instance_segmentation", "Web"
    )

    project_name = "voc2sa_pixel"

    projects = sa.search_projects(project_name, True)

    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Pixel")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)
