from pathlib import Path

import superannotate as sa


def test_basic_auth():
    try:
        sa.init(Path("tests") / "config__wrong.json")
    except sa.SABaseException as e:
        assert e.message == 'Couldn\'t authorize {"error":"Not authorized."}'
    else:
        assert False
    sa.init(Path.home() / ".superannotate" / "config.json")
