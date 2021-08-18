#!/usr/bin/env python3
import logging
import os
import sys
from pathlib import Path

import fire

sys.path.insert(0, "/" + "/".join(Path(os.path.abspath(__file__)).parts[1:6]))

from src.lib.app.interface.cli_interface import CLIFacade

logger = logging.getLogger("superannotate-python-sdk")

# TODO Add help text
HELP_TEXT = ""


if __name__ == "__main__":
    fire.Fire(CLIFacade)
