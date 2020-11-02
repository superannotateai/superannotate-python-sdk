import json
import cv2
import os
from glob import glob

from .sagemaker_converter import SageMakerConverter
from .sagemaker_to_sa_vector import sagemaker_object_detection_to_sa_vector
from .sagemaker_to_sa_pixel import sagemaker_instance_segmentation_to_sa_pixel


class SageMakerObjectDetectionStrategy(SageMakerConverter):
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
                    self.conversion_algorithm = sagemaker_object_detection_to_sa_vector
            elif self.project_type == "Pixel":
                if self.task == "instance_segmentation":
                    self.conversion_algorithm = sagemaker_instance_segmentation_to_sa_pixel

    def __str__(self):
        return '{} object'.format(self.name)

    def from_sa_format(self):
        pass

    def to_sa_format(self):
        sa_jsons, sa_classes, sa_masks = self.conversion_algorithm(
            self.export_root, self.dataset_name
        )
        old_masks = glob(os.path.join(self.output_dir, '*.png'))
        for mask in old_masks:
            os.remove(mask)
        if self.project_type == 'Pixel':
            for name, mask in sa_masks.items():
                cv2.imwrite(os.path.join(self.output_dir, name), mask)

        self.dump_output(sa_classes, sa_jsons)
