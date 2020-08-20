from pathlib import Path

import superannotate as sa


def test_basic_auth():
    try:
        sa.init(Path("tests") / "config__wrong.json")
    except sa.AOBaseException as e:
        assert e.message == "Couldn't authorize"
    else:
        assert False
    sa.init(Path.home() / ".annotateonline" / "config.json")
