'''
This may look over-engineered at this point however the idea is the following:
1. We eventually might want to convert to and from other formats than COCO
2. For each of these formats (COCO included) there should be different strategies
   for conversion. In COCO's case there are 5
   1.1 Panoptic
   1.2 Object Detection
   1.3 Stuff Detection
   1.4 Keypoint Detection
   1.5 Image Captioning
3. We will have a general Converter object will not care about the format or the
   conversion strategy. It has to methods:
   3.1 convert from sa format to desired format` convert_from_sa()
   3.2 convert from some format to sa format` convert_to_sa()
4. This object will receive the strategy from outside and will convert according to
   said strategy.
'''
from .cococonverters.cocostrategies import ObjectDetectionStrategy, KeypointDetectionStrategy, PanopticConverterStrategy
from .vocconverters.vocstrategies import VocObjectDetectionStrategy


class Converter(object):
    def __init__(
        self, project_type, task, dataset_name, export_root, output_dir, method
    ):
        self._select_strategy(
            project_type, task, dataset_name, export_root, output_dir, method
        )

    def convert_from_sa(self):
        self.strategy.sa_to_output_format()

    def convert_to_sa(self):
        print(self.strategy)
        self.strategy.to_sa_format()

    def __set_strategy(self, c_strategy):
        self.strategy = c_strategy

    def _select_strategy(
        self, project_type, task, dataset_name, export_root, output_dir, method
    ):
        if method.dataset_format == "COCO":
            if task == 'instance_segmentation' or task == 'object_detection':
                c_strategy = ObjectDetectionStrategy(
                    dataset_name, export_root, project_type, output_dir, task,
                    method.direction
                )
            if task == 'keypoint_detection':
                c_strategy = KeypointDetectionStrategy(
                    dataset_name, export_root, project_type, output_dir,
                    method.direction
                )
            if task == 'panoptic_segmentation':
                c_strategy = PanopticConverterStrategy(
                    dataset_name, export_root, project_type, output_dir,
                    method.direction
                )
        elif method.dataset_format == "VOC":
            if task == 'instance_segmentation' or task == 'object_detection':
                c_strategy = VocObjectDetectionStrategy(
                    dataset_name, export_root, project_type, output_dir, task,
                    method.direction
                )
        else:
            pass
        self.__set_strategy(c_strategy)
