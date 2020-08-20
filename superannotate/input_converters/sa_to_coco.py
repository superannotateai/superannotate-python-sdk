import sys
import os
from argparse import ArgumentParser
import glob
import shutil
import json
import logging
import copy
import numpy as np

from sa_coco_converters.converters import Converter

ALLOWED_TASK_TYPES = [
    'panoptic_segmentation', 'instance_segmentation', 'keypoint_detection',
    'object_detection'
]
ALLOWED_PROJECT_TYPES = ['pixel', 'vector']
ALLOWED_CONVERSIONS = [
    ('pixel', 'panoptic_segmentation'), ('pixel', 'instance_segmentation'),
    ('vector', 'instance_segmentation'), ('vector', 'keypoint_detection'),
    ('pixel', 'object_detection')
]


def passes_sanity_checks(args):

    if args.train_val_split_ratio < 0 or args.train_val_split_ratio > 100:
        logging.error(
            "The split percentage should be in range (0,100), a number x will mean\
        to put x percent of input images in train set, and the rest in validation set"
        )
        return False
    if args.project_type not in ALLOWED_PROJECT_TYPES:
        logging.error('Please enter valid project type: pixel or vector')
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


def parse_args():
    argument_parser = ArgumentParser()

    argument_parser.add_argument(
        '-is',
        '--input_images_source',
        required=True,
        help=
        "The folder where images and their corresponding annotation json files are located",
        type=str
    )

    argument_parser.add_argument(
        '-sr',
        '--train_val_split_ratio',
        required=True,
        help="What percentage of input images should be in train set",
        type=int
    )

    argument_parser.add_argument(
        '-ptype',
        '--project_type',
        required=True,
        help="The type of the annotate.online project can be vector or pixel",
        type=str
    )

    argument_parser.add_argument(
        '-t',
        '--task',
        required=True,
        help=
        "The output format of the converted file, this corresponds to one of 5 coco tasks",
        type=str
    )

    argument_parser.add_argument(
        '-dn',
        '--dataset_name',
        required=True,
        help="The name of the dataset",
        type=str
    )

    argument_parser.add_argument(
        '-od',
        '--output_dir',
        required=True,
        help="The output folder for the coco json files test/train images",
        type=str
    )

    argument_parser.add_argument(
        '-cp',
        '--copyQ',
        required=True,
        help=
        "Move or copy source images to corresponding test and train folders",
        type=bool
    )

    args = argument_parser.parse_args()
    return args


def load_files(path_to_imgs, ratio, task, ptype):
    suffix = None
    if ptype == "pixel":
        suffix = '___pixel.json'
    else:
        suffix = '___objects.json'

    orig_images = glob.glob(os.path.join(path_to_imgs, '*'))
    orig_images = [x for x in orig_images if not os.path.isdir(x) and  '___' not in x.split('.')[-2] and  "mapper.json" not in x]
    all_files = None
    if task == 'keypoint_detection':
        all_files = np.array([(fname, fname + suffix) for fname in orig_images])

    elif ptype == 'pixel':
        all_files = np.array(
            [
                (fname, fname + suffix, fname + '___save.png')
                for fname in orig_images
            ]
        )
    elif ptype == 'vector':
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


def main(args, create_classes_mapper_fn=create_classes_mapper):
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
                os.path.join(args.input_images_source, 'classes/classes.json')
            )
    except Exception as e:
        create_classes_mapper_fn(args.input_images_source, args.output_dir)

    try:
        train_set, test_set = load_files(
            args.input_images_source, args.train_val_split_ratio, args.task,
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

    converter = Converter(
        args.project_type, args.task, args.dataset_name,
        os.path.join(args.output_dir, 'train_set'), args.output_dir
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
if __name__ == '__main__':
    args = parse_args()

    if not passes_sanity_checks(args):
        sys.exit()
    main(args)
