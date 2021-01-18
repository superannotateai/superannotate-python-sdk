'''

This object will receive the strategy from outside and will convert according to
   said strategy.

'''
from .coco_converters.coco_strategies import CocoObjectDetectionStrategy, CocoKeypointDetectionStrategy, CocoPanopticConverterStrategy
from .dataloop_converters.dataloop_strategies import DataLoopStrategy
from .googlecloud_converters.googlecloud_strategies import GoogleCloudStrategy
from .labelbox_converters.labelbox_strategies import LabelBoxStrategy
from .sagemaker_converters.sagemaker_strategies import SageMakerStrategy
from .supervisely_converters.supervisely_strategies import SuperviselyStrategy
from .vgg_converters.vgg_strategies import VGGStrategy
from .voc_converters.voc_strategies import VocStrategy
from .vott_converters.vott_strategies import VoTTStrategy
from .yolo_converters.yolo_strategies import YoloStrategy


class Converter(object):
    def __init__(self, args):
        self.output_dir = args.output_dir
        self._select_strategy(args)

    def convert_from_sa(self):
        self.strategy.sa_to_output_format()

    def convert_to_sa(self):
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
        elif args.dataset_format == "DataLoop":
            c_strategy = DataLoopStrategy(args)
        elif args.dataset_format == "GoogleCloud":
            c_strategy = GoogleCloudStrategy(args)
        elif args.dataset_format == "LabelBox":
            c_strategy = LabelBoxStrategy(args)
        elif args.dataset_format == "SageMaker":
            c_strategy = SageMakerStrategy(args)
        elif args.dataset_format == "Supervisely":
            c_strategy = SuperviselyStrategy(args)
        elif args.dataset_format == "VGG":
            c_strategy = VGGStrategy(args)
        elif args.dataset_format == "VOC":
            c_strategy = VocStrategy(args)
        elif args.dataset_format == "VoTT":
            c_strategy = VoTTStrategy(args)
        elif args.dataset_format == "YOLO":
            if args.task == 'object_detection':
                c_strategy = YoloStrategy(args)
        else:
            pass

        self.__set_strategy(c_strategy)
