import json
from pathlib import Path

from .vott_to_sa_vector import (
    vott_object_detection_to_sa_vector, vott_instance_segmentation_to_sa_vector,
    vott_to_sa
)

from ..baseStrategy import baseStrategy
from ....common import dump_output


class VoTTObjectDetectionStrategy(baseStrategy):
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

    def get_file_list(self):
        json_file_list = []
        path = Path(self.export_root)
        if self.dataset_name != '':
            json_file_list.append(path.joinpath(self.dataset_name + '.json'))
        else:
            file_generator = path.glob('*.json')
            for gen in file_generator:
                json_file_list.append(gen)

        return json_file_list
