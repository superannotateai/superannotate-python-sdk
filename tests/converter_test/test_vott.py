from pathlib import Path
import superannotate as sa


def vott_convert_object(tmpdir):
    out_dir = tmpdir / "object_detection"
    sa.import_annotation_format(
        "tests/converter_test/VoTT/input/toSuperAnnotate", str(out_dir), "VoTT",
        "", "Vector", "object_detection", "Web"
    )

    project_name = "vott_vector"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)

    return 0


def vott_convert_instance(tmpdir):
    out_dir = tmpdir / "instance_segmentation"
    sa.import_annotation_format(
        "tests/converter_test/VoTT/input/toSuperAnnotate", str(out_dir), "VoTT",
        "", "Vector", "instance_segmentation", "Desktop"
    )

    return 0


def vott_convert_vector(tmpdir):
    out_dir = tmpdir / "vector_annotation"
    sa.import_annotation_format(
        "tests/converter_test/VoTT/input/toSuperAnnotate", str(out_dir), "VoTT",
        "", "Vector", "vector_annotation", "Web"
    )

    project_name = "vott_vector"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)

    return 0


def test_vott(tmpdir):
    assert vott_convert_vector(tmpdir) == 0
    assert vott_convert_instance(tmpdir) == 0
    assert vott_convert_object(tmpdir) == 0
