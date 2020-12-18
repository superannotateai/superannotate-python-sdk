from pathlib import Path

from .googlecloud_converter import GoogleCloudConverter
from .googlecloud_to_sa_vector import googlecloud_object_detection_to_sa_vector

from ....common import dump_output


class GoogleCloudObjectDetectionStrategy(GoogleCloudConverter):
    name = "ObjectDetection converter"

    def __init__(self, args):
        super().__init__(args)
        self.__setup_conversion_algorithm()

    def __setup_conversion_algorithm(self):
        if self.direction == "from":
            if self.project_type == "Vector":
                if self.task == "object_detection":
                    self.conversion_algorithm = googlecloud_object_detection_to_sa_vector

    def __str__(self):
        return '{} object'.format(self.name)

    def to_sa_format(self):
        path = Path(self.export_root).joinpath(self.dataset_name + '.csv')
        sa_jsons, sa_classes = self.conversion_algorithm(path)
        dump_output(self.output_dir, self.platform, sa_classes, sa_jsons)
