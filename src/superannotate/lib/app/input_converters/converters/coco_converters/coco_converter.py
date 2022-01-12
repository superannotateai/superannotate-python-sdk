"""
"""
import json
from collections import namedtuple
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from superannotate.logger import get_default_logger

from ....common import id2rgb
from ....common import write_to_json
from ..baseStrategy import baseStrategy

logger = get_default_logger()


class CocoBaseStrategy(baseStrategy):
    project_type_to_json_ending = {
        "pixel": "___pixel.json",
        "vector": "___objects.json",
    }

    def __init__(self, args):
        self.total_images_num = 0
        super().__init__(args)

    def set_num_total_images(self, num):
        self.total_images_num = num

    def get_num_total_images(self):
        return self.total_images_num

    def _create_categories(self, path_to_classes):

        classes = None
        s_class = namedtuple("Class", ["class_name", "id"])

        with open(path_to_classes) as fp:
            classes = json.load(fp)
        categories = [
            self._create_single_category(s_class(item, classes[item]))
            for item in classes
        ]
        return categories

    def _create_single_category(self, item):
        category = {
            "id": item.id,
            "name": item.class_name,
            "supercategory": item.class_name,
            "isthing": 1,
            "color": id2rgb(item.id),
        }
        return category

    def _make_id_generator(self):
        cur_id = 0
        while True:
            cur_id += 1
            yield cur_id

    def _create_skeleton(self):
        out_json = {
            "info": {
                "description": f"This is {self.dataset_name} dataset.",
                "url": "https://superannotate.ai",
                "version": "1.0",
                "year": datetime.now().year,
                "contributor": "Superannotate AI",
                "date_created": datetime.now().strftime("%d/%m/%Y"),
            },
            "licenses": [
                {"url": "https://superannotate.ai", "id": 1, "name": "Superannotate AI"}
            ],
            "images": [],
            "annotations": [],
            "categories": [],
        }
        return out_json

    def convert_from_old_sa_to_new(self, old_json_data, project_type):

        new_json_data = {"metadata": {}, "instances": [], "tags": [], "comments": []}

        meta_keys = [
            "name",
            "width",
            "height",
            "status",
            "pinned",
            "isPredicted",
            "projectId",
            "annotatorEmail",
            "qaEmail",
        ]
        if project_type == "pixel":
            meta_keys.append("isSegmented")

        new_json_data["metadata"] = dict.fromkeys(meta_keys)

        metadata = new_json_data["metadata"]

        for item in old_json_data:
            object_type = item.get("type")

            # add metadata
            if object_type == "meta":
                meta_name = item["name"]
                if meta_name == "imageAttributes":
                    metadata["height"] = item.get("height")
                    metadata["width"] = item.get("width")
                    metadata["status"] = item.get("status")
                    metadata["pinned"] = item.get("pinned")
                if meta_name == "lastAction":
                    metadata["lastAction"] = dict.fromkeys(["email", "timestamp"])
                    metadata["lastAction"]["email"] = item.get("userId")
                    metadata["lastAction"]["timestamp"] = item.get("timestamp")
            # add tags
            elif object_type == "tag":
                new_json_data["tags"].append(item.get("name"))
            # add comments
            elif object_type == "comment":
                item.pop("type")
                item["correspondence"] = item["comments"]
                for comment in item["correspondence"]:
                    comment["email"] = comment["id"]
                    comment.pop("id")
                item.pop("comments")
                new_json_data["comments"].append(item)
            # add instances
            else:
                new_json_data["instances"].append(item)
        return new_json_data

    def _parse_json_into_common_format(self, sa_annotation_json, fpath):
        """
           If the annotation format ever changes this function will handle it and
           return something optimal for the converters. Additionally, if anything
           important is absent from the current json, this function fills it.
        """
        if isinstance(sa_annotation_json, list):
            sa_annotation_json = self.convert_from_old_sa_to_new(
                sa_annotation_json, self.project_type
            )
        if "metadata" not in sa_annotation_json:
            sa_annotation_json["metadata"] = {}

        if "tags" not in sa_annotation_json:
            sa_annotation_json["tags"] = []

        if "instances" not in sa_annotation_json:
            sa_annotation_json["instances"] = []
        if "comments" not in sa_annotation_json:
            sa_annotation_json["comments"] = []

        if (
            "name" not in sa_annotation_json["metadata"]
            or sa_annotation_json["metadata"]["name"] is None
        ):
            fname = fpath.name
            fname = fname[
                : -len(self.project_type_to_json_ending[self.project_type.lower()])
            ]
            sa_annotation_json["metadata"]["name"] = fname
        sa_annotation_json["metadata"]["image_path"] = str(
            Path(fpath).parent / sa_annotation_json["metadata"]["name"]
        )

        sa_annotation_json["metadata"]["annotation_json"] = fpath
        if self.task == "panoptic_segmentation":
            panoptic_mask = str(
                Path(self.export_root)
                / (sa_annotation_json["metadata"]["name"] + ".png")
            )

            sa_annotation_json["metadata"]["panoptic_mask"] = panoptic_mask

        if self.project_type == "Pixel":
            sa_annotation_json["metadata"]["sa_bluemask_path"] = str(
                Path(self.export_root)
                / (sa_annotation_json["metadata"]["name"] + "___save.png")
            )

        if not isinstance(
            sa_annotation_json["metadata"].get("height", None), int
        ) or not isinstance(sa_annotation_json["metadata"].get("width", None), int):
            image_height, image_width = self.get_image_dimensions(
                sa_annotation_json["metadata"]["image_path"]
            )
            sa_annotation_json["metadata"]["height"] = image_height
            sa_annotation_json["metadata"]["width"] = image_width

        return sa_annotation_json

    def get_image_dimensions(self, image_path):

        img_height = None
        img_width = None

        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            dimensions = img.shape
            img_height, img_width = (dimensions[0], dimensions[1])
        else:
            try:
                img = Image.open(image_path)
                img_width, img_height = img.size()
            except Exception as e:
                raise

        return img_height, img_width

    def _prepare_single_image_commons_pixel(self, id_, metadata):

        ImgCommons = namedtuple(
            "ImgCommons", ["image_info", "ann_mask", "sa_bluemask_rgb", "flat_mask"]
        )
        sa_bluemask_path = metadata["sa_bluemask_path"]

        image_info = self._make_image_info(
            metadata["name"], metadata["height"], metadata["width"], id_
        )

        sa_bluemask_rgb = np.asarray(
            Image.open(sa_bluemask_path).convert("RGB"), dtype=np.uint32
        )

        ann_mask = np.zeros(
            (image_info["height"], image_info["width"]), dtype=np.uint32
        )
        flat_mask = (
            (sa_bluemask_rgb[:, :, 0] << 16)
            | (sa_bluemask_rgb[:, :, 1] << 8)
            | (sa_bluemask_rgb[:, :, 2])
        )

        res = ImgCommons(image_info, ann_mask, sa_bluemask_rgb, flat_mask)

        return res

    def _prepare_single_image_commons_vector(self, id_, metadata):

        ImgCommons = namedtuple("ImgCommons", ["image_info"])

        image_info = self._make_image_info(
            metadata["name"], metadata["height"], metadata["width"], id_
        )

        res = ImgCommons(image_info)

        return res

    def _prepare_single_image_commons(self, id_, metadata):
        res = None
        if self.project_type == "Pixel":
            res = self._prepare_single_image_commons_pixel(id_, metadata)
        elif self.project_type == "Vector":
            res = self._prepare_single_image_commons_vector(id_, metadata)
        return res

    def _make_image_info(self, pname, pheight, pwidth, id_):
        image_info = {
            "id": id_,
            "file_name": pname,
            "height": pheight,
            "width": pwidth,
            "license": 1,
        }

        return image_info

    def _create_sa_classes(self, json_path):
        json_data = json.load(open(json_path))
        classes_list = json_data["categories"]

        classes = []
        for data in classes_list:
            color = np.random.choice(range(256), size=3)
            hexcolor = "#%02x%02x%02x" % tuple(color)
            classes_dict = {
                "name": data["name"],
                "color": hexcolor,
                "attribute_groups": [],
            }
            classes.append(classes_dict)

        return classes

    def to_sa_format(self):
        json_data = self.export_root / (self.dataset_name + ".json")
        sa_classes = self._create_sa_classes(json_data)
        (self.output_dir / "classes").mkdir(parents=True, exist_ok=True)
        write_to_json(self.output_dir / "classes" / "classes.json", sa_classes)
        self.conversion_algorithm(json_data, self.output_dir)

    def make_anno_json_generator(self):
        json_data = None

        if self.project_type == "Pixel":
            jsons = list(Path(self.export_root).glob("*pixel.json"))
        elif self.project_type == "Vector":
            jsons = list(Path(self.export_root).glob("*objects.json"))

        self.set_num_total_images(len(jsons))
        print()
        for fpath in jsons:
            with open(fpath) as fp:
                json_data = json.load(fp)
                json_data = self._parse_json_into_common_format(json_data, fpath)

            yield json_data
