import numpy as np
from pathlib import Path

from ..baseStrategy import baseStrategy

from ....common import write_to_json


class VGGStrategy(baseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def to_sa_format(self):
        json_data = self.get_file_list()
        classes = self.conversion_algorithm(
            json_data, self.task, self.output_dir
        )
        sa_classes = self._create_classes(classes)
        (self.output_dir / 'classes').mkdir(exist_ok=True)
        write_to_json(self.output_dir / 'classes' / 'classes.json', sa_classes)

    def get_file_list(self):
        json_file_list = []
        path = Path(self.export_root)
        if self.dataset_name != '':
            json_file_list.append(path.joinpath(self.dataset_name + '.json'))
        else:
            file_generator = path.glob('*.json')
            for gen in file_generator:
                json_file_list.append(gen)

        return json_file_list

    def _create_classes(self, class_id_map):
        sa_classes = []
        for key in class_id_map.keys():
            color = np.random.choice(range(256), size=3)
            hexcolor = "#%02x%02x%02x" % tuple(color)
            dd = {'name': key, 'color': hexcolor, 'attribute_groups': []}
            for attributes, value in class_id_map[key]['attribute_groups'
                                                      ].items():
                attr_group = {
                    'name': attributes,
                    'is_multiselect': value['is_multiselect'],
                    'attributes': []
                }
                for attribute in value['attributes']:
                    attr = {'name': attribute, 'groupName': attributes}
                    attr_group['attributes'].append(attr.copy())
                dd['attribute_groups'].append(attr_group.copy())
            sa_classes.append(dd)
        return sa_classes
