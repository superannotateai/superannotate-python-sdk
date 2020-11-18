"""
Module which will run converters and convert from other
annotation formats to superannotate annotation format
"""
import glob
import logging
import os
import shutil

from .converters.converters import Converter
from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")


def _load_files(path_to_imgs, ptype):
    images = glob.glob(
        os.path.join(path_to_imgs, "**", "*.jpg"), recursive=True
    )
    if not images:
        logger.warning("Images doesn't exist")

    if ptype == "Pixel":
        masks = glob.glob(
            os.path.join(path_to_imgs, "**", "*.png"), recursive=True
        )
        if not masks:
            logger.warning("Masks doesn't exist")
    else:
        masks = None

    return images, masks


def _move_files(imgs, masks, output_dir, platforom):
    if platforom == "Desktop":
        output_path = os.path.join(output_dir, "images")
        os.makedirs(output_path)
    else:
        os.makedirs(os.path.join(output_dir, 'classes'))
        output_path = output_dir

    if imgs is not None:
        for im in imgs:
            shutil.copy(im, os.path.join(output_path, os.path.basename(im)))

    if masks is not None:
        for mask in masks:
            shutil.copy(mask, os.path.join(output_path, os.path.basename(mask)))


def import_to_sa(args):
    """
    :param args: All arguments that will be used during convertion.
    :type args: Namespace
    """

    images, masks = _load_files(args.input_dir, args.project_type)
    _move_files(images, masks, args.output_dir, args.platform)

    args.__dict__.update({'direction': 'from', 'export_root': args.input_dir})
    converter = Converter(args)

    converter.convert_to_sa(args.platform)

    logger.info('Conversion completed successfully')
