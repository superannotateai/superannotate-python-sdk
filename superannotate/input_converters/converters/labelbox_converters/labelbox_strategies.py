import json

from .labelbox_converter import LabelBoxConverter
from .labelbox_to_sa_vector import (
    labelbox_object_detection_to_sa_vector,
    labelbox_instance_segmentation_to_sa_vector, labelbox_to_sa
)


class LabelBoxObjectDetectionStrategy(LabelBoxConverter):
    name = "ObjectDetection converter"

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):
        if self.direction == "from":
            if self.project_type == "Vector":
                if self.task == "object_detection":
                    self.conversion_algorithm = labelbox_object_detection_to_sa_vector
                elif self.task == 'instance_segmentation':
                    self.conversion_algorithm = labelbox_instance_segmentation_to_sa_vector
                elif self.task == 'vector_annotation':
                    self.conversion_algorithm = labelbox_to_sa

    def __str__(self):
        return '{} object'.format(self.name)

    def to_sa_format(self):
        json_data = json.load(
            open(self.export_root / (self.dataset_name + '.json'))
        )
        sa_jsons, sa_classes = self.conversion_algorithm(json_data)
        self.dump_output(sa_classes, sa_jsons)
