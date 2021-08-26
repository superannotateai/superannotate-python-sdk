from pathlib import Path

import pytest
import superannotate as sa


@pytest.mark.skip(reason="Need to adjust")
def test_dataloop_convert_vector(tmpdir):
    project_name = "dataloop2sa_vector_annotation"

    input_dir = (
        Path("tests") / "converter_test" / "DataLoop" / "input" / "toSuperAnnotate"
    )
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "DataLoop", "", "Vector", "vector_annotation"
    )

    description = "dataloop vector annotation"
    ptype = "Vector"
    # upload_project(out_dir, project_name, description, ptype)


@pytest.mark.skip(reason="Need to adjust")
def test_dataloop_convert_object(tmpdir):
    project_name = "dataloop2sa_vector_object"

    input_dir = (
        Path("tests") / "converter_test" / "DataLoop" / "input" / "toSuperAnnotate"
    )
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "DataLoop", "", "Vector", "object_detection"
    )

    description = "dataloop object detection"
    ptype = "Vector"
    # upload_project(out_dir, project_name, description, ptype)


@pytest.mark.skip(reason="Need to adjust")
def test_dataloop_convert_instance(tmpdir):
    project_name = "dataloop2sa_vector_instance"

    input_dir = (
        Path("tests") / "converter_test" / "DataLoop" / "input" / "toSuperAnnotate"
    )
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "DataLoop", "", "Vector", "instance_segmentation"
    )
    description = "dataloop instance segmentation"
    ptype = "Vector"
    # upload_project(out_dir, project_name, description, ptype)
