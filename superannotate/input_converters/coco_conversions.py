import sys
import os
import glob
import shutil
import json
import logging
import copy
import numpy as np
from argparse import Namespace

from .converters.converters import Converter

ALLOWED_TASK_TYPES = [
    'panoptic_segmentation', 'instance_segmentation', 'keypoint_detection',
    'object_detection'
]
ALLOWED_PROJECT_TYPES = ['Pixel', 'Vector']
ALLOWED_CONVERSIONS = [
    ('Pixel', 'panoptic_segmentation'), ('Pixel', 'instance_segmentation'),
    ('Vector', 'instance_segmentation'), ('Vector', 'keypoint_detection'),
    ('Pixel', 'object_detection')
]


def passes_sanity_checks(args):

    if hasattr(args, "train_val_split_ratio"):
        if args.train_val_split_ratio < 0 or args.train_val_split_ratio > 100:
            logging.error(
                "The split percentage should be in range (0,100), a number x will mean\
            to put x percent of input images in train set, and the rest in validation set"
            )
            return False
    if args.project_type not in ALLOWED_PROJECT_TYPES:
        logging.error('Please enter valid project type: Pixel or Vector')
        return False
    if args.task not in ALLOWED_TASK_TYPES:
        logging.error(
            'Please enter valid task: instance_segmentation, panoptic_segmentation, keypoint_detection'
        )
        return False
    tp = (args.project_type, args.task)
    if tp not in ALLOWED_CONVERSIONS:
        logging.error(
            'Converting from project type {} to coco format for the task {} is not supported'
            .format(args.project_type, args.task)
        )
        return False
    return True


def load_files(path_to_imgs, ratio, task, ptype):
    suffix = None
    if ptype == "Pixel":
        suffix = '___pixel.json'
    else:
        suffix = '___objects.json'

    orig_images = glob.glob(os.path.join(path_to_imgs, '*'))
    orig_images = [
        x for x in orig_images if not os.path.isdir(x) and
        '___' not in x.split('.')[-2] and "mapper.json" not in x
    ]
    all_files = None
    if task == 'keypoint_detection':
        all_files = np.array([(fname, fname + suffix) for fname in orig_images])

    elif ptype == 'Pixel':
        all_files = np.array(
            [
                (fname, fname + suffix, fname + '___save.png')
                for fname in orig_images
            ]
        )
    elif ptype == 'Vector':
        all_files = np.array([(fname, fname + suffix) for fname in orig_images])
    num_train_vals = int(len(all_files) * (ratio / 100))

    num_test_vals = len(all_files) - num_train_vals

    train_indices = set(
        np.random.choice(range(len(all_files)), num_train_vals, replace=False)
    )

    all_indices = set(range(len(all_files)))

    test_indices = all_indices.difference(train_indices)
    test_set = None
    train_set = None

    if len(test_indices) > 0:
        test_set = all_files[np.array(list(test_indices))]
    if len(train_indices) > 0:
        train_set = all_files[np.array(list(train_indices))]
    return (train_set, test_set)


def load_files_sa(path_to_imgs, ptype):
    images = glob.glob(
        os.path.join(path_to_imgs, "**", "*.jpg"), recursive=True
    )
    if len(images) == 0:
        logging.error("Images doesn't exist")

    if ptype == "Pixel":
        masks = glob.glob(
            os.path.join(path_to_imgs, "**", "*.png"), recursive=True
        )
        if len(masks) == 0:
            logging.warning("Masks doesn't exist")
    else:
        masks = None

    return images, masks


def move_files(train_set, test_set, src, cp):

    train_path = os.path.join(src, 'train_set')
    test_path = os.path.join(src, 'test_set')
    move_fn = None

    if cp:
        move_fn = shutil.copy
        logging.warning(
            'Source image files will be copied to output_dir/test and output_dir/train folders'
        )
    else:
        move_fn = shutil.move
        logging.warning(
            'Source image files will be moved to output_dir/test and output_dir/train folders'
        )
    if train_set is not None:
        for tup in train_set:
            for i in tup:
                move_fn(i, os.path.join(train_path, i.split('/')[-1]))
    if test_set is not None:
        for tup in test_set:
            for i in tup:
                move_fn(i, os.path.join(test_path, i.split('/')[-1]))


def move_files_sa(imgs, masks, output_dir, cp):
    if cp:
        move_fn = shutil.copy
        logging.warning('Source image files will be copied to output_dir')
    else:
        move_fn = shutil.move
        logging.warning('Source image files will be moved to output_dir')

    if imgs is not None:
        for im in imgs:
            move_fn(im, os.path.join(output_dir, os.path.basename(im)))

    if masks is not None:
        for mask in masks:
            move_fn(mask, os.path.join(output_dir, os.path.basename(mask)))


def create_classes_mapper(imgs, classes_json):
    classes = {}
    j_data = json.load(open(classes_json))
    for instance in j_data:
        if 'id' not in instance:
            continue
        classes[instance['name']] = instance['id']

    with open(os.path.join(imgs, 'test_set', 'classes_mapper.json'), 'w') as fp:
        json.dump(classes, fp)

    with open(
        os.path.join(imgs, 'train_set', 'classes_mapper.json'), 'w'
    ) as fp:
        json.dump(classes, fp)


def _generate_colors(number):
    total = 255**3
    color = []
    for i in range(number):
        idx = int(i * total / number)
        r = idx // (255**2)
        g = (idx % (255**2)) // 255
        b = (idx % (255**2)) % 255
        color.append("#%02x%02x%02x" % (r, g, b))
    return color


def create_sa_classes(path_to_write, classes_json):
    json_data = json.load(open(classes_json))
    classes_list = json_data["categories"]

    colors = _generate_colors(len(classes_list))
    classes = []
    for c, data in enumerate(classes_list):
        classes_dict = {
            'name': data["name"],
            'id': data["id"],
            'color': colors[c],
            'attribute_groups': []
        }
        classes.append(classes_dict)
    with open(
        os.path.join(path_to_write, "classes", "classes.json"), "w"
    ) as fp:
        json.dump(classes, fp)


def sa_to_coco(args, create_classes_mapper_fn=create_classes_mapper):
    if not passes_sanity_checks(args):
        sys.exit()

    train_set = None
    test_set = None

    try:
        os.makedirs(os.path.join(args.output_dir, 'train_set'))
        os.makedirs(os.path.join(args.output_dir, 'test_set'))
    except Exception as e:
        logging.error(
            'Could not make test and train set paths, check if they already exist'
        )
        sys.exit()

    try:
        if args.task == 'instance_segmentation' or args.task == 'panoptic_segmentation' or args.task == 'object_detection':
            create_classes_mapper_fn(
                args.output_dir,
                os.path.join(args.input_dir, 'classes/classes.json')
            )
    except Exception as e:
        create_classes_mapper_fn(args.input_dir, args.output_dir)

    try:
        train_set, test_set = load_files(
            args.input_dir, args.train_val_split_ratio, args.task,
            args.project_type
        )
    except Exception as e:
        logging.error(
            'Something went wrong while loading files from source directory, check if you have valid export'
        )
        logging.error(e)

    try:
        move_files(train_set, test_set, args.output_dir, args.copyQ)
    except Exception as e:
        logging.error(
            'Something is went wrong while moving or copying files from source folder'
        )
        logging.error(e)

    method = Namespace(direction="to", dataset_format=args.dataset_format)

    converter = Converter(
        args.project_type, args.task, args.dataset_name,
        os.path.join(args.output_dir, 'train_set'), args.output_dir, method
    )

    if train_set is not None:
        converter.strategy.set_dataset_name(args.dataset_name + '_train')
        print(converter.strategy)
        try:
            converter.convert_from_sa()
        except Exception as e:
            logging.error('Something went wrong while converting train set')
            logging.error(e)
            sys.exit()

    converter.strategy.set_dataset_name(args.dataset_name + '_test')
    converter.strategy.set_export_root(
        os.path.join(args.output_dir, 'test_set')
    )
    train_set_failed = copy.deepcopy(converter.strategy.failed_conversion_cnt)
    converter.strategy.failed_conversion_cnt = 0
    if test_set is not None:
        try:
            converter.convert_from_sa()
        except Exception as e:
            logging.error(
                'Something went wrong while converting the validation set'
            )
            logging.error(e)
            sys.exit()

    test_set_failed = copy.deepcopy(converter.strategy.failed_conversion_cnt)

    logging.info('Conversion completed successfully')
    return train_set_failed, test_set_failed


def coco_to_sa(args):
    if not passes_sanity_checks(args):
        sys.exit()
    try:
        os.makedirs(os.path.join(args.output_dir, "classes"))
    except Exception as e:
        logging.error(
            "Could not create output folders, check if they already exist"
        )
        sys.exit()

    try:
        if args.task == "panoptic_segmentation" or args.task == "keypoint_detection" or args.task == "instance_segmentation":
            create_sa_classes(
                args.output_dir,
                os.path.join(args.input_dir, args.dataset_name + '.json')
            )
    except Exception as e:
        logging.error("Can't 'create classes.json'")

    try:
        images, masks = load_files_sa(args.input_dir, args.project_type)
    except Exception as e:
        logging.error("Can't load images or masks")
        logging.error(e)

    try:
        move_files_sa(images, masks, args.output_dir, args.copyQ)
    except Exception as e:
        logging.error(
            'Something is went wrong while moving or copying files from source folder'
        )
        logging.error(e)

    method = Namespace(direction="from", dataset_format=args.dataset_format)

    converter = Converter(
        args.project_type, args.task, args.dataset_name, args.input_dir,
        args.output_dir, method
    )

    try:
        converter.convert_to_sa()
    except Exception as e:
        logging.error("Something went wrong while converting")
        sys.exit()
