from mixpanel import Mixpanel
from .config import TOKEN
from ..version import __version__

mp = Mixpanel(TOKEN)


def get_default(team_name, user_id, project_name=None):
    return {
        "SDK": True,
        "Paid": True,
        "Team": team_name,
        "Team Owner": user_id,
        "Project Name": project_name,
        "Project Role": "Admin",
        "Version": __version__
    }
