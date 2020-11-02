import glob
import json
import os
from collections import namedtuple
from datetime import datetime

from panopticapi.utils import IdGenerator, id2rgb
from PIL import Image
from tqdm import tqdm

from .coco_converter import CoCoConverter
from .coco_to_sa_pixel import (
    coco_instance_segmentation_to_sa_pixel,
    coco_panoptic_segmentation_to_sa_pixel
)
from .coco_to_sa_vector import (
    coco_instance_segmentation_to_sa_vector,
    coco_keypoint_detection_to_sa_vector
)
from .sa_pixel_to_coco import (
    sa_pixel_to_coco_instance_segmentation, sa_pixel_to_coco_object_detection,
    sa_pixel_to_coco_panoptic_segmentation
)
from .sa_vector_to_coco import (
    sa_vector_to_coco_instance_segmentation,
    sa_vector_to_coco_keypoint_detection, sa_vector_to_coco_object_detection
)


class CocoPanopticConverterStrategy(CoCoConverter):
    name = "Panoptic converter"

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):
        if self.direction == "to":
            if self.project_type == 'Pixel':
                self.conversion_algorithm = sa_pixel_to_coco_panoptic_segmentation
            elif self.project_type == 'Vector':
                pass
        else:
            self.conversion_algorithm = coco_panoptic_segmentation_to_sa_pixel

    def __str__(self, ):
        return '{} object'.format(self.name)

    def _sa_to_coco_single(self, id_, json_path, id_generator):

        image_commons = self._prepare_single_image_commons(id_, json_path)
        res = self.conversion_algorithm(image_commons, id_generator)

        return res

    def sa_to_output_format(self):
        out_json = self._create_skeleton()
        out_json['categories'] = self._create_categories(
            os.path.join(self.export_root, 'classes_mapper.json')
        )

        panoptic_root = os.path.join(
            self.dataset_name, "panoptic_{}".format(self.dataset_name)
        )

        images = []
        annotations = []
        id_generator = self._make_id_generator()
        jsons = glob.glob(
            os.path.join(self.export_root, '*pixel.json'), recursive=True
        )

        for id_, json_ in tqdm(enumerate(jsons, 1)):
            res = self._sa_to_coco_single(id_, json_, id_generator)

            panoptic_mask = json_[:-len('___pixel.json')] + '.png'

            Image.fromarray(id2rgb(res[2])).save(panoptic_mask)

            annotation = {
                'image_id': res[0]['id'],
                'file_name': panoptic_mask,
                'segments_info': res[1]
            }
            annotations.append(annotation)

            images.append(res[0])

        out_json['annotations'] = annotations
        out_json['images'] = images
        json_data = json.dumps(out_json, indent=4)
        with open(
            os.path.join(self.output_dir, '{}.json'.format(self.dataset_name)),
            'w+'
        ) as coco_json:

            coco_json.write(json_data)

        self.set_num_converted(len(jsons))

    def to_sa_format(self):
        json_data = os.path.join(self.export_root, self.dataset_name + ".json")
        sa_classes = self._create_sa_classes(json_data)
        sa_jsons = self.conversion_algorithm(json_data, self.output_dir)
        self.dump_output(sa_classes, sa_jsons)


class CocoObjectDetectionStrategy(CoCoConverter):
    name = "ObjectDetection converter"

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):

        if self.direction == "to":
            if self.project_type == 'Pixel':
                if self.task == 'instance_segmentation':
                    self.conversion_algorithm = sa_pixel_to_coco_instance_segmentation
                elif self.task == 'object_detection':
                    self.conversion_algorithm = sa_pixel_to_coco_object_detection

            elif self.project_type == 'Vector':
                if self.task == 'instance_segmentation':
                    self.conversion_algorithm = sa_vector_to_coco_instance_segmentation
                elif self.task == 'object_detection':
                    self.conversion_algorithm = sa_vector_to_coco_object_detection
        else:
            if self.project_type == 'Pixel':
                if self.task == 'instance_segmentation':
                    self.conversion_algorithm = coco_instance_segmentation_to_sa_pixel
                elif self.task == 'object_detection':
                    raise ValueError('Method not implemented')
            elif self.project_type == 'Vector':
                if self.task == 'instance_segmentation':
                    self.conversion_algorithm = coco_instance_segmentation_to_sa_vector
                elif self.task == 'object_detection':
                    raise ValueError('Method not implemented')

    def __str__(self, ):
        return '{} object'.format(self.name)

    def _sa_to_coco_single(self, id_, json_path, id_generator):

        image_commons = self._prepare_single_image_commons(id_, json_path)
        annotations_per_image = []

        def make_annotation(
            category_id, image_id, bbox, segmentation, area, anno_id
        ):
            if self.task == 'object_detection':
                segmentation = [
                    [
                        bbox[0], bbox[1], bbox[0], bbox[1] + bbox[3],
                        bbox[0] + bbox[2], bbox[1] + bbox[3], bbox[0] + bbox[2],
                        bbox[1]
                    ]
                ]
            annotation = {
                'id': anno_id,  # making sure ids are unique
                'image_id': image_id,
                'segmentation': segmentation,
                'iscrowd': 0,
                'bbox': bbox,
                'area': area,
                'category_id': category_id
            }

            return annotation

        res = self.conversion_algorithm(
            make_annotation, image_commons, id_generator
        )
        return res

    def sa_to_output_format(self):

        out_json = self._create_skeleton()
        out_json['categories'] = self._create_categories(
            os.path.join(self.export_root, 'classes_mapper.json')
        )
        jsons = self._load_sa_jsons()
        images = []
        annotations = []
        id_generator = self._make_id_generator()
        for id_, json_ in tqdm(enumerate(jsons)):
            try:
                res = self._sa_to_coco_single(id_, json_, id_generator)
            except Exception as e:
                raise
            images.append(res[0])
            if len(res[1]) < 1:
                self.increase_converted_count()
            for ann in res[1]:
                annotations.append(ann)
        out_json['annotations'] = annotations
        out_json['images'] = images

        json_data = json.dumps(out_json, indent=4)
        with open(
            os.path.join(self.output_dir, '{}.json'.format(self.dataset_name)),
            'w+'
        ) as coco_json:
            coco_json.write(json_data)
        print("NUMBER OF IMAGES FAILED TO CONVERT", self.failed_conversion_cnt)

        self.set_num_converted(len(jsons))

    def to_sa_format(self):
        json_data = os.path.join(self.export_root, self.dataset_name + ".json")
        sa_classes = self._create_sa_classes(json_data)
        sa_jsons = self.conversion_algorithm(json_data, self.output_dir)
        self.dump_output(sa_classes, sa_jsons)


class CocoKeypointDetectionStrategy(CoCoConverter):
    name = 'Keypoint Detection Converter'

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __str__(self):
        return '{} object'.format(self.name)

    def __setup_conversion_algorithm(self):
        if self.direction == "to":
            self.conversion_algorithm = sa_vector_to_coco_keypoint_detection
        else:
            self.conversion_algorithm = coco_keypoint_detection_to_sa_vector

    def __make_image_info(self, json_path, id_, source_type):
        if source_type == 'Pixel':
            rm_len = len('___pixel.json')
        elif source_type == 'Vector':
            rm_len = len('___objects.json')

        image_path = json_path[:-rm_len]

        img_width, img_height = Image.open(image_path).size
        image_info = {
            'id': id_,
            'file_name': image_path[len(self.output_dir):],
            'height': img_height,
            'width': img_width,
            'license': 1
        }

        return image_info

    def sa_to_output_format(self):
        out_json = self._create_skeleton()
        jsons = self._load_sa_jsons()

        images = []
        annotations = []

        id_generator = self._make_id_generator()
        id_generator_anno = self._make_id_generator()
        id_generator_img = self._make_id_generator()
        res = self.conversion_algorithm(
            jsons, id_generator, id_generator_anno, id_generator_img,
            self.__make_image_info
        )

        out_json['categories'] = res[0]
        out_json['annotations'] = res[1]
        out_json['images'] = res[2]
        json_data = json.dumps(out_json, indent=4)

        with open(
            os.path.join(self.output_dir, '{}.json'.format(self.dataset_name)),
            'w+'
        ) as coco_json:
            coco_json.write(json_data)

        self.set_num_converted(len(out_json['images']))

    def to_sa_format(self):
        json_data = os.path.join(self.export_root, self.dataset_name + ".json")
        sa_classes = self._create_sa_classes(json_data)
        sa_jsons = self.conversion_algorithm(json_data, self.output_dir)
        self.dump_output(sa_classes, sa_jsons)
