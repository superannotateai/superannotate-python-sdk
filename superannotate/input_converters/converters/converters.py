'''

This object will receive the strategy from outside and will convert according to
   said strategy.

'''

import glob
import os
import json
import shutil
import time

from tqdm import tqdm

from .coco_converters.coco_strategies import CocoObjectDetectionStrategy, CocoKeypointDetectionStrategy, CocoPanopticConverterStrategy
from .voc_converters.voc_strategies import VocObjectDetectionStrategy
from .labelbox_converters.labelbox_strategies import LabelBoxObjectDetectionStrategy
from .dataloop_converters.dataloop_strategies import DataLoopObjectDetectionStrategy
from .supervisely_converters.supervisely_strategies import SuperviselyObjectDetectionStrategy
from .vott_converters.vott_strategies import VoTTObjectDetectionStrategy
from .sagemaker_converters.sagemaker_strategies import SageMakerObjectDetectionStrategy
from .vgg_converters.vgg_strategies import VGGObjectDetectionStrategy
from .googlecloud_converters.googlecloud_strategies import GoogleCloudObjectDetectionStrategy
from .yolo_converters.yolo_strategies import YoloObjectDetectionStrategy


class Converter(object):
    def __init__(self, args):
        self.output_dir = args.output_dir
        self._select_strategy(args)

    def convert_from_sa(self):
        self.strategy.sa_to_output_format()

    def convert_to_sa(self, platform):
        self.strategy.to_sa_format()

    def __set_strategy(self, c_strategy):
        self.strategy = c_strategy

    def _select_strategy(self, args):
        if args.dataset_format == "COCO":
            if args.task == 'instance_segmentation' or args.task == 'object_detection':
                c_strategy = CocoObjectDetectionStrategy(args)
            if args.task == 'keypoint_detection':
                c_strategy = CocoKeypointDetectionStrategy(args)
            if args.task == 'panoptic_segmentation':
                c_strategy = CocoPanopticConverterStrategy(args)
        elif args.dataset_format == "VOC":
            if args.task == 'instance_segmentation' or args.task == 'object_detection':
                c_strategy = VocObjectDetectionStrategy(args)
        elif args.dataset_format == "LabelBox":
            if args.task == "object_detection" or args.task == 'instance_segmentation' or args.task == 'vector_annotation':
                c_strategy = LabelBoxObjectDetectionStrategy(args)
        elif args.dataset_format == "DataLoop":
            if args.task == 'object_detection' or args.task == 'instance_segmentation' or args.task == 'vector_annotation':
                c_strategy = DataLoopObjectDetectionStrategy(args)
        elif args.dataset_format == "Supervisely":
            if args.task == 'vector_annotation':
                c_strategy = SuperviselyObjectDetectionStrategy(args)
        elif args.dataset_format == "VoTT":
            if args.task == 'object_detection' or args.task == 'instance_segmentation' or args.task == 'vector_annotation':
                c_strategy = VoTTObjectDetectionStrategy(args)
        elif args.dataset_format == "SageMaker":
            if args.task == 'object_detection' or args.task == 'instance_segmentation':
                c_strategy = SageMakerObjectDetectionStrategy(args)
        elif args.dataset_format == "VGG":
            if args.task == 'object_detection' or args.task == 'instance_segmentation' or args.task == 'vector_annotation':
                c_strategy = VGGObjectDetectionStrategy(args)
        elif args.dataset_format == "GoogleCloud":
            if args.task == 'object_detection':
                c_strategy = GoogleCloudObjectDetectionStrategy(args)
        elif args.dataset_format == "YOLO":
            if args.task == 'object_detection':
                c_strategy = YoloObjectDetectionStrategy(args)
        else:
            pass

        self.__set_strategy(c_strategy)
