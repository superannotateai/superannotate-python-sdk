"""
"""
import numpy as np

from ....common import write_to_json
from ..baseStrategy import baseStrategy


class DataLoopStrategy(baseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def to_sa_format(self):
        classes = self.conversion_algorithm(
            self.export_root, self.task, self.output_dir
        )
        sa_classes = self._create_sa_classes(classes)
        (self.output_dir / "classes").mkdir(exist_ok=True)
        write_to_json(self.output_dir / "classes" / "classes.json", sa_classes)

    def _create_sa_classes(self, classes):
        sa_classes_loader = []
        for key, value in classes.items():
            color = np.random.choice(range(256), size=3)
            hexcolor = "#%02x%02x%02x" % tuple(color)
            sa_classes = {"name": key, "color": hexcolor, "attribute_groups": []}
            attribute_groups = []
            for attr_group_key, attr_group in value["attribute_group"].items():
                attr_loader = {
                    "name": attr_group_key,
                    "is_multiselect": attr_group["is_multiselect"],
                    "attributes": [],
                }
                for attr in set(attr_group["attributes"]):
                    attr_loader["attributes"].append({"name": attr})
                if attr_loader:
                    attribute_groups.append(attr_loader)

            sa_classes["attribute_groups"] = attribute_groups

            sa_classes_loader.append(sa_classes)
        return sa_classes_loader
