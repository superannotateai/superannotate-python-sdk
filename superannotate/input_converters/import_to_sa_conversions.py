"""
Module which will run converters and convert from other
annotation formats to superannotate annotation format
"""
import logging
import shutil
from pathlib import Path

from .converters.converters import Converter

logger = logging.getLogger("superannotate-python-sdk")


def _load_files(path_to_imgs, ptype):
    rec_search = str(Path('**') / '*.jpg')
    images_gen = Path(path_to_imgs).glob(rec_search)
    images = list(images_gen)

    if not images:
        logger.warning("Images doesn't exist")

    if ptype == 'Pixel':
        rec_search = str(Path('**') / '*.png')
        masks_gen = Path(path_to_imgs).glob(rec_search)
        masks = list(masks_gen)
        # if not masks:
        #     logger.warning("Masks doesn't exist")
    else:
        masks = []

    return images, masks


def _move_files(imgs, masks, output_dir, platforom):
    if platforom == "Desktop":
        output_path = output_dir / "images"
        output_path.mkdir(parents=True)
    else:
        (output_dir / 'classes').mkdir(parents=True, exist_ok=True)
        output_path = output_dir

    for im in imgs:
        shutil.copy(im, output_path / Path(im).name)

    for mask in masks:
        shutil.copy(mask, output_path / Path(mask).name)


def import_to_sa(args):
    """
    :param args: All arguments that will be used during convertion.
    :type args: Namespace
    """

    images, masks = _load_files(
        args.input_dir / args.images_root, args.project_type
    )
    _move_files(images, masks, args.output_dir, args.platform)

    args.__dict__.update({'direction': 'from', 'export_root': args.input_dir})
    converter = Converter(args)

    converter.convert_to_sa(args.platform)

    logger.info('Conversion completed successfully')
