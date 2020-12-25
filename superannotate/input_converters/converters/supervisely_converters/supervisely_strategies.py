import json

from ..baseStrategy import baseStrategy

from ....common import write_to_json


class SuperviselyStrategy(baseStrategy):
    def __init__(self, args):
        super().__init__(args)

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
                json_files, classes_id_map, meta_json, self.output_dir
            )
        elif self.conversion_algorithm.__name__ == 'supervisely_instance_segmentation_to_sa_pixel':
            sa_jsons = self.conversion_algorithm(
                json_files, classes_id_map, self.output_dir
            )
        else:
            sa_jsons = self.conversion_algorithm(
                json_files, classes_id_map, self.task, self.output_dir
            )
        (self.output_dir / 'classes').mkdir(exist_ok=True)
        write_to_json(self.output_dir / 'classes' / 'classes.json', sa_classes)

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
