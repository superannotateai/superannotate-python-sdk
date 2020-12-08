from pathlib import Path

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")


def test_team_metadata():
    metadata = sa.get_team_metadata()
    print(metadata)
    assert all(
        [x in metadata for x in ["id", "users", "name", "description", "type"]]
    )

    for user in metadata["users"]:
        assert all(
            [
                x in user for x in
                ["id", "email", "first_name", "last_name", "user_role"]
            ]
        )
