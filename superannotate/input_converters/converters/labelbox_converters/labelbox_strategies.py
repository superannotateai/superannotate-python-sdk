import os
import json

from .labelbox_converter import LabelBoxConverter
from .labelbox_to_sa_vector import labelbox_object_detection_to_sa_vector, labelbox_instance_segmentation_to_sa_vector, labelbox_to_sa


class LabelBoxObjectDetectionStrategy(LabelBoxConverter):
    name = "ObjectDetection converter"

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
                    self.converion_algorithm = labelbox_object_detection_to_sa_vector
                elif self.task == 'instace_segmentation':
                    self.converion_algorithm = labelbox_instance_segmentation_to_sa_vector
                elif self.task == 'vector_annotation':
                    self.converion_algorithm = labelbox_to_sa
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
        id_generator = self._make_id_generator()
        self.converion_algorithm(json_data, self.output_dir, id_generator)

    def _make_id_generator(self):
        cur_id = 0
        while True:
            cur_id += 1
            yield cur_id
