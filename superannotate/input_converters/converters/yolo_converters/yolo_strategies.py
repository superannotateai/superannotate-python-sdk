import json

from .yolo_converter import YOLOConverter
from .yolo_to_sa_vector import yolo_object_detection_to_sa_vector


class YoloObjectDetectionStrategy(YOLOConverter):
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
                    self.converion_algorithm = yolo_object_detection_to_sa_vector
            elif self.project_type == "Pixel":
                raise NotImplementedError("Doesn't support yet")

    def __str__(self):
        return '{} object'.format(self.name)

    def from_sa_format(self):
        pass

    def to_sa_format(self):
        sa_jsons, sa_classes = self.converion_algorithm(self.export_root)
        self.dump_output(sa_classes, sa_jsons)
