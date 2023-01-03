from importlib import import_module

from superannotate import SAServer


APPS = ["app"]


def create_app():
    server = SAServer()
    for path in APPS:
        import_module(path)
    return server


app = create_app()
