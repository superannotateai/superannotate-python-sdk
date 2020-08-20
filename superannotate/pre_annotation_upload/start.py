import json
import boto3
import traceback
import threading
import os
from .coco_convert import get_jsons_dict


def upload_coco_annotation(image_name,image_data,args,logger):
    try:
        logger.info('start---'+image_name+'----')
        destination = args.destination
        bucket = args.bucket
        session = boto3.Session(aws_access_key_id=args.aws_access_key_id,aws_secret_access_key=args.aws_secret_access_key,aws_session_token=args.aws_session_token)
        s3 = session.resource('s3')
        my_bucket = s3.Bucket(args.bucket)
        put_data = my_bucket.put_object(Body=json.dumps(image_data), Bucket=bucket, Key=destination + '/' + image_name + '___objects.json', ContentType="application/json")
        logger.info('done---'+image_name+'----')
    except Exception as e:
        logger.error(traceback.format_exc())
    
def upload_ao_annotations(file_path,args,logger):
    try:
        logger.info('start---'+file_path+'----')
        file_name = file_path.split('/')[-1]
        destination = args.destination
        bucket = args.bucket
        session = boto3.Session(aws_access_key_id=args.aws_access_key_id,aws_secret_access_key=args.aws_secret_access_key,aws_session_token=args.aws_session_token)
        s3 = session.resource('s3')
        my_bucket = s3.Bucket(args.bucket)
        put_data = my_bucket.upload_file(file_path,destination + '/' + file_name )
        logger.info('done---'+file_name+'----')
    except Exception as e:
        logger.error(traceback.format_exc())

def start(args,logger):
    if(args.ao_jsons):
        pwd = args.ao_jsons
        files = os.listdir(pwd)
        if pwd[-1] != '/':
            pwd += '/'
        for f in files:
            if not '___objects.json' in f:
                continue
            file_path = pwd + f
            t = threading.Thread(target=upload_ao_annotations, args=(file_path,args,logger)).start()

    if(args.coco_json):
        coco_json_path = args.coco_json
        ao_jsons = get_jsons_dict(coco_json_path)
        for image_name in ao_jsons:
            t = threading.Thread(target = upload_coco_annotation, args=(image_name,ao_jsons[image_name],args,logger)).start()


