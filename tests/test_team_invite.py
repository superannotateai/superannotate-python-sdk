from pathlib import Path

import superannotate as sa


def test_team_invite():
    try:
        sa.invite_contributor_to_team("hovnatan@superannotate.com")
    except sa.SABaseException as e:
        assert e.message == 'Couldn\'t invite to team. {"error":"User with hovnatan@superannotate.com email is already member of this team."}'
    else:
        assert False
    # sa.delete_team_contributor_invitation(invite)

    # print(sa.search_team_contributors())
