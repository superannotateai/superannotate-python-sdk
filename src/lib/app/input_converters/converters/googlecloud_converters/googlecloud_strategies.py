from pathlib import Path
import numpy as np

from ..baseStrategy import baseStrategy

from ....common import write_to_json


class GoogleCloudStrategy(baseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def to_sa_format(self):
        path = Path(self.export_root).joinpath(self.dataset_name + '.csv')
        classes = self.conversion_algorithm(path, self.output_dir)
        sa_classes = self._create_classes(classes)
        (self.output_dir / 'classes').mkdir(exist_ok=True)
        write_to_json(self.output_dir / 'classes' / 'classes.json', sa_classes)

    def _create_classes(self, classes):
        classes_loader = []
        for class_ in set(classes):
            color = np.random.choice(range(256), size=3)
            hexcolor = "#%02x%02x%02x" % tuple(color)
            sa_classes = {
                'name': class_,
                'color': hexcolor,
                'attribute_groups': []
            }
            classes_loader.append(sa_classes)
        return classes_loader
