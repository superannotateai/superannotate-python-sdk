from pathlib import Path
import os

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")


@pytest.mark.skipif(
    "AO_TEST_LEVEL" not in os.environ or
    os.environ["AO_TEST_LEVEL"] != "stress",
    reason="Requires env variable to be set"
)
def test_download_stress(tmpdir):
    team = sa.get_default_team()

    project = sa.search_projects(team, name_prefix="test_test_15")[0]
    export = sa.prepare_export(project)
    sa.download_export(export, tmpdir)

    count_in_project = sa.get_project_image_count(project)
    count_in_folder = len(list(Path(tmpdir).glob("*.jpg")))

    assert count_in_project == count_in_folder
