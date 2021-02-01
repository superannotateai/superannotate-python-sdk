from pathlib import Path
import superannotate as sa
from ..common import upload_project


def test_vgg_convert_object(tmpdir):
    project_name = "vgg_test_object"

    input_dir = Path(
        "tests"
    ) / "converter_test" / "VGG" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "VGG", "vgg_test", "Vector", "object_detection"
    )

    description = 'vgg object detection'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_vgg_convert_instance(tmpdir):
    project_name = "vgg_test_instance"

    input_dir = Path(
        "tests"
    ) / "converter_test" / "VGG" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "VGG", "vgg_test", "Vector", "instance_segmentation"
    )

    description = 'vgg instance segmentation'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)


def test_vgg_convert_vector(tmpdir):
    project_name = "vgg_test_vector"

    input_dir = Path(
        "tests"
    ) / "converter_test" / "VGG" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "VGG", "vgg_test", "Vector", "vector_annotation"
    )

    description = 'vgg vector annotation'
    ptype = 'Vector'
    upload_project(out_dir, project_name, description, ptype)
