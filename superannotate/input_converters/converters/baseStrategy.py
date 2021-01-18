'''
'''
import logging

from .coco_converters.coco_to_sa_pixel import (
    coco_instance_segmentation_to_sa_pixel,
    coco_panoptic_segmentation_to_sa_pixel
)
from .coco_converters.coco_to_sa_vector import (
    coco_instance_segmentation_to_sa_vector,
    coco_keypoint_detection_to_sa_vector, coco_object_detection_to_sa_vector
)
from .coco_converters.sa_pixel_to_coco import (
    sa_pixel_to_coco_instance_segmentation,
    sa_pixel_to_coco_panoptic_segmentation
)
from .coco_converters.sa_vector_to_coco import (
    sa_vector_to_coco_instance_segmentation,
    sa_vector_to_coco_keypoint_detection, sa_vector_to_coco_object_detection
)

from .voc_converters.voc_to_sa_pixel import voc_instance_segmentation_to_sa_pixel
from .voc_converters.voc_to_sa_vector import (
    voc_object_detection_to_sa_vector, voc_instance_segmentation_to_sa_vector
)

from .dataloop_converters.dataloop_to_sa_vector import dataloop_to_sa

from .labelbox_converters.labelbox_to_sa_vector import labelbox_to_sa
from .labelbox_converters.labelbox_to_sa_pixel import labelbox_instance_segmentation_to_sa_pixel

from .sagemaker_converters.sagemaker_to_sa_vector import sagemaker_object_detection_to_sa_vector
from .sagemaker_converters.sagemaker_to_sa_pixel import sagemaker_instance_segmentation_to_sa_pixel

from .supervisely_converters.supervisely_to_sa_vector import (
    supervisely_to_sa, supervisely_keypoint_detection_to_sa_vector
)

from .supervisely_converters.supervisely_to_sa_pixel import (
    supervisely_instance_segmentation_to_sa_pixel
)

from .vgg_converters.vgg_to_sa_vector import vgg_to_sa

from .vott_converters.vott_to_sa_vector import vott_to_sa

from .googlecloud_converters.googlecloud_to_sa_vector import googlecloud_to_sa_vector

from .yolo_converters.yolo_to_sa_vector import yolo_object_detection_to_sa_vector

logger = logging.getLogger("superannotate-python-sdk")

CONVERSION_ALGORITHMS = {
    'from':
        {
            'COCO':
                {
                    'Vector':
                        {
                            'keypoint_detection':
                                coco_keypoint_detection_to_sa_vector,
                            'instance_segmentation':
                                coco_instance_segmentation_to_sa_vector,
                            'object_detection':
                                coco_object_detection_to_sa_vector
                        },
                    'Pixel':
                        {
                            'panoptic_segmentation':
                                coco_panoptic_segmentation_to_sa_pixel,
                            'instance_segmentation':
                                coco_instance_segmentation_to_sa_pixel
                        }
                },
            'VOC':
                {
                    'Vector':
                        {
                            'object_detection':
                                voc_object_detection_to_sa_vector,
                            'instance_segmentation':
                                voc_instance_segmentation_to_sa_vector
                        },
                    'Pixel':
                        {
                            'instance_segmentation':
                                voc_instance_segmentation_to_sa_pixel
                        }
                },
            'LabelBox':
                {
                    'Vector':
                        {
                            'object_detection': labelbox_to_sa,
                            'instance_segmentation': labelbox_to_sa,
                            'vector_annotation': labelbox_to_sa
                        },
                    'Pixel':
                        {
                            'instance_segmentation':
                                labelbox_instance_segmentation_to_sa_pixel
                        }
                },
            'DataLoop':
                {
                    'Vector':
                        {
                            'object_detection': dataloop_to_sa,
                            'instance_segmentation': dataloop_to_sa,
                            'vector_annotation': dataloop_to_sa
                        },
                    'Pixel': {}
                },
            'Supervisely':
                {
                    'Vector':
                        {
                            'vector_annotation':
                                supervisely_to_sa,
                            'instance_segmentation':
                                supervisely_to_sa,
                            'object_detection':
                                supervisely_to_sa,
                            'keypoint_detection':
                                supervisely_keypoint_detection_to_sa_vector
                        },
                    'Pixel':
                        {
                            'instance_segmentation':
                                supervisely_instance_segmentation_to_sa_pixel
                        }
                },
            'VoTT':
                {
                    'Vector':
                        {
                            'instance_segmentation': vott_to_sa,
                            'object_detection': vott_to_sa,
                            'vector_annotation': vott_to_sa
                        },
                    'Pixel': {}
                },
            'SageMaker':
                {
                    'Vector':
                        {
                            'object_detection':
                                sagemaker_object_detection_to_sa_vector
                        },
                    'Pixel':
                        {
                            'instance_segmentation':
                                sagemaker_instance_segmentation_to_sa_pixel
                        }
                },
            'VGG':
                {
                    'Vector':
                        {
                            'object_detection': vgg_to_sa,
                            'instance_segmentation': vgg_to_sa,
                            'vector_annotation': vgg_to_sa
                        },
                    'Pixel': {}
                },
            'GoogleCloud':
                {
                    'Vector': {
                        'object_detection': googlecloud_to_sa_vector
                    },
                    'Pixel': {}
                },
            'YOLO':
                {
                    'Vector':
                        {
                            'object_detection':
                                yolo_object_detection_to_sa_vector
                        },
                    'Pixel': {}
                }
        },
    'to':
        {
            'COCO':
                {
                    'Vector':
                        {
                            'instance_segmentation':
                                sa_vector_to_coco_instance_segmentation,
                            'object_detection':
                                sa_vector_to_coco_object_detection,
                            'keypoint_detection':
                                sa_vector_to_coco_keypoint_detection
                        },
                    'Pixel':
                        {
                            'panoptic_segmentation':
                                sa_pixel_to_coco_panoptic_segmentation,
                            'instance_segmentation':
                                sa_pixel_to_coco_instance_segmentation
                        }
                },
        }
}


class baseStrategy():
    def __init__(self, args):
        if args.dataset_format not in ('COCO', 'VOC'):
            logger.warning(
                "Beta feature. %s to SuperAnnotate annotation format converter is in BETA state."
                % args.dataset_format
            )
        self.project_type = args.project_type
        self.dataset_name = args.dataset_name
        self.export_root = args.export_root
        self.output_dir = args.output_dir
        self.task = args.task
        self.direction = args.direction
        self.conversion_algorithm = CONVERSION_ALGORITHMS[self.direction][
            args.dataset_format][self.project_type][self.task]

        self.name = "%s %s converter" % (args.dataset_format, self.task)

        self.failed_conversion_cnt = 0

    def __str__(self):
        return '%s object' % (self.name)

    def set_output_dir(self, output_dir_):
        self.output_dir = output_dir_

    def set_export_root(self, export_dir):
        self.export_root = export_dir

    def set_dataset_name(self, dname):
        self.dataset_name = dname

    def increase_converted_count(self):
        self.failed_conversion_cnt = self.failed_conversion_cnt + 1

    def set_num_converted(self, num_converted_):
        self.num_converted = num_converted_
