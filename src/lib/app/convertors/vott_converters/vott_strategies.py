from pathlib import Path

import numpy as np

from ....common import write_to_json
from ..baseStrategy import baseStrategy


class VoTTStrategy(baseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def to_sa_format(self):
        json_data = self.get_file_list()
        classes = self.conversion_algorithm(json_data, self.task, self.output_dir)
        sa_classes = self._create_classes(classes)
        (self.output_dir / "classes").mkdir(exist_ok=True)
        write_to_json(self.output_dir / "classes" / "classes.json", sa_classes)

    def get_file_list(self):
        json_file_list = []
        path = Path(self.export_root)
        if self.dataset_name != "":
            json_file_list.append(path.joinpath(self.dataset_name + ".json"))
        else:
            file_generator = path.glob("*.json")
            for gen in file_generator:
                json_file_list.append(gen)

        return json_file_list

    def _create_classes(self, classes_map):
        classes_loader = []
        for key in classes_map:
            color = np.random.choice(range(256), size=3)
            hexcolor = "#%02x%02x%02x" % tuple(color)
            sa_classes = {"name": key, "color": hexcolor, "attribute_groups": []}
            classes_loader.append(sa_classes)
        return classes_loader
