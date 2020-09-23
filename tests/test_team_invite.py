from pathlib import Path

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")


def test_team_invite():
    try:
        sa.invite_contributor_to_team("hovnatan@supenotate.com")
    except sa.SABaseException as e:
        assert e.message == 'Couldn\'t invite to team. {"error":"User with hovnatan@supenotate.com email is already invited to this team."}'
    else:
        assert False

    # sa.delete_team_contributor_invitation(invite)

    # print(sa.search_team_contributors())
