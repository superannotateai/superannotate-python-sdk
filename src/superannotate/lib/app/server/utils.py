import typing
from importlib import import_module


def setup_app(apps: typing.List[str]):
    apps.extend(["superannotate.lib.app.server.default_app"])
    for path in apps:
        import_module(path)
