from .dataloop_converter import DataLoopConverter
from .dataloop_to_sa_vector import (
    dataloop_object_detection_to_sa_vector,
    dataloop_instance_segmentation_to_sa_vector, dataloop_to_sa
)

from ....common import dump_output


class DataLoopObjectDetectionStrategy(DataLoopConverter):
    name = "Object Detection converter"

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):
        if self.direction == "from":
            if self.project_type == "Vector":
                if self.task == "object_detection":
                    self.conversion_algorithm = dataloop_object_detection_to_sa_vector
                elif self.task == 'instance_segmentation':
                    self.conversion_algorithm = dataloop_instance_segmentation_to_sa_vector
                elif self.task == 'vector_annotation':
                    self.conversion_algorithm = dataloop_to_sa

    def __str__(self):
        return '{} object'.format(self.name)

    def to_sa_format(self):
        sa_jsons, sa_classes = self.conversion_algorithm(self.export_root)
        dump_output(self.output_dir, self.platform, sa_classes, sa_jsons)
