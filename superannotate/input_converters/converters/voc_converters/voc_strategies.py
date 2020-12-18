import json
import os
import cv2

from .voc_converter import VocConverter
from .voc_to_sa_pixel import voc_instance_segmentation_to_sa_pixel
from .voc_to_sa_vector import voc_object_detection_to_sa_vector, voc_instance_segmentation_to_sa_vector

from ....common import dump_output


class VocObjectDetectionStrategy(VocConverter):
    name = "ObjectDetection converter"

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):
        if self.direction == "to":
            raise NotImplementedError("Doesn't support yet")
        else:
            if self.project_type == "Vector":
                if self.task == "object_detection":
                    self.conversion_algorithm = voc_object_detection_to_sa_vector
                elif self.task == "instance_segmentation":
                    self.conversion_algorithm = voc_instance_segmentation_to_sa_vector
            elif self.project_type == "Pixel":
                if self.task == "instance_segmentation":
                    self.conversion_algorithm = voc_instance_segmentation_to_sa_pixel

    def __str__(self):
        return '{} object'.format(self.name)

    def to_sa_format(self):
        sa_classes, sa_jsons, sa_masks = self.conversion_algorithm(
            self.export_root
        )
        dump_output(self.output_dir, self.platform, sa_classes, sa_jsons)

        if self.project_type == 'Pixel':
            all_files = self.output_dir.glob('*.png')
            for file in all_files:
                if '___save.png' not in str(file.name):
                    (self.output_dir / file.name).unlink()

            for sa_mask_name, sa_mask_value in sa_masks.items():
                sa_mask_value = sa_mask_value[:, :, ::-1]
                cv2.imwrite(str(self.output_dir / sa_mask_name), sa_mask_value)
