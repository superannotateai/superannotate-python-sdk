from pathlib import Path

import pytest
import superannotate as sa


@pytest.mark.skip(reason="Need to adjust")
def test_vott_convert_object(tmpdir):
    project_name = "vott_object"
    input_dir = Path("tests") / "converter_test" / "VoTT" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(input_dir, out_dir, "VoTT", "", "Vector", "object_detection")

    description = "vott object detection"
    ptype = "Vector"
    # upload_project(out_dir, project_name, description, ptype)


@pytest.mark.skip(reason="Need to adjust")
def test_vott_convert_instance(tmpdir):
    project_name = "vott_vector_instance"
    input_dir = Path("tests") / "converter_test" / "VoTT" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "VoTT", "", "Vector", "instance_segmentation"
    )

    description = "vott instance segmentation"
    ptype = "Vector"
    # upload_project(out_dir, project_name, description, ptype)


@pytest.mark.skip(reason="Need to adjust")
def test_vott_convert_vector(tmpdir):
    project_name = "vott_vector_annotation"

    input_dir = Path("tests") / "converter_test" / "VoTT" / "input" / "toSuperAnnotate"
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(input_dir, out_dir, "VoTT", "", "Vector", "vector_annotation")

    description = "vott vector annotation"
    ptype = "Vector"
    # upload_project(out_dir, project_name, description, ptype)
