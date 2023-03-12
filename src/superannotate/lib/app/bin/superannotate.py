#!/usr/bin/env python3
import logging

import fire
from lib.app.interface.cli_interface import CLIFacade

logger = logging.getLogger("sa")


def main():
    fire.Fire(CLIFacade)


if __name__ == "__main__":
    main()
