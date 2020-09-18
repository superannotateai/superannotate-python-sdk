import logging
import json
import sys
from pathlib import Path

from .exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")


def asktoken():
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

    # if command in ["preannotation-upload", "image-upload"]:
    #     upload(command, further_args)
    # elif command == "convert":
    #     convert(further_args)
    if command == "init":
        asktoken()
    else:
        raise SABaseException(0, "Wrong command to superannotate CLI")


# def upload(command, args):
#     parser = argparse.ArgumentParser()
#     parser.add_argument(
#         '--command',
#         required=True,
#         help=
#         'superannotate API action command - visit https://annotate.online for more info.'
#     )
#     parser.add_argument(
#         '--aws_access_key_id',
#         required=False,
#         help='Find aws_access_key_id for your account after login.'
#     )
#     parser.add_argument(
#         '--aws_secret_access_key',
#         required=False,
#         help='Find aws_secret_access_key for your account after login.'
#     )
#     parser.add_argument(
#         '--aws_session_token',
#         required=False,
#         help='Find aws_session_token for your account after login.'
#     )
#     parser.add_argument(
#         '--bucket',
#         required=True,
#         help='Find bucket for your account after login.'
#     )
#     parser.add_argument('--project_type', help='superannotate project type.')
#     parser.add_argument(
#         '--origin', help='Images directory path in local machine.'
#     )
#     parser.add_argument(
#         '--destination', help='Find destination for your account after login.'
#     )
#     parser.add_argument('--coco_json', help='COCO annotation full path.')
#     parser.add_argument(
#         '--ao_jsons', help='superannotate annotations directory path.'
#     )
#     args = parser.parse_args(args)
#     if command == "preannotation-upload":
#         pre_annotation_upload(args)
#     else:
#         image_upload(args)

if __name__ == "__main__":
    main()
