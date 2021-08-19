#!/usr/bin/env python3
import logging

import fire
from lib.app.interface.cli_interface import CLIFacade

logger = logging.getLogger("superannotate-python-sdk")

# TODO Add help text
HELP_TEXT = ""


def main():
    fire.Fire(CLIFacade)


if __name__ == "__main__":
    main()
