import os
import json

from .dataloop_converter import DataLoopConverter
from .dataloop_to_sa_vector import dataloop_object_detection_to_sa_vector, dataloop_instance_segmentation_to_sa_vector, dataloop_to_sa


class DataLoopObjectDetectionStrategy(DataLoopConverter):
    name = "Object Detection converter"

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):
        if self.direction == "to":
            raise NotImplementedError("Doesn't support yet")
        else:
            if self.project_type == "Vector":
                if self.task == "object_detection":
                    self.conversion_algorithm = dataloop_object_detection_to_sa_vector
                elif self.task == 'instance_segmentation':
                    self.conversion_algorithm = dataloop_instance_segmentation_to_sa_vector
                elif self.task == 'vector_annotation':
                    self.conversion_algorithm = dataloop_to_sa
            elif self.project_type == "Pixel":
                raise NotImplementedError("Doesn't support yet")

    def __str__(self):
        return '{} object'.format(self.name)

    def from_sa_format(self):
        pass

    def to_sa_format(self):
        id_generator = self._make_id_generator()
        sa_jsons, classes_json = self.conversion_algorithm(
            self.export_root, id_generator
        )
        self.dump_output(classes_json, sa_jsons)

    def _make_id_generator(self):
        cur_id = 0
        while True:
            cur_id += 1
            yield cur_id
