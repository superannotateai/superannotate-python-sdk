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

    def _create_classes(self, classes):
        sa_classes = []
        for class_ in set(classes):
            color = np.random.choice(range(256), size=3)
            hexcolor = "#%02x%02x%02x" % tuple(color)
            sa_class = {
                "name": class_,
                "color": hexcolor,
                "attribute_groups": []
            }
            sa_classes.append(sa_class)
        return sa_classes
