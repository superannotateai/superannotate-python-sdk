"""
Main module for input converters
"""
import sys
from argparse import Namespace
from pathlib import Path

from .import_to_sa_conversions import import_to_sa
from .export_from_sa_conversions import export_from_sa
from .sa_conversion import sa_conversion
from ..exceptions import SABaseException

AVAILABLE_ANNOTATION_FORMATS = ["COCO", "VOC", "LabelBox", "DataLoop"]

AVAILABLE_PLATFORMS = ["Desktop", "Web"]

ALLOWED_TASK_TYPES = [
    'panoptic_segmentation', 'instance_segmentation', 'keypoint_detection',
    'object_detection', 'vector_annotation', 'pixel_annotation'
]

ALLOWED_PROJECT_TYPES = ['Pixel', 'Vector']

ALLOWED_CONVERSIONS_SA_TO_COCO = [
    ('Pixel', 'panoptic_segmentation'), ('Pixel', 'instance_segmentation'),
    ('Vector', 'instance_segmentation'), ('Vector', 'keypoint_detection'),
    ('Vector', 'object_detection')
]

ALLOWED_CONVERSIONS_COCO_TO_SA = [
    ('Pixel', 'panoptic_segmentation'), ('Pixel', 'instance_segmentation'),
    ('Vector', 'keypoint_detection'), ('Vector', 'instance_segmentation')
]

ALLOWED_CONVERSIONS_VOC_TO_SA = [
    ('Vector', 'object_detection'), ('Vector', 'instance_segmentation'),
    ('Pixel', 'instance_segmentation')
]

ALLOWED_CONVERSIONS_LABELBOX_TO_SA = [
    ('Vector', 'object_detection'), ('Vector', 'instance_segmentation'),
    ('Vector', 'vector_annotation')
]

ALLOWED_CONVERSIONS_DATALOOP_TO_SA = [
    ('Vector', 'object_detection'), ('Vector', 'instance_segmentation'),
    ('Vector', 'vector_annotation')
]

ALLOWED_CONVERSIONS_SUPERVISELY_TO_SA = [('Vector', 'vector_annotation')]


def _passes_sanity_checks(args):
    if not isinstance(args.input_dir, (str, Path)):
        log_msg = "'input_dir' should be 'str' or 'Path' type, not '%s'" % (
            type(args.input_dir)
        )
        raise SABaseException(0, log_msg)

    if not isinstance(args.output_dir, (str, Path)):
        log_msg = "'output_dir' should be 'str' or 'Path' type, not {}".format(
            type(args.output_dir)
        )
        raise SABaseException(0, log_msg)

    if args.dataset_format not in AVAILABLE_ANNOTATION_FORMATS:
        log_msg = "'%s' converter doesn't exist. Possible candidates are '%s'"\
         % (args.dataset_format, AVAILABLE_ANNOTATION_FORMATS)
        raise SABaseException(0, log_msg)

    if not isinstance(args.dataset_name, str):
        log_msg = "'dataset_name' should be 'str' type, not {}".format(
            type(args.dataset_name)
        )
        raise SABaseException(0, log_msg)

    if args.project_type not in ALLOWED_PROJECT_TYPES:
        log_msg = "Please enter valid project type: 'Pixel' or 'Vector'"
        raise SABaseException(0, log_msg)

    if args.task not in ALLOWED_TASK_TYPES:
        log_msg = "Please enter valid task '%s'" % (ALLOWED_TASK_TYPES)
        raise SABaseException(0, log_msg)

    if 'platform' in args:
        if args.platform not in AVAILABLE_PLATFORMS:
            log_msg = "Please enter valid platform: 'Desktop' or 'Web'"
            raise SABaseException(0, log_msg)

    if args.task == "Pixel" and args.platform == "Desktop":
        log_msg = "Sorry, but Desktop Application doesn't support 'Pixel' projects yet."
        raise SABaseException(0, log_msg)

    return True


def _passes_converter_sanity(args, direction):
    converter_values = (args.project_type, args.task)
    if direction == 'import':
        if args.dataset_format == "COCO" and converter_values in ALLOWED_CONVERSIONS_COCO_TO_SA:
            return True
        elif args.dataset_format == "VOC" and converter_values in ALLOWED_CONVERSIONS_VOC_TO_SA:
            return True
        elif args.dataset_format == "LabelBox" and \
        converter_values in ALLOWED_CONVERSIONS_LABELBOX_TO_SA:
            return True
        elif args.dataset_format == "DataLoop" and converter_values in ALLOWED_CONVERSIONS_DATALOOP_TO_SA:
            return True
        elif args.dataset_format == "Supervisely" and converter_values in ALLOWED_CONVERSIONS_SUPERVISELY_TO_SA:
            return True
    else:
        if args.dataset_format == "COCO" and converter_values in ALLOWED_CONVERSIONS_SA_TO_COCO:
            return True

    log_msg = "Please enter valid converter values. You can check available \
        candidates in the documentation(https://superannotate.readthedocs.io/en/latest/index.html)."

    raise SABaseException(log_msg)


def export_annotation_format(
    input_dir,
    output_dir,
    dataset_format,
    dataset_name,
    project_type="Vector",
    task="object_detection",
    platform="Web",
):
    """Converts SuperAnnotate annotation formate to the other annotation formats. Currently available (project_type, task) combinations for converter
    presented below:

    ==============  ======================
             From SA to COCO
    --------------------------------------
     project_type           task
    ==============  ======================
    Pixel           panoptic_segmentation
    Pixel           instance_segmentation
    Vector          instance_segmentation
    Vector          object_detection
    Vector          keypoint_detection
    ==============  ======================

    :param input_dir: Path to the dataset folder that you want to convert.
    :type input_dir: str
    :param output_dir: Path to the folder, where you want to have converted dataset.
    :type output_dir: str
    :param dataset_format: One of the formats that are possible to convert. Available candidates are: ["COCO"]
    :type dataset_format: str
    :param dataset_name: Will be used to create json file in the output_dir.
    :type dataset_name: str
    :param project_type: SuperAnnotate project type is either 'Vector' or 'Pixel' (Default: 'Vector')
                         'Vector' project creates <image_name>___objects.json for each image.
                         'Pixel' project creates <image_name>___pixel.jsons and <image_name>___save.png annotation mask for each image.
    :type project_type: str
    :param task: Task can be one of the following: ['panoptic_segmentation', 'instance_segmentation',
                 'keypoint_detection', 'object_detection']. (Default: "objec_detection").
                 'keypoint_detection' can be used to converts keypoints from/to available annotation format.
                 'panoptic_segmentation' will use panoptic mask for each image to generate bluemask for SuperAnnotate annotation format and use bluemask to generate panoptic mask for invert conversion. Panoptic masks should be in the input folder.
                 'instance_segmentation' 'Pixel' project_type converts instance masks and 'Vector' project_type generates bounding boxes and polygons from instance masks. Masks should be in the input folder if it is 'Pixel' project_type.
                 'object_detection' converts objects from/to available annotation format
    :type task: str
    :param platform: SuperAnnotate has both 'Web' and 'Desktop' platforms. Choose from which one you are converting. (Default: "Web")
    :type platform: str

    """

    args = Namespace(
        input_dir=input_dir,
        output_dir=output_dir,
        dataset_format=dataset_format,
        dataset_name=dataset_name,
        project_type=project_type,
        task=task,
        platform=platform,
    )

    if not _passes_sanity_checks(args):
        sys.exit()
    if not _passes_converter_sanity(args, 'export'):
        sys.exit()

    export_from_sa(args)


def import_annotation_format(
    input_dir,
    output_dir,
    dataset_format,
    dataset_name,
    project_type="Vector",
    task="object_detection",
    platform="Web",
):
    """Converts other annotation formats to SuperAnnotate annotation format. Currently available (project_type, task) combinations for converter
    presented below:

    ==============  ======================
             From COCO to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Pixel           panoptic_segmentation
    Pixel           instance_segmentation
    Vector          instance_segmentation
    Vector          keypoint_detection
    ==============  ======================

    ==============  ======================
             From VOC to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Vector          instance_segmentation
    Vector          object_detection
    Pixel           instance_segmentation
    ==============  ======================

    ==============  ======================
           From LabelBox to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Vector          object_detection
    Vector          instance_segmentation
    Vector          vector_annotation
    ==============  ======================

    ==============  ======================
           From DataLoop to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Vector          object_detection
    Vector          instance_segmentation
    Vector          vector_annotation
    ==============  ======================

    ==============  ======================
           From Supervisely to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Vector          vector_annotation
    ==============  ======================

    :param input_dir: Path to the dataset folder that you want to convert.
    :type input_dir: str
    :param output_dir: Path to the folder, where you want to have converted dataset.
    :type output_dir: str
    :param dataset_format: Annotation format to convert SuperAnnotate annotation format. Available candidates are: ["COCO", "VOC", "LabelBox"]
    :type dataset_format: str
    :param dataset_name: Name of the json file in the input_dir, which should be converted.
    :type dataset_name: str
    :param project_type: SuperAnnotate project type is either 'Vector' or 'Pixel' (Default: 'Vector')
                         'Vector' project creates <image_name>___objects.json for each image.
                         'Pixel' project creates <image_name>___pixel.jsons and <image_name>___save.png annotation mask for each image.
    :type project_type: str
    :param task: Task can be one of the following: ['panoptic_segmentation', 'instance_segmentation',
                 'keypoint_detection', 'object_detection']. (Default: "objec_detection").
                 'keypoint_detection' can be used to converts keypoints from/to available annotation format.
                 'panoptic_segmentation' will use panoptic mask for each image to generate bluemask for SuperAnnotate annotation format and use bluemask to generate panoptic mask for invert conversion. Panoptic masks should be in the input folder.
                 'instance_segmentation' 'Pixel' project_type converts instance masks and 'Vector' project_type generates bounding boxes and polygons from instance masks. Masks should be in the input folder if it is 'Pixel' project_type.
                 'object_detection' converts objects from/to available annotation format
    :param platform: SuperAnnotate has both 'Web' and 'Desktop' platforms. Choose to which platform you want convert. (Default: "Web")
    :type platform: str

    """

    args = Namespace(
        input_dir=input_dir,
        output_dir=output_dir,
        dataset_format=dataset_format,
        dataset_name=dataset_name,
        project_type=project_type,
        task=task,
        platform=platform,
    )

    if not _passes_sanity_checks(args):
        sys.exit()
    if not _passes_converter_sanity(args, 'import'):
        sys.exit()

    import_to_sa(args)


def convert_platform(input_dir, output_dir, input_platform):
    """ Converts SuperAnnotate input file structure from one platform too another.

    :param input_dir: Path to the dataset folder that you want to convert.
    :type input_dir: str
    :param output_dir: Path to the folder where you want to have converted files.
    :type output_dir: str
    :param input_platform: Original platform format type
    :type input_platform: str

    """
    if not isinstance(input_dir, (str, Path)):
        log_msg = "'input_dir' should be 'str' or 'Path' type, not '%s'" % (
            type(input_dir)
        )
        raise SABaseException(0, log_msg)

    if not isinstance(output_dir, (str, Path)):
        log_msg = "'output_dir' should be 'str' or 'Path' type, not '%s'" % (
            type(output_dir)
        )
        raise SABaseException(0, log_msg)

    if input_platform not in AVAILABLE_PLATFORMS:
        log_msg = "Please enter valid platform: 'Desktop' or 'Web'"
        raise SABaseException(0, log_msg)

    sa_conversion(input_dir, output_dir, input_platform)
