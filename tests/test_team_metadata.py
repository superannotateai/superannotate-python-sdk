from pathlib import Path

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")


def test_team_metadata():
    metadata = sa.get_team_metadata(convert_users_role_to_string=True)
    print(len(metadata["users"]))
    print(metadata["users"])
