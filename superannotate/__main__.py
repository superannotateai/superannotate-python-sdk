import sys
import argparse
import logging
from .image_upload.start import start as image_upload
from .pre_annotation_upload.start import start as pre_annotation_upload
from .input_converters import sa_to_coco
from .input_converters import coco_to_sa
from .exceptions import SABaseException

logging.basicConfig(
    level=logging.INFO,
    format=' %(asctime)s - %(levelname)s - %(message)s',
    datefmt='%I:%M:%S %p'
)
logger = logging.getLogger()


def convert(argv):
    parser.parse_args(argv)


def main():
    command = sys.argv[1]
    further_args = sys.argv[2:]

    if command in ["preannotation-upload", "image-upload"]:
        upload(command, further_args)
    elif command == "convert":
        convert(further_args)
    else:
        raise SABaseException(0, "Wrong command to superannotate cli")


def upload(command, args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--command',
        required=True,
        help=
        'superannotate API action command - visit https://annotate.online for more info.'
    )
    parser.add_argument(
        '--aws_access_key_id',
        required=False,
        help='Find aws_access_key_id for your account after login.'
    )
    parser.add_argument(
        '--aws_secret_access_key',
        required=False,
        help='Find aws_secret_access_key for your account after login.'
    )
    parser.add_argument(
        '--aws_session_token',
        required=False,
        help='Find aws_session_token for your account after login.'
    )
    parser.add_argument(
        '--bucket',
        required=True,
        help='Find bucket for your account after login.'
    )
    parser.add_argument('--project_type', help='superannotate project type.')
    parser.add_argument(
        '--origin', help='Images directory path in local machine.'
    )
    parser.add_argument(
        '--destination', help='Find destination for your account after login.'
    )
    parser.add_argument('--coco_json', help='COCO annotation full path.')
    parser.add_argument(
        '--ao_jsons', help='superannotate annotations directory path.'
    )
    args = parser.parse_args(args)
    if command == "preannotation-upload":
        pre_annotation_upload(args)
    else:
        image_upload(args)


if __name__ == "__main__":
    main()
