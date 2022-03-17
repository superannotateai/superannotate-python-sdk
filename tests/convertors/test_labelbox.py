from pathlib import Path

import pytest

import superannotate as sa


@pytest.mark.skip(reason="Need to adjust")
def test_labelbox_convert_vector(tmpdir):
    project_name = "labelbox_vector_annotation"

    input_dir = (
            Path("tests")
            / "converter_test"
            / "LabelBox"
            / "vector_annotations"
            / "toSuperAnnotate"
    )
    out_dir = Path(tmpdir) / project_name
    dataset_name = "labelbox_example"
    sa.import_annotation(
        input_dir, out_dir, "LabelBox", dataset_name, "Vector", "vector_annotation"
    )

    description = "labelbox vector vector annotation"
    ptype = "Vector"
    # upload_project(out_dir, project_name, description, ptype)


@pytest.mark.skip(reason="Need to adjust")
def test_labelbox_convert_object(tmpdir):
    project_name = "labelbox_object_vector"

    input_dir = (
            Path("tests")
            / "converter_test"
            / "LabelBox"
            / "vector_annotations"
            / "toSuperAnnotate"
    )
    out_dir = Path(tmpdir) / project_name
    dataset_name = "labelbox_example"
    sa.import_annotation(
        input_dir, out_dir, "LabelBox", dataset_name, "Vector", "object_detection"
    )

    description = "labelbox vector object detection"
    ptype = "Vector"
    # upload_project(out_dir, project_name, description, ptype)


@pytest.mark.skip(reason="Need to adjust")
def test_labelbox_convert_instance(tmpdir):
    project_name = "labelbox_vector_instance"

    input_dir = (
            Path("tests")
            / "converter_test"
            / "LabelBox"
            / "vector_annotations"
            / "toSuperAnnotate"
    )
    out_dir = Path(tmpdir) / project_name
    dataset_name = "labelbox_example"
    sa.import_annotation(
        input_dir, out_dir, "LabelBox", dataset_name, "Vector", "instance_segmentation"
    )

    description = "labelbox vector instance_segmentation"
    ptype = "Vector"
    # upload_project(out_dir, project_name, description, ptype)


@pytest.mark.skip(reason="Need to adjust")
def test_labelbox_convert_instance_pixel(tmpdir):
    project_name = "labelbox_pixel_instance"

    input_dir = (
            Path("tests")
            / "converter_test"
            / "LabelBox"
            / "instance_segmentation"
            / "toSuperAnnotate"
    )
    out_dir = Path(tmpdir) / project_name
    dataset_name = "labelbox_example"
    sa.import_annotation(
        input_dir, out_dir, "LabelBox", dataset_name, "Pixel", "instance_segmentation"
    )

    description = "labelbox pixel instance_segmentation"
    ptype = "Pixel"
    # upload_project(out_dir, project_name, description, ptype)
