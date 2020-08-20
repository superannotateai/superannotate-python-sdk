from pathlib import Path

import superannotate as sa

sa.init(Path.home() / ".annotateonline" / "config.json")


def test_basic_team():
    teams = sa.search_teams("hfg1")
    for team in teams:
        sa.delete_team(team)

    sa.create_team("hfg1", "pppppp")
    teams = sa.search_teams("hfg1")
    assert len(teams) == 1
    sa.delete_team(teams[0])
