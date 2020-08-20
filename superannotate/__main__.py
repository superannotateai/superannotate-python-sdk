import sys
import argparse
import logging
from .image_upload.start import start as image_upload
from .pre_annotation_upload.start import start as pre_annotation_upload

logging.basicConfig(level=logging.INFO,format=' %(asctime)s - %(levelname)s - %(message)s',datefmt='%I:%M:%S %p')
logger = logging.getLogger()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--command' , required=True , help='AnnotateOnline API action command - visit https://annotate.online for more info.')
    parser.add_argument('--aws_access_key_id' ,required=True , help='Find aws_access_key_id for your account after login.')
    parser.add_argument('--aws_secret_access_key',required=True,help='Find aws_secret_access_key for your account after login.')
    parser.add_argument('--aws_session_token',required=True, help='Find aws_session_token for your account after login.')
    parser.add_argument('--bucket',required=True,help='Find bucket for your account after login.')
    parser.add_argument('--project_type', help='AnnotateOnline project type.')
    parser.add_argument('--origin',help='Images directory path in local machine.')
    parser.add_argument('--destination',help='Find destination for your account after login.')
    parser.add_argument('--coco_json',help='COCO annotation full path.')
    parser.add_argument('--ao_jsons',help='AnnotateOnline annotations directory path.'),
    args = parser.parse_args()

    if args.command == "pre_annotation_upload":
        pre_annotation_upload(args,logger)
    if args.command == "image_upload":
        image_upload(args,logger)
       
    
if __name__ == "__main__":
    main()



