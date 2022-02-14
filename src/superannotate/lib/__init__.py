import os
import sys


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DEFAULT_CONTROLLER = None


def get_default_controller(raise_exception=False):
    from lib.infrastructure.controller import Controller
    try:
        global DEFAULT_CONTROLLER
        if not DEFAULT_CONTROLLER:
            DEFAULT_CONTROLLER = Controller()
        return DEFAULT_CONTROLLER
    except Exception:
        if raise_exception:
            raise


def set_default_controller(controller_obj):
    # global DEFAULT_CONTROLLER
    DEFAULT_CONTROLLER = controller_obj
