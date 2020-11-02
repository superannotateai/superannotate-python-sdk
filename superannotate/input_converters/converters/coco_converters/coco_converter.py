"""
"""
from datetime import datetime
from collections import namedtuple
import json
import glob
import os
import numpy as np
from panopticapi.utils import id2rgb
from PIL import Image

import tqdm
import time
from pathlib import Path


class CoCoConverter(object):
    def __init__(self, args):
        self.project_type = args.project_type
        self.dataset_name = args.dataset_name
        self.export_root = args.export_root
        self.output_dir = args.output_dir
        self.task = args.task
        self.direction = args.direction
        self.platform = args.platform

        self.failed_conversion_cnt = 0

    def _create_single_category(self, item):
        category = {
            'id': item.id,
            'name': item.class_name,
            'supercategory': item.class_name,
            'isthing': 1,
            'color': id2rgb(item.id)
        }
        return category

    def set_output_dir(self, output_dir_):
        self.output_dir = output_dir_

    def set_export_root(self, export_dir):
        self.export_root = export_dir

    def set_dataset_name(self, dname):
        self.dataset_name = dname

    def increase_converted_count(self):
        self.failed_conversion_cnt = self.failed_conversion_cnt + 1

    def set_num_converted(self, num_converted_):
        self.num_converted = num_converted_

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

    def _make_id_generator(self):
        cur_id = 0
        while True:
            cur_id += 1
            yield cur_id

    def _create_skeleton(self):
        out_json = {
            'info':
                {
                    'description': 'This is dataset.'.format(self.dataset_name),
                    'url': 'https://superannotate.ai',
                    'version': '1.0',
                    'year': 2020,
                    'contributor': 'Superannotate AI',
                    'date_created': datetime.now().strftime("%d/%m/%Y")
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
        jsons = []
        if self.project_type == 'Pixel':
            jsons = glob.glob(os.path.join(self.export_root, '*pixel.json'))
        elif self.project_type == 'Vector':
            jsons = glob.glob(os.path.join(self.export_root, '*objects.json'))

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
        image_path = json_path[:-rm_len
                              ] + '___lores.jpg'  # maybe not use low res files?

        sa_ann_json = json.load(open(os.path.join(json_path)))
        sa_bluemask_path = os.path.join(json_path[:-rm_len] + '___save.png')

        image_info = self.__make_image_info(json_path, id_, self.project_type)

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

    def _prepare_single_image_commons_vector(self, id_, json_path):
        ImgCommons = namedtuple('ImgCommons', ['image_info', 'sa_ann_json'])

        image_info = self.__make_image_info(json_path, id_, self.project_type)
        sa_ann_json = json.load(open(json_path))

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

        colors = self._generate_colors(len(classes_list))
        classes = []
        for c, data in enumerate(classes_list):
            classes_dict = {
                'name': data["name"],
                'id': data["id"],
                'color': colors[c],
                'attribute_groups': []
            }
            classes.append(classes_dict)

        return classes

    def _generate_colors(self, number):
        colors = []
        for i in range(number):
            color = np.random.choice(range(256), size=3)
            hexcolor = "#%02x%02x%02x" % tuple(color)
            colors.append(hexcolor)
        return colors

    def save_desktop_format(self, classes, files_dict):
        path = Path(self.output_dir)
        cat_id_map = {}
        new_classes = []
        for idx, class_ in enumerate(classes):
            cat_id_map[class_['id']] = idx + 2
            class_['id'] = idx + 2
            new_classes.append(class_)
        with open(path.joinpath('classes.json'), 'w') as fw:
            json.dump(new_classes, fw)

        meta = {
            "type": "meta",
            "name": "lastAction",
            "timestamp": int(round(time.time() * 1000))
        }
        new_json = {}
        for file_name, json_data in files_dict.items():
            file_name = file_name.replace('___objects.json', '')
            new_json_data = []
            for js_data in json_data:
                if 'classId' in js_data:
                    new_js_data = js_data.copy()
                    new_js_data['classId'] = cat_id_map[js_data['classId']]
                    new_json_data.append(new_js_data)
            new_json_data.append(meta)
            new_json[file_name] = new_json_data
        with open(path.joinpath('annotations.json'), 'w') as fw:
            json.dump(new_json, fw)

    def save_web_format(self, classes, files_dict):
        path = Path(self.output_dir)
        for key, value in files_dict.items():
            with open(path.joinpath(key), 'w') as fw:
                json.dump(value, fw, indent=2)

        with open(path.joinpath('classes', 'classes.json'), 'w') as fw:
            json.dump(classes, fw)

    def dump_output(self, classes, files_dict):
        if self.platform == 'Web':
            self.save_web_format(classes, files_dict)
        else:
            self.save_desktop_format(classes, files_dict)
