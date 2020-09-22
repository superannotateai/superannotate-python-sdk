import argparse
import json
import logging
import sys
from pathlib import Path

import superannotate as sa

from .exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")


def ask_token(args):
    config_dir = Path.home() / ".superannotate"
    config_filename = "config.json"
    config_file = config_dir / config_filename
    if config_file.is_file():
        yes_no = input(
            f"File {config_file} exists. Do you want to overwrite? [y/n] : "
        )
        if yes_no != "y":
            return
    token = input(
        "Input the team SDK token from https://app.superannotate.com/team : "
    )
    config_dir.mkdir(exist_ok=True)
    if config_file.is_file():
        existing_config = json.load(open(config_file))
        existing_config["token"] = token
        json.dump(existing_config, open(config_file, "w"), indent=4)
        logger.info("Configuration file %s successfully updated.", config_file)
    else:
        json.dump({"token": token}, open(config_file, "w"), indent=4)
        logger.info("Configuration file %s successfully created.", config_file)


def main():
    if len(sys.argv) == 1:
        print("No command given to superannotate CLI")
        print("Available commands to superannotate CLI are: init")
        return
    command = sys.argv[1]
    further_args = sys.argv[2:]

    if command == "image-upload":
        image_upload(further_args)
    elif command == "init":
        ask_token(further_args)
    else:
        raise SABaseException(0, "Wrong command to superannotate CLI")


def _list_str(values):
    return values.split(',')


def image_upload(args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--project', required=True, help='Project name to upload'
    )
    parser.add_argument(
        '--folder', required=True, help='Folder from which to upload'
    )
    parser.add_argument(
        '--recursive',
        default=False,
        action='store_true',
        help='Enables recursive subfolder upload.'
    )
    parser.add_argument(
        '--extensions',
        default=None,
        type=_list_str,
        help='List of image extensions to include. Default is jpg,png'
    )
    args = parser.parse_args(args)

    sa.upload_images_from_folder_to_project(
        args.project,
        args.folder,
        args.extensions,
        recursive_subfolders=args.recursive
    )


if __name__ == "__main__":
    main()
