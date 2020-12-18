from pathlib import Path
import superannotate as sa


def test_vgg_convert_object(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "VGG" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / "object_detection"
    sa.import_annotation(
        input_dir, out_dir, "VGG", "vgg_test", "Vector", "object_detection",
        "Web"
    )

    project_name = "vgg_test_object"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_vgg_convert_instance(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "VGG" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / "instance_segmentation"
    sa.import_annotation(
        input_dir, out_dir, "VGG", "vgg_test", "Vector",
        "instance_segmentation", "Desktop"
    )


def test_vgg_convert_vector(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "VGG" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / "vector_annotation"
    sa.import_annotation(
        input_dir, out_dir, "VGG", "vgg_test", "Vector", "vector_annotation",
        "Web"
    )

    project_name = "vgg_test_vector"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)
