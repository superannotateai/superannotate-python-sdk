"""
Main module for input converters
"""
from argparse import Namespace
from pathlib import Path

from ..exceptions import SABaseException
from .export_from_sa_conversions import export_from_sa
from .import_to_sa_conversions import import_to_sa
from .sa_conversion import (
    degrade_json, sa_convert_project_type, split_coco, upgrade_json
)

ALLOWED_TASK_TYPES = [
    'panoptic_segmentation', 'instance_segmentation', 'keypoint_detection',
    'object_detection', 'vector_annotation'
]

ALLOWED_PROJECT_TYPES = ['Pixel', 'Vector']

ALLOWED_ANNOTATION_IMPORT_FORMATS = {
    'COCO':
        [
            ('Pixel', 'panoptic_segmentation'),
            ('Pixel', 'instance_segmentation'),
            ('Vector', 'keypoint_detection'),
            ('Vector', 'instance_segmentation'), ('Vector', 'object_detection')
        ],
    'VOC':
        [
            ('Vector', 'object_detection'), ('Vector', 'instance_segmentation'),
            ('Pixel', 'instance_segmentation')
        ],
    'LabelBox':
        [
            ('Vector', 'object_detection'), ('Vector', 'instance_segmentation'),
            ('Vector', 'vector_annotation'), ('Pixel', 'instance_segmentation')
        ],
    'DataLoop':
        [
            ('Vector', 'object_detection'), ('Vector', 'instance_segmentation'),
            ('Vector', 'vector_annotation')
        ],
    'Supervisely':
        [
            ('Vector', 'vector_annotation'), ('Vector', 'object_detection'),
            ('Vector', 'instance_segmentation'),
            ('Pixel', 'instance_segmentation'),
            ('Vector', 'keypoint_detection')
        ],
    'VoTT':
        [
            ('Vector', 'object_detection'), ('Vector', 'instance_segmentation'),
            ('Vector', 'vector_annotation')
        ],
    'SageMaker':
        [('Pixel', 'instance_segmentation'), ('Vector', 'object_detection')],
    'VGG':
        [
            ('Vector', 'object_detection'), ('Vector', 'instance_segmentation'),
            ('Vector', 'vector_annotation')
        ],
    'GoogleCloud': [('Vector', 'object_detection')],
    'YOLO': [('Vector', 'object_detection')]
}

ALLOWED_ANNOTATION_EXPORT_FORMATS = {
    'COCO':
        [
            ('Pixel', 'panoptic_segmentation'),
            ('Pixel', 'instance_segmentation'),
            ('Vector', 'instance_segmentation'),
            ('Vector', 'keypoint_detection'), ('Vector', 'object_detection')
        ]
}


def _change_type(input_dir, output_dir):
    if isinstance(input_dir, str):
        input_dir = Path(input_dir)
    if isinstance(output_dir, str):
        output_dir = Path(output_dir)
    return input_dir, output_dir


def _passes_type_sanity(params_info):
    for param in params_info:
        if not isinstance(param[0], param[2]):
            raise SABaseException(
                0, "'%s' should be %s type, not %s" %
                (param[1], param[2], type(param[0]))
            )


def _passes_list_members_type_sanity(lists_info):
    for _list in lists_info:
        for _list_member in _list[0]:
            if not isinstance(_list_member, _list[2]):
                raise SABaseException(
                    0, "'%s' should be list of '%s', but contains '%s'" %
                    (_list[1], _list[2], type(_list_member))
                )


def _passes_value_sanity(values_info):
    for value in values_info:
        if value[0] not in value[2]:
            raise SABaseException(
                0, "'%s' should be one of the following '%s'" %
                (value[1], value[2])
            )


def _passes_converter_sanity(args, direction):
    converter_values = (args.project_type, args.task)
    test_passed = False
    if direction == 'import':
        if converter_values in ALLOWED_ANNOTATION_IMPORT_FORMATS[
            args.dataset_format]:
            test_passed = True
    else:
        if converter_values in ALLOWED_ANNOTATION_EXPORT_FORMATS[
            args.dataset_format]:
            test_passed = True

    if not test_passed:
        raise SABaseException(
            0,
            "Please enter valid converter values. You can check available candidates in the documentation (https://superannotate.readthedocs.io/en/stable/index.html)."
        )


def export_annotation(
    input_dir,
    output_dir,
    dataset_format,
    dataset_name,
    project_type="Vector",
    task="object_detection",
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
    :type input_dir: Pathlike(str or Path)
    :param output_dir: Path to the folder, where you want to have converted dataset.
    :type output_dir: Pathlike(str or Path)
    :param dataset_format: One of the formats that are possible to convert. Available candidates are: ["COCO"]
    :type dataset_format: str
    :param dataset_name: Will be used to create json file in the output_dir.
    :type dataset_name: str
    :param project_type: SuperAnnotate project type is either 'Vector' or 'Pixel' (Default: 'Vector')
                         'Vector' project creates <image_name>___objects.json for each image.
                         'Pixel' project creates <image_name>___pixel.jsons and <image_name>___save.png annotation mask for each image.
    :type project_type: str
    :param task: Task can be one of the following: ['panoptic_segmentation', 'instance_segmentation',
                 'keypoint_detection', 'object_detection']. (Default: "object_detection").
                 'keypoint_detection' can be used to converts keypoints from/to available annotation format.
                 'panoptic_segmentation' will use panoptic mask for each image to generate bluemask for SuperAnnotate annotation format and use bluemask to generate panoptic mask for invert conversion. Panoptic masks should be in the input folder.
                 'instance_segmentation' 'Pixel' project_type converts instance masks and 'Vector' project_type generates bounding boxes and polygons from instance masks. Masks should be in the input folder if it is 'Pixel' project_type.
                 'object_detection' converts objects from/to available annotation format
    :type task: str

    """

    params_info = [
        (input_dir, 'input_dir', (str, Path)),
        (output_dir, 'output_dir', (str, Path)),
        (dataset_name, 'dataset_name', str),
        (dataset_format, 'dataset_format', str),
        (project_type, 'project_type', str), (task, 'task', str)
    ]
    _passes_type_sanity(params_info)
    input_dir, output_dir = _change_type(input_dir, output_dir)

    values_info = [
        (project_type, 'project_type', ALLOWED_PROJECT_TYPES),
        (task, 'task', ALLOWED_TASK_TYPES),
        (
            dataset_format, 'dataset_format',
            list(ALLOWED_ANNOTATION_EXPORT_FORMATS.keys())
        )
    ]
    _passes_value_sanity(values_info)

    args = Namespace(
        input_dir=input_dir,
        output_dir=output_dir,
        dataset_format=dataset_format,
        dataset_name=dataset_name,
        project_type=project_type,
        task=task,
    )

    _passes_converter_sanity(args, 'export')

    export_from_sa(args)


def import_annotation(
    input_dir,
    output_dir,
    dataset_format,
    dataset_name='',
    project_type="Vector",
    task="object_detection",
    images_root='',
    images_extensions=None
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
    Vector          object_detection
    Vector          keypoint_detection
    ==============  ======================

    ==============  ======================
             From VOC to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Pixel           instance_segmentation
    Vector          instance_segmentation
    Vector          object_detection
    ==============  ======================

    ==============  ======================
           From LabelBox to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Vector          object_detection
    Vector          instance_segmentation
    Vector          vector_annotation
    Pixel           instance_segmentation
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
    Vector          object_detection
    Vector          keypoint_detection
    Vector          vector_annotation
    Vector          instance_segmentation
    Pixel           instance_segmentation
    ==============  ======================

    ==============  ======================
           From VoTT to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Vector          instance_segmentation
    Vector          object_detection
    Vector          vector_annotation
    ==============  ======================

    ==============  ======================
           From SageMaker to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Pixel           instance_segmentation
    Vector          objcet_detection
    ==============  ======================

    ==============  ======================
           From VGG to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Vector          instance_segmentation
    Vector          object_detection
    Vector          vector_annotation
    ==============  ======================

    ==============  ======================
           From GoogleCloud to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Vector          object_detection
    ==============  ======================

    ==============  ======================
           From YOLO to SA
    --------------------------------------
     project_type           task
    ==============  ======================
    Vector          object_detection
    ==============  ======================

    :param input_dir: Path to the dataset folder that you want to convert.
    :type input_dir: Pathlike(str or Path)
    :param output_dir: Path to the folder, where you want to have converted dataset.
    :type output_dir: Pathlike(str or Path)
    :param dataset_format: Annotation format to convert SuperAnnotate annotation format. Available candidates are: ["COCO", "VOC", "LabelBox", "DataLoop",
                        "Supervisely", 'VGG', 'YOLO', 'SageMake', 'VoTT', 'GoogleCloud']
    :type dataset_format: str
    :param dataset_name: Name of the json file in the input_dir, which should be converted.
    :type dataset_name: str
    :param project_type: SuperAnnotate project type is either 'Vector' or 'Pixel' (Default: 'Vector')
                         'Vector' project creates <image_name>___objects.json for each image.
                         'Pixel' project creates <image_name>___pixel.jsons and <image_name>___save.png annotation mask for each image.
    :type project_type: str
    :param task: Task can be one of the following: ['panoptic_segmentation', 'instance_segmentation',
                 'keypoint_detection', 'object_detection', 'vector_annotation']. (Default: "object_detection").
                 'keypoint_detection' can be used to converts keypoints from/to available annotation format.
                 'panoptic_segmentation' will use panoptic mask for each image to generate bluemask for SuperAnnotate annotation format and use bluemask to generate panoptic mask for invert conversion. Panoptic masks should be in the input folder.
                 'instance_segmentation' 'Pixel' project_type converts instance masks and 'Vector' project_type generates bounding boxes and polygons from instance masks. Masks should be in the input folder if it is 'Pixel' project_type.
                 'object_detection' converts objects from/to available annotation format
                 'vector_annotation' can be used to convert all annotations (point, ellipse, circule, cuboid and etc) to SuperAnnotate vector project.
    :param images_root: Additonal path to images directory in input_dir
    :type images_root: str
    :param image_extensions: List of image files xtensions in the images_root folder
    :type image_extensions: list

    """

    params_info = [
        (input_dir, 'input_dir', (str, Path)),
        (output_dir, 'output_dir', (str, Path)),
        (dataset_name, 'dataset_name', str),
        (dataset_format, 'dataset_format', str),
        (project_type, 'project_type', str), (task, 'task', str),
        (images_root, 'images_root', str)
    ]

    if images_extensions is not None:
        params_info.append((images_extensions, 'image_extensions', list))

    _passes_type_sanity(params_info)

    values_info = [
        (project_type, 'project_type', ALLOWED_PROJECT_TYPES),
        (task, 'task', ALLOWED_TASK_TYPES),
        (
            dataset_format, 'dataset_format',
            list(ALLOWED_ANNOTATION_IMPORT_FORMATS.keys())
        )
    ]
    _passes_value_sanity(values_info)

    input_dir, output_dir = _change_type(input_dir, output_dir)
    args = Namespace(
        input_dir=input_dir,
        output_dir=output_dir,
        dataset_format=dataset_format,
        dataset_name=dataset_name,
        project_type=project_type,
        task=task,
        images_root=images_root,
        images_extensions=images_extensions
    )

    _passes_converter_sanity(args, 'import')

    import_to_sa(args)


def convert_project_type(input_dir, output_dir):
    """ Converts SuperAnnotate 'Vector' project type to 'Pixel' or reverse.

    :param input_dir: Path to the dataset folder that you want to convert.
    :type input_dir: Pathlike(str or Path)
    :param output_dir: Path to the folder where you want to have converted files.
    :type output_dir: Pathlike(str or Path)

    """
    params_info = [
        (input_dir, 'input_dir', (str, Path)),
        (output_dir, 'output_dir', (str, Path)),
    ]
    _passes_type_sanity(params_info)
    input_dir, output_dir = _change_type(input_dir, output_dir)

    sa_convert_project_type(input_dir, output_dir)


def coco_split_dataset(
    coco_json_path, image_dir, output_dir, dataset_list_name, ratio_list
):
    """ Splits COCO dataset to few datsets.

    :param coco_json_path: Path to main COCO JSON dataset, which should be splitted.
    :type coco_json_path: Pathlike(str or Path)
    :param image_dir: Path to all images in the original dataset.
    :type coco_json_path: str or Pathlike
    :param coco_json_path: Path to the folder where you want to output splitted COCO JSON files.
    :type coco_json_path: str or Pathlike
    :param dataset_list_name: List of dataset names.
    :type dataset_list_name: list
    :param ratio_list: List of ratios for each splitted dataset.
    :type ratio_list: list
    """
    params_info = [
        (coco_json_path, 'coco_json_path', (str, Path)),
        (image_dir, 'image_dir', (str, Path)),
        (output_dir, 'output_dir', (str, Path)),
        (dataset_list_name, 'dataset_list_name', list),
        (ratio_list, 'ratio_list', list)
    ]
    _passes_type_sanity(params_info)

    lists_info = [
        (dataset_list_name, 'dataset_name', str),
        (ratio_list, 'ratio_list', (int, float))
    ]

    _passes_list_members_type_sanity(lists_info)

    if sum(ratio_list) != 100:
        raise SABaseException(0, "Sum of 'ratio_list' members must be 100")

    if len(dataset_list_name) != len(ratio_list):
        raise SABaseException(
            0, "'dataset_list_name' and 'ratio_list' should have same lenght"
        )

    if isinstance(coco_json_path, str):
        coco_json_path = Path(coco_json_path)
    if isinstance(image_dir, str):
        image_dir = Path(image_dir)
    if isinstance(output_dir, str):
        output_dir = Path(output_dir)

    split_coco(
        coco_json_path, image_dir, output_dir, dataset_list_name, ratio_list
    )


def convert_json_version(input_dir, output_dir, version=2):
    """
    Converts SuperAnnotate JSON versions. Newest JSON version is 2.

    :param input_dir: Path to the dataset folder that you want to convert.
    :type input_dir: Pathlike(str or Path)
    :param output_dir: Path to the folder, where you want to have converted dataset.
    :type output_dir: Pathlike(str or Path)
    :param version: Output version number. Currently is either 1 or 2. Default value is 2. It will upgrade version 1 to  version 2. Set 1 to degrade from version 2 to version 1.
    :type version: int

    :return: List of converted files
    :rtype: list
    """

    params_info = [
        (input_dir, 'input_dir', (str, Path)),
        (output_dir, 'output_dir', (str, Path)), (version, 'version', int)
    ]
    _passes_type_sanity(params_info)
    input_dir, output_dir = _change_type(input_dir, output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    if version == 2:
        converted_files = upgrade_json(input_dir, output_dir)
    elif version == 1:
        converted_files = degrade_json(input_dir, output_dir)
    else:
        raise SABaseException(0, "'version' is either 1 or 2.")

    return converted_files
