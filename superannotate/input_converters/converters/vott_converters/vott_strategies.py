import json

from .vott_converter import VoTTConverter
from .vott_to_sa_vector import vott_object_detection_to_sa_vector, vott_instance_segmentation_to_sa_vector, vott_to_sa


class VoTTObjectDetectionStrategy(VoTTConverter):
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
                    self.converion_algorithm = vott_object_detection_to_sa_vector
                elif self.task == 'instace_segmentation':
                    self.converion_algorithm = vott_instance_segmentation_to_sa_vector
                elif self.task == 'vector_annotation':
                    self.converion_algorithm = vott_to_sa
            elif self.project_type == "Pixel":
                raise NotImplementedError("Doesn't support yet")

    def __str__(self):
        return '{} object'.format(self.name)

    def from_sa_format(self):
        pass

    def to_sa_format(self):
        json_data = self.get_file_list()
        id_generator = self._make_id_generator()
        sa_jsons, sa_classes = self.converion_algorithm(json_data, id_generator)
        self.dump_output(sa_classes, sa_jsons)

    def _make_id_generator(self):
        cur_id = 0
        while True:
            cur_id += 1
            yield cur_id
