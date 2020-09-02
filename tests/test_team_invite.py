from pathlib import Path

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")


def test_team_invite():
    invite = sa.invite_contributor_to_team("hovnatan@supenotate.com", "QA")

    sa.delete_team_contributor_invitation(invite)

    # print(sa.search_team_contributors())
