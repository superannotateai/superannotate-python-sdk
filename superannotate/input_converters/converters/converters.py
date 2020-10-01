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
import glob
import os
import json
import shutil
import time

from tqdm import tqdm

from .coco_converters.coco_strategies import ObjectDetectionStrategy, KeypointDetectionStrategy, PanopticConverterStrategy
from .voc_converters.voc_strategies import VocObjectDetectionStrategy
from .labelbox_converters.labelbox_strategies import LabelBoxObjectDetectionStrategy
from .dataloop_converters.dataloop_strategies import DataLoopObjectDetectionStrategy


class Converter(object):
    def __init__(
        self, project_type, task, dataset_name, export_root, output_dir, method
    ):
        self.export_root = export_root
        self.output_dir = output_dir
        self._select_strategy(
            project_type, task, dataset_name, export_root, output_dir, method
        )

    def convert_from_sa(self):
        self.strategy.sa_to_output_format()

    def convert_to_sa(self, platform):
        self.strategy.to_sa_format()
        if platform == "Desktop":
            self._merge_jsons(self.output_dir)

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
        elif method.dataset_format == "LabelBox":
            if task == "object_detection" or task == 'instance_segmentation' or task == 'vector_annotation':
                c_strategy = LabelBoxObjectDetectionStrategy(
                    dataset_name, export_root, project_type, output_dir, task,
                    method.direction
                )
        elif method.dataset_format == "DataLoop":
            if task == 'object_detection' or task == 'instance_segmentation' or task == 'vector_annotation':
                c_strategy = DataLoopObjectDetectionStrategy(
                    dataset_name, export_root, project_type, output_dir, task,
                    method.direction
                )
        else:
            pass
        self.__set_strategy(c_strategy)

    def _merge_jsons(self, input_dir):
        cat_id_map = {}
        classes_json = json.load(
            open(os.path.join(input_dir, "classes", "classes.json"))
        )

        new_classes = []
        for idx, class_ in enumerate(classes_json):
            cat_id_map[class_["id"]] = idx + 2
            class_["id"] = idx + 2
            new_classes.append(class_)

        files = glob.glob(os.path.join(input_dir, "*.json"))
        merged_json = {}
        shutil.rmtree(os.path.join(input_dir, "classes"))
        for f in tqdm(files, "Merging files"):
            json_data = json.load(open(f))
            meta = {
                "type": "meta",
                "name": "lastAction",
                "timestamp": int(round(time.time() * 1000))
            }
            for js_data in json_data:
                if "classId" in js_data:
                    js_data["classId"] = cat_id_map[js_data["classId"]]
            json_data.append(meta)
            file_name = os.path.split(f)[1].replace("___objects.json", "")
            merged_json[file_name] = json_data
            os.remove(f)
        with open(
            os.path.join(input_dir, "annotations.json"), "w"
        ) as final_json_file:
            json.dump(merged_json, final_json_file, indent=2)

        with open(os.path.join(input_dir, "classes.json"), "w") as fw:
            json.dump(classes_json, fw, indent=2)
