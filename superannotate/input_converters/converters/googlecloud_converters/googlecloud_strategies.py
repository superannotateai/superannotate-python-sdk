import os
from pathlib import Path

from .googlecloud_converter import GoogleCloudConverter
from .googlecloud_to_sa_vector import googlecloud_object_detection_to_sa_vector


class GoogleCloudObjectDetectionStrategy(GoogleCloudConverter):
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
                    self.converion_algorithm = googlecloud_object_detection_to_sa_vector
                else:
                    raise NotImplementedError("Doesn't support yet")
            elif self.project_type == "Pixel":
                raise NotImplementedError("Doesn't support yet")

    def __str__(self):
        return '{} object'.format(self.name)

    def from_sa_format(self):
        pass

    def to_sa_format(self):
        path = Path(self.export_root).joinpath(self.dataset_name + '.csv')
        id_generator = self._make_id_generator()
        sa_jsons, sa_classes = self.converion_algorithm(path, id_generator)
        self.dump_output(sa_classes, sa_jsons)

    def _make_id_generator(self):
        cur_id = 0
        while True:
            cur_id += 1
            yield cur_id
