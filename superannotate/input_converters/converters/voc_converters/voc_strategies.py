import json
import os
import cv2

from .voc_converter import VocConverter
from .voc_to_sa_pixel import voc_instance_segmentation_to_sa_pixel
from .voc_to_sa_vector import voc_object_detection_to_sa_vector, voc_instance_segmentation_to_sa_vector


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
                if self.task == "object_detection":
                    raise NotImplementedError("Doesn't support yet")
                elif self.task == "instance_segmentation":
                    self.conversion_algorithm = voc_instance_segmentation_to_sa_pixel

    def __str__(self):
        return '{} object'.format(self.name)

    def from_sa_format(self):
        pass

    def to_sa_format(self):
        sa_classes, sa_jsons, sa_masks = self.conversion_algorithm(
            self.export_root
        )
        self.dump_output(sa_classes, sa_jsons)

        if self.project_type == 'Pixel':
            all_files = os.listdir(self.output_dir)
            for file in all_files:
                if os.path.splitext(file)[1] == '.png':
                    os.remove(os.path.join(self.output_dir, file))

            for sa_mask_name, sa_mask_value in sa_masks.items():
                sa_mask_value = sa_mask_value[:, :, ::-1]
                cv2.imwrite(
                    os.path.join(self.output_dir, sa_mask_name), sa_mask_value
                )
