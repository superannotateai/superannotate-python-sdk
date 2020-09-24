import os
import json

from .dataloop_converter import DataLoopConverter
from .dataloop_to_sa_vector import dataloop_object_detection_to_sa_vector, dataloop_instance_segmentation_to_sa_vector


class DataLoopObjectDetectionStrategy(DataLoopConverter):
    name = "Object Detection converter"

    def __init__(
        self, dataset_name, export_root, project_type, output_dir, task,
        direction
    ):
        self.direction = direction
        super().__init__(
            dataset_name, export_root, project_type, output_dir, task
        )

        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):
        if self.direction == "to":
            raise NotImplementedError("Doesn't support yet")
        else:
            if self.project_type == "Vector":
                if self.task == "object_detection":
                    self.converion_algorithm = dataloop_object_detection_to_sa_vector
                elif self.task == 'instance_segmentation':
                    self.converion_algorithm = dataloop_instance_segmentation_to_sa_vector
            elif self.project_type == "Pixel":
                raise NotImplementedError("Doesn't support yet")

    def __str__(self):
        return '{} object'.format(self.name)

    def from_sa_format(self):
        pass

    def to_sa_format(self):
        json_data = json.load(
            open(os.path.join(self.export_root, self.dataset_name + '.json'))
        )
        self.converion_algorithm(json_data, self.output_dir)
