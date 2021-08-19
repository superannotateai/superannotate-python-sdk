import json

from ....common import write_to_json
from ..baseStrategy import baseStrategy


class LabelBoxStrategy(baseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def to_sa_format(self):
        json_data = json.load(open(self.export_root / (self.dataset_name + ".json")))
        if self.project_type == "Vector":
            classes = self.conversion_algorithm(json_data, self.output_dir, self.task)
        elif self.project_type == "Pixel":
            classes = self.conversion_algorithm(
                json_data, self.output_dir, self.export_root
            )
        sa_classes = self._create_classes(classes)
        (self.output_dir / "classes").mkdir(exist_ok=True)
        write_to_json(self.output_dir / "classes" / "classes.json", sa_classes)

    def _create_classes(self, classes):
        sa_classes_loader = []
        for key, value in classes.items():
            sa_classes = {"name": key, "color": value["color"], "attribute_groups": []}
            attribute_groups = []
            for attr_group_key, attr_group in value["attribute_groups"].items():
                attr_loader = {
                    "name": attr_group_key,
                    "is_multiselect": attr_group["is_multiselect"],
                    "attributes": [],
                }
                for attr in attr_group["attributes"]:
                    attr_loader["attributes"].append({"name": attr})
                if attr_loader:
                    attribute_groups.append(attr_loader)
            sa_classes["attribute_groups"] = attribute_groups

            sa_classes_loader.append(sa_classes)

        return sa_classes_loader
