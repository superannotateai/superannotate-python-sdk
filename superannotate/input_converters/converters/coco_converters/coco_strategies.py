import json
import numpy as np

from collections import namedtuple
from datetime import datetime

from pathlib import Path
from PIL import Image
from tqdm import tqdm

from ..baseStrategy import baseStrategy

from ....common import id2rgb, write_to_json


class CocoBaseStrategy(baseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def _create_categories(self, path_to_classes):

        classes = None
        s_class = namedtuple('Class', ['class_name', 'id'])

        with open(path_to_classes, 'r') as fp:
            classes = json.load(fp)
        categories = [
            self._create_single_category(s_class(item, classes[item]))
            for item in classes
        ]
        return categories

    def _create_single_category(self, item):
        category = {
            'id': item.id,
            'name': item.class_name,
            'supercategory': item.class_name,
            'isthing': 1,
            'color': id2rgb(item.id)
        }
        return category

    def _make_id_generator(self):
        cur_id = 0
        while True:
            cur_id += 1
            yield cur_id

    def _create_skeleton(self):
        out_json = {
            'info':
                {
                    'description':
                        'This is {} dataset.'.format(self.dataset_name),
                    'url':
                        'https://superannotate.ai',
                    'version':
                        '1.0',
                    'year':
                        2020,
                    'contributor':
                        'Superannotate AI',
                    'date_created':
                        datetime.now().strftime("%d/%m/%Y")
                },
            'licenses':
                [
                    {
                        'url': 'https://superannotate.ai',
                        'id': 1,
                        'name': 'Superannotate AI'
                    }
                ],
            'images': [],
            'annotations': [],
            'categories': []
        }
        return out_json

    def _load_sa_jsons(self):
        if self.project_type == 'Pixel':
            jsons_gen = self.export_root.glob('*pixel.json')
        elif self.project_type == 'Vector':
            jsons_gen = self.export_root.glob('*objects.json')
        jsons = list(jsons_gen)
        self.set_num_converted(len(jsons))
        return jsons

    def _prepare_single_image_commons_pixel(self, id_, json_path):
        ImgCommons = namedtuple(
            'ImgCommons', [
                'image_info', 'sa_ann_json', 'ann_mask', 'sa_bluemask_rgb',
                'flat_mask'
            ]
        )
        rm_len = len('___pixel.json')

        sa_json = json.load(open(json_path))
        sa_ann_json = sa_json['instances']

        sa_bluemask_path = str(json_path)[:-rm_len] + '___save.png'

        image_info = self.__make_image_info(id_, sa_json['metadata'])

        if image_info['height'] is None or image_info['width'] is None:
            img_height, img_width = self.get_dimensions(
                json_path, self.project_type
            )
            image_info['height'] = img_height
            image_info['width'] = img_width

        sa_bluemask_rgb = np.asarray(
            Image.open(sa_bluemask_path).convert('RGB'), dtype=np.uint32
        )

        ann_mask = np.zeros(
            (image_info['height'], image_info['width']), dtype=np.uint32
        )
        flat_mask = (sa_bluemask_rgb[:, :, 0] <<
                     16) | (sa_bluemask_rgb[:, :, 1] <<
                            8) | (sa_bluemask_rgb[:, :, 2])

        res = ImgCommons(
            image_info, sa_ann_json, ann_mask, sa_bluemask_rgb, flat_mask
        )

        return res

    def get_dimensions(self, json_path, source_type):
        if source_type == 'Pixel':
            rm_len = len('___pixel.json')
        elif source_type == 'Vector':
            rm_len = len('___objects.json')

        image_path = str(json_path)[:-rm_len]
        img_width, img_height = Image.open(image_path).size
        return img_height, img_width

    def __make_image_info(self, id_, sa_meta_json):
        image_info = {
            'id': id_,
            'file_name': sa_meta_json['name'],
            'height': sa_meta_json['height'],
            'width': sa_meta_json['width'],
            'license': 1
        }

        return image_info

    def _prepare_single_image_commons_vector(self, id_, json_path):
        ImgCommons = namedtuple('ImgCommons', ['image_info', 'sa_ann_json'])

        sa_json = json.load(open(json_path))
        sa_ann_json = sa_json['instances']

        image_info = self.__make_image_info(id_, sa_json['metadata'])

        res = ImgCommons(image_info, sa_ann_json)

        return res

    def _prepare_single_image_commons(self, id_, json_path):
        res = None
        if self.project_type == 'Pixel':
            res = self._prepare_single_image_commons_pixel(id_, json_path)
        elif self.project_type == 'Vector':
            res = self._prepare_single_image_commons_vector(id_, json_path)
        return res

    def _create_sa_classes(self, json_path):
        json_data = json.load(open(json_path))
        classes_list = json_data["categories"]

        classes = []
        for data in classes_list:
            color = np.random.choice(range(256), size=3)
            hexcolor = "#%02x%02x%02x" % tuple(color)
            classes_dict = {
                'name': data["name"],
                'color': hexcolor,
                'attribute_groups': []
            }
            classes.append(classes_dict)

        return classes

    def to_sa_format(self):
        json_data = self.export_root / (self.dataset_name + ".json")
        sa_classes = self._create_sa_classes(json_data)
        (self.output_dir / 'classes').mkdir(parents=True, exist_ok=True)
        write_to_json(self.output_dir / 'classes' / 'classes.json', sa_classes)
        self.conversion_algorithm(json_data, self.output_dir)


class CocoPanopticConverterStrategy(CocoBaseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def _sa_to_coco_single(self, id_, json_path, id_generator, cat_id_map):

        image_commons = self._prepare_single_image_commons(id_, json_path)
        res = self.conversion_algorithm(image_commons, id_generator, cat_id_map)

        return res

    def sa_to_output_format(self):
        out_json = self._create_skeleton()
        out_json['categories'] = self._create_categories(
            self.export_root / 'classes_mapper.json'
        )

        cat_id_map = json.load(open(self.export_root / 'classes_mapper.json'))

        images = []
        annotations = []
        id_generator = self._make_id_generator()

        jsons_gen = self.export_root.glob('*pixel.json')
        jsons = list(jsons_gen)

        for id_, json_ in tqdm(enumerate(jsons, 1)):
            res = self._sa_to_coco_single(id_, json_, id_generator, cat_id_map)

            panoptic_mask = str(json_)[:-len('___pixel.json')] + '.png'

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
        write_to_json(
            self.output_dir / '{}.json'.format(self.dataset_name), out_json
        )
        self.set_num_converted(len(jsons))


class CocoObjectDetectionStrategy(CocoBaseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def _sa_to_coco_single(self, id_, json_path, id_generator, cat_id_map):

        image_commons = self._prepare_single_image_commons(id_, json_path)

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
            make_annotation, image_commons, id_generator, cat_id_map
        )
        return res

    def sa_to_output_format(self):
        out_json = self._create_skeleton()
        out_json['categories'] = self._create_categories(
            self.export_root / 'classes_mapper.json'
        )

        cat_id_map = json.load(open(self.export_root / 'classes_mapper.json'))

        jsons = self._load_sa_jsons()
        images = []
        annotations = []
        id_generator = self._make_id_generator()
        for id_, json_ in tqdm(enumerate(jsons)):
            try:
                res = self._sa_to_coco_single(
                    id_, json_, id_generator, cat_id_map
                )
            except Exception as e:
                raise
            images.append(res[0])
            if len(res[1]) < 1:
                self.increase_converted_count()
            for ann in res[1]:
                annotations.append(ann)
        out_json['annotations'] = annotations
        out_json['images'] = images

        write_to_json(
            self.output_dir / '{}.json'.format(self.dataset_name), out_json
        )
        print("NUMBER OF IMAGES FAILED TO CONVERT", self.failed_conversion_cnt)

        self.set_num_converted(len(jsons))


class CocoKeypointDetectionStrategy(CocoBaseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def __make_image_info(self, json_path, id_, source_type):
        if source_type == 'Pixel':
            rm_len = len('___pixel.json')
        elif source_type == 'Vector':
            rm_len = len('___objects.json')

        img_width, img_height = 0, 0
        json_data = json.load(open(json_path))
        for annot in json_data:
            if 'type' in annot and annot['type'] == 'meta':
                img_height = annot['height']
                img_width = annot['width']

        image_path = str(json_path)[:-rm_len]

        if img_width == 0 and img_height == 0:
            img_width, img_height = Image.open(image_path).size

        image_info = {
            'id': id_,
            'file_name': Path(image_path).name,
            'height': img_height,
            'width': img_width,
            'license': 1
        }

        return image_info

    def sa_to_output_format(self):
        out_json = self._create_skeleton()
        jsons = self._load_sa_jsons()

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
        write_to_json(
            self.output_dir / '{}.json'.format(self.dataset_name), out_json
        )
        self.set_num_converted(len(out_json['images']))
