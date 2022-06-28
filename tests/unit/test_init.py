import os

from src.superannotate import SAClient
from src.superannotate.lib.core import CONFIG_PATH
from src.superannotate.lib.core import CONFIG
from src.superannotate.lib.infrastructure.repositories import ConfigRepository


def test_init_from_token():
    config_repo = ConfigRepository(CONFIG_PATH)
    main_endpoint = config_repo.get_one("main_endpoint").value
    os.environ.update({"SA_URL": main_endpoint})
    token = config_repo.get_one("token").value

    sa_1 = SAClient(token=token)
    sa_2 = SAClient(token=token)
    sa_1.get_team_metadata()
    sa_2.get_team_metadata()

    assert len(CONFIG.SESSIONS) == 1

