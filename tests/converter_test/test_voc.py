from pathlib import Path
import superannotate as sa


def voc_vector_instance(tmpdir):
    out_dir = tmpdir / "instance_vector"
    sa.import_annotation_format(
        "tests/converter_test/VOC/input/fromPascalVOCToSuperAnnotate/VOC2012/",
        out_dir, "VOC", "", "Vector", "instance_segmentation", "Web"
    )

    project_name = "voc2sa_vector_instance"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir + "/classes/classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)

    return 0


def voc_vector_object(tmpdir):
    out_dir = tmpdir / "object_vector"
    sa.import_annotation_format(
        "tests/converter_test/VOC/input/fromPascalVOCToSuperAnnotate/VOC2012/",
        out_dir, "VOC", "", "Vector", "object_detection", "Web"
    )

    project_name = "voc2sa_vector_object"

    projects = sa.search_projects(project_name, True)

    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir + "/classes/classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)

    return 0


def voc_pixel(tmpdir):
    out_dir = tmpdir / "instance_pixel"
    sa.import_annotation_format(
        "tests/converter_test/VOC/input/fromPascalVOCToSuperAnnotate/VOC2012/",
        out_dir, "VOC", "", "Pixel", "instance_segmentation", "Web"
    )

    project_name = "voc2sa_pixel"

    projects = sa.search_projects(project_name, True)

    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Pixel")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir + "/classes/classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)

    return 0


def test_voc(tmpdir):

    sa.init(Path.home() / ".superannotate" / "config.json")

    assert voc_vector_object(tmpdir) == 0
    assert voc_pixel(tmpdir) == 0
    assert voc_vector_instance(tmpdir) == 0
