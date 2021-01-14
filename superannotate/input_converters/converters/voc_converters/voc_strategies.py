import numpy as np

from ..baseStrategy import baseStrategy

from ....common import write_to_json


class VocStrategy(baseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def to_sa_format(self):
        classes = self.conversion_algorithm(self.export_root, self.output_dir)
        sa_classes = self._create_classes(classes)
        (self.output_dir / 'classes').mkdir(exist_ok=True)
        write_to_json(self.output_dir / 'classes' / 'classes.json', sa_classes)

        if self.project_type == 'Pixel':
            all_files = self.output_dir.glob('*.png')
            for file in all_files:
                if '___save.png' not in str(file.name):
                    (self.output_dir / file.name).unlink()

    def _create_classes(self, instances):
        classes = {}
        for instance in instances:
            for class_, value in instance.items():
                if class_ not in classes:
                    classes[class_] = {}

                for attr in value:
                    if attr['groupName'] in classes[class_]:
                        classes[class_][attr['groupName']].append(attr['name'])
                    else:
                        classes[class_][attr['groupName']] = [attr['name']]

        sa_classes = []
        for class_ in classes:
            color = np.random.choice(range(256), size=3)
            hexcolor = "#%02x%02x%02x" % tuple(color)
            attribute_groups = []
            for attr_group, value in classes[class_].items():
                attributes = []
                for attr in set(value):
                    attributes.append({'name': attr})

                attribute_groups.append(
                    {
                        'name': attr_group,
                        'is_multiselect': 0,
                        'attributes': attributes
                    }
                )
            sa_class = {
                "name": class_,
                "color": hexcolor,
                "attribute_groups": attribute_groups
            }
            sa_classes.append(sa_class)
        return sa_classes
