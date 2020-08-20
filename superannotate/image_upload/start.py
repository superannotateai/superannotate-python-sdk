import os
from PIL import Image
import boto3
import math  
from io import BytesIO
import traceback
import threading
from queue import Queue
from threading import Thread

RESIZE_CONFIG = {
    'Pixel' : 4000000, 
    'Vector' : 100000000 
}

def resize(image_path,args,logger):
    try:
        logger.info('starting ----'+image_path+'----')
        bucket = args.bucket
        project_type = args.project_type
        destination  = args.destination
        img_name = image_path.split('/')[-1]
        im = Image.open(image_path)
        width, height = im.size
        maxSize = RESIZE_CONFIG[project_type]
        session = boto3.Session(aws_access_key_id=args.aws_access_key_id,aws_secret_access_key=args.aws_secret_access_key,aws_session_token=args.aws_session_token)
        s3 = session.resource('s3')
        my_bucket = s3.Bucket(args.bucket)
        if (width * height) > maxSize:
            maxSizeRoot = math.sqrt(maxSize)
            nwidth = math.floor(maxSizeRoot * math.sqrt(width / height))
            nheight = math.floor(maxSizeRoot * math.sqrt(height / width))
            im = im.resize((nwidth,nheight))
        byte_io = BytesIO()
        im.convert('RGB').save(byte_io,'JPEG')
        put_img = my_bucket.put_object(Body=byte_io.getvalue(), Bucket=bucket, Key=destination + '/' + img_name , ContentType="image/jpeg")    
        byte_io = BytesIO()
        im.convert('RGB').save(byte_io,'JPEG',dpi=(96, 96))
        put_img = my_bucket.put_object(Body=byte_io.getvalue(), Bucket=bucket, Key=destination + '/' + img_name +'___lores.jpg' , ContentType="image/jpeg")
        byte_io = BytesIO()
        im.convert('RGB').resize((128, 96)).save(byte_io, 'JPEG',dpi=(96, 96))
        put_img = my_bucket.put_object(Body=byte_io.getvalue(), Bucket=bucket, Key=destination + '/' + img_name + '___thumb.jpg', ContentType="image/jpeg")        
        logger.info('done ----'+image_path+'----')
    except Exception as e:
        logger.error(traceback.format_exc())

class AppWorker(Thread):

    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # Get the work from the queue and expand the tuple
            image_path,args,logger = self.queue.get()
            try:
                logger.info('runing {}'.format(image_path))
                resize(image_path,args,logger)
            finally:
                self.queue.task_done()

def start(args,logger):
    pwd = args.origin
    files = os.listdir(pwd)
    if pwd[-1] != '/':
        pwd += '/'
    # Create a queue to communicate with the worker threads
    queue = Queue()
    # Create 8 worker threads
    for x in range(8):
        worker = AppWorker(queue)
        # Setting daemon to True will let the main thread exit even though the workers are blocking
        worker.daemon = True
        worker.start()
    # Put the tasks into the queue as a tuple
    for f in files:
        image_path = pwd+f
        logger.info('Queueing {}'.format(image_path))
        queue.put((image_path,args,logger))
    # Causes the main thread to wait for the queue to finish processing all the tasks
    queue.join()