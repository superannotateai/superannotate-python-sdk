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


class Converter(object):
    def __init__(self, args):
        self.output_dir = args.output_dir
        self._select_strategy(args)

    def convert_from_sa(self):
        self.strategy.sa_to_output_format()

    def convert_to_sa(self, platform):
        self.strategy.to_sa_format()
        if platform == "Desktop":
            self._merge_jsons(self.output_dir)

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
