#!/usr/bin/env python3
import fire
from lib.app.interface.cli_interface import CLIFacade
from superannotate.logger import get_default_logger

logger = get_default_logger()


def main():
    fire.Fire(CLIFacade)


if __name__ == "__main__":
    main()
