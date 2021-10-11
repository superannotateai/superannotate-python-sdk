from pathlib import Path

import pytest
import superannotate as sa


@pytest.mark.skip(reason="Need to adjust")
def test_googlecloud_convert_web(tmpdir):
    project_name = "googlcloud_object"

    input_dir = (
        Path("tests") / "converter_test" / "GoogleCloud" / "input" / "toSuperAnnotate"
    )
    out_dir = Path(tmpdir) / project_name
    sa.import_annotation(
        input_dir,
        out_dir,
        "GoogleCloud",
        "image_object_detection",
        "Vector",
        "object_detection",
    )

    description = "googlecloud object detection"
    ptype = "Vector"
    # upload_project(out_dir, project_name, description, ptype)
