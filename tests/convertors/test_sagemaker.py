from pathlib import Path

import pytest
import superannotate as sa


@pytest.mark.skip(reason="Need to adjust")
def test_sagemaker_instance_segmentation(tmpdir):
    project_name = "sagemaker_instance_pixel"

    input_dir = (
        Path("tests")
        / "converter_test"
        / "SageMaker"
        / "input"
        / "toSuperAnnotate"
        / "instance_segmentation"
    )
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir,
        out_dir,
        "SageMaker",
        "test-obj-detect",
        "Pixel",
        "instance_segmentation",
    )

    description = "sagemaker vector instance segmentation"
    ptype = "Pixel"
    upload_project(out_dir, project_name, description, ptype)


@pytest.mark.skip(reason="Need to adjust")
def test_sagemaker_object_detection(tmpdir):
    project_name = "sagemaker_object_vector"

    input_dir = (
        Path("tests")
        / "converter_test"
        / "SageMaker"
        / "input"
        / "toSuperAnnotate"
        / "object_detection"
    )
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir, out_dir, "SageMaker", "test-obj-detect", "Vector", "object_detection"
    )

    description = "sagemaker object detection"
    ptype = "Vector"
    # upload_project(out_dir, project_name, description, ptype)
