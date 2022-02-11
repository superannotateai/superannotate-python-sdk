import os
import sys


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

controller = None


def get_default_controller():
    from lib.infrastructure.controller import Controller

    global controller
    controller = Controller()
    return controller
