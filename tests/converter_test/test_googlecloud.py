from pathlib import Path
import superannotate as sa


def googlecloud_convert_web(tmpdir):
    out_dir = tmpdir / "output_web"
    sa.import_annotation_format(
        "tests/converter_test/GoogleCloud/input/toSuperAnnotate", str(out_dir),
        "GoogleCloud", "image_object_detection", "Vector", "object_detection",
        "Web"
    )

    project_name = "googlcloud_vector"

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


def googlecloud_convert_desktop(tmpdir):
    out_dir = tmpdir / "output_desktop"
    sa.import_annotation_format(
        "tests/converter_test/GoogleCloud/input/toSuperAnnotate", str(out_dir),
        "GoogleCloud", "image_object_detection", "Vector", "object_detection",
        "Desktop"
    )

    # project_name = "googlcloud_vector"

    # projects = sa.search_projects(project_name, True)
    # if projects:
    #     sa.delete_project(projects[0])
    # project = sa.create_project(project_name, "converter vector", "Vector")

    # sa.create_annotation_classes_from_classes_json(
    #     project, out_dir + "/classes/classes.json"
    # )
    # sa.upload_images_from_folder_to_project(project, out_dir)
    # sa.upload_annotations_from_folder_to_project(project, out_dir)

    return 0


def test_googlecloud(tmpdir):
    assert googlecloud_convert_web(tmpdir) == 0
    assert googlecloud_convert_desktop(tmpdir) == 0
