import numpy as np

from ....common import write_to_json
from ..baseStrategy import baseStrategy


class SageMakerStrategy(baseStrategy):
    def __init__(self, args):
        super().__init__(args)

    def to_sa_format(self):
        if (
            self.conversion_algorithm.__name__
            == "sagemaker_object_detection_to_sa_vector"
        ):
            classes = self.conversion_algorithm(
                self.export_root, self.dataset_name, self.output_dir
            )
        else:
            classes = self.conversion_algorithm(self.export_root, self.output_dir)
        sa_classes = self._create_classes(classes)
        (self.output_dir / "classes").mkdir(exist_ok=True)
        write_to_json(self.output_dir / "classes" / "classes.json", sa_classes)

        old_masks = self.output_dir.glob("*.png")
        for mask in old_masks:
            if "___save.png" not in str(mask):
                mask.unlink()

    def _create_classes(self, classes_map):
        classes_loader = []
        for _, value in classes_map.items():
            color = np.random.choice(range(256), size=3)
            hexcolor = "#%02x%02x%02x" % tuple(color)
            sa_classes = {"name": value, "color": hexcolor, "attribute_groups": []}
            classes_loader.append(sa_classes)
        return classes_loader
