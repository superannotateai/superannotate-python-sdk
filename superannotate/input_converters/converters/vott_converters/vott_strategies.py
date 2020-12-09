import json

from .vott_converter import VoTTConverter
from .vott_to_sa_vector import vott_object_detection_to_sa_vector, vott_instance_segmentation_to_sa_vector, vott_to_sa

from ....common import dump_output


class VoTTObjectDetectionStrategy(VoTTConverter):
    name = "ObjectDetection converter"

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):
        if self.direction == "from":
            if self.project_type == "Vector":
                if self.task == "object_detection":
                    self.conversion_algorithm = vott_object_detection_to_sa_vector
                elif self.task == 'instance_segmentation':
                    self.conversion_algorithm = vott_instance_segmentation_to_sa_vector
                elif self.task == 'vector_annotation':
                    self.conversion_algorithm = vott_to_sa

    def __str__(self):
        return '{} object'.format(self.name)

    def to_sa_format(self):
        json_data = self.get_file_list()
        sa_jsons, sa_classes = self.conversion_algorithm(json_data)
        dump_output(self.output_dir, self.platform, sa_classes, sa_jsons)
