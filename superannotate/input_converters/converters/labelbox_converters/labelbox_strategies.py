import json
import cv2

from .labelbox_to_sa_vector import labelbox_to_sa
from .labelbox_to_sa_pixel import labelbox_instance_segmentation_to_sa_pixel

from ..baseStrategy import baseStrategy

from ....common import dump_output


class LabelBoxStrategy(baseStrategy):
    name = "LabelBox converter"

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):
        if self.direction == "from":
            if self.project_type == "Vector":
                self.conversion_algorithm = labelbox_to_sa
            else:
                if self.task == 'instance_segmentation':
                    self.conversion_algorithm = labelbox_instance_segmentation_to_sa_pixel

    def __str__(self):
        return '{} object'.format(self.name)

    def to_sa_format(self):
        json_data = json.load(
            open(self.export_root / (self.dataset_name + '.json'))
        )
        sa_jsons, sa_classes, sa_masks = self.conversion_algorithm(
            json_data, self.task
        )
        dump_output(self.output_dir, self.platform, sa_classes, sa_jsons)

        if self.project_type == 'Pixel':
            for name, mask in sa_masks.items():
                cv2.imwrite(str(self.output_dir / name), mask)
