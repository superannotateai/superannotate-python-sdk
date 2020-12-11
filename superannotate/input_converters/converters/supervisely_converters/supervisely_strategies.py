import json

from .supervisely_converter import SuperviselyConverter
from .supervisely_to_sa_vector import (
    supervisely_to_sa, supervisely_instance_segmentation_to_sa_vector,
    supervisely_object_detection_to_sa_vector,
    supervisely_keypoint_detection_to_sa_vector
)
from .supervisely_to_sa_pixel import supervisely_instance_segmentation_to_sa_pixel

from ....common import dump_output


class SuperviselyObjectDetectionStrategy(SuperviselyConverter):
    name = "ObjectDetection converter"

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):
        if self.direction == "from":
            if self.project_type == "Vector":
                if self.task == 'vector_annotation':
                    self.conversion_algorithm = supervisely_to_sa
                elif self.task == 'object_detection':
                    self.conversion_algorithm = supervisely_object_detection_to_sa_vector
                elif self.task == 'instance_segmentation':
                    self.conversion_algorithm = supervisely_instance_segmentation_to_sa_vector
                elif self.task == 'keypoint_detection':
                    self.conversion_algorithm = supervisely_keypoint_detection_to_sa_vector
            elif self.project_type == "Pixel":
                if self.task == 'instance_segmentation':
                    self.conversion_algorithm = supervisely_instance_segmentation_to_sa_pixel

    def __str__(self):
        return '{} object'.format(self.name)

    def to_sa_format(self):
        sa_classes, classes_id_map = self._create_sa_classes()
        json_files = []
        if self.dataset_name != '':
            json_files.append(
                self.export_root / 'ds' / 'ann' / (self.dataset_name + '.json')
            )
        else:
            files_gen = (self.export_root / 'ds' / 'ann').glob('*')
            json_files = list(files_gen)

        if self.conversion_algorithm.__name__ == 'supervisely_keypoint_detection_to_sa_vector':
            meta_json = json.load(open(self.export_root / 'meta.json'))
            sa_jsons = self.conversion_algorithm(
                json_files, classes_id_map, meta_json
            )
        elif self.conversion_algorithm.__name__ == 'supervisely_instance_segmentation_to_sa_pixel':
            sa_jsons = self.conversion_algorithm(
                json_files, classes_id_map, self.output_dir
            )
        else:
            sa_jsons = self.conversion_algorithm(json_files, classes_id_map)
        dump_output(self.output_dir, self.platform, sa_classes, sa_jsons)

    def _create_sa_classes(self):
        classes_json = json.load(open(self.export_root / 'meta.json'))

        attributes = []
        for tag in classes_json['tags']:
            attributes.append({'name': tag['name']})

        classes_id_map = {}
        classes_loader = []
        for class_ in classes_json['classes']:
            group_name = 'converted_attributs'
            classes_id_map[class_['title']] = {
                'attr_group': {
                    'group_name': group_name,
                    'attributes': []
                }
            }
            for attribute in attributes:
                attribute['groupName'] = group_name
                classes_id_map[class_['title']
                              ]['attr_group']['attributes'].append(
                                  {'name': attribute['name']}
                              )

            if not attributes:
                attribute_groups = []
            else:
                attribute_groups = [
                    {
                        'name': group_name,
                        'is_multiselect': 1,
                        'attributes': attributes
                    }
                ]

            attr_group = {
                'name': class_['title'],
                'color': class_['color'],
                'attribute_groups': attribute_groups
            }
            classes_loader.append(attr_group)
        return classes_loader, classes_id_map
