import os
import sys


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_default_controller():
    from lib.infrastructure.controller import Controller

    return Controller.get_default()
