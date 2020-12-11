import cv2
import os
from glob import glob

from .sagemaker_converter import SageMakerConverter
from .sagemaker_to_sa_vector import sagemaker_object_detection_to_sa_vector
from .sagemaker_to_sa_pixel import sagemaker_instance_segmentation_to_sa_pixel

from ....common import dump_output


class SageMakerObjectDetectionStrategy(SageMakerConverter):
    name = "ObjectDetection converter"

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):
        if self.direction == "from":
            if self.project_type == "Vector":
                if self.task == "object_detection":
                    self.conversion_algorithm = sagemaker_object_detection_to_sa_vector
            elif self.project_type == "Pixel":
                if self.task == "instance_segmentation":
                    self.conversion_algorithm = sagemaker_instance_segmentation_to_sa_pixel

    def __str__(self):
        return '{} object'.format(self.name)

    def to_sa_format(self):
        if self.conversion_algorithm.__name__ == 'sagemaker_object_detection_to_sa_vector':
            sa_jsons, sa_classes, sa_masks = self.conversion_algorithm(
                self.export_root, self.dataset_name
            )
        else:
            sa_jsons, sa_classes, sa_masks = self.conversion_algorithm(
                self.export_root
            )

        old_masks = self.output_dir.glob('*.png')
        for mask in old_masks:
            mask.unlink()
        if self.project_type == 'Pixel':
            for name, mask in sa_masks.items():
                cv2.imwrite(str(self.output_dir / name), mask)

        dump_output(self.output_dir, self.platform, sa_classes, sa_jsons)
