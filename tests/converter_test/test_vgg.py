from pathlib import Path
import superannotate as sa


def googlecloud_convert(tmpdir):
    out_dir = tmpdir / "output"
    sa.import_annotation_format(
        "tests/converter_test/VGG/input/toSuperAnnotate", str(out_dir), "VGG",
        "vgg_test", "Vector", "object_detection", "Web"
    )

    project_name = "vgg_test"

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


def test_googlecloud(tmpdir):
    assert googlecloud_convert(tmpdir) == 0