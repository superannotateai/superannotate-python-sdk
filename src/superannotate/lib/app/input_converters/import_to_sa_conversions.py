"""
Module which will convert from other
annotation formats to superannotate annotation format
"""
import logging
import shutil
from pathlib import Path

from .converters.converters import Converter

logger = logging.getLogger("sa")


def _load_files(path_to_imgs, ptype, extensions):
    if extensions is None:
        extensions = ["jpg", "jpeg", "png", "tif", "tiff", "webp", "bmp"]

    logger.info(
        "All files with following extensions %s will be copied to output folder",
        extensions,
    )

    images = []
    for extension in extensions:
        rec_search = str(Path("**") / ("*." + extension))
        images_gen = Path(path_to_imgs).glob(rec_search)
        images.extend(list(images_gen))

    if not images:
        logger.warning("Images doesn't exist")

    return images


def _move_files(imgs, output_dir):
    (output_dir / "classes").mkdir(parents=True, exist_ok=True)
    output_path = output_dir

    for im in imgs:
        shutil.copy(im, output_path / Path(im).name)


def import_to_sa(args):
    """
    :param args: All arguments that will be used during convertion.
    :type args: Namespace
    """

    images = _load_files(
        args.input_dir / args.images_root, args.project_type, args.images_extensions
    )
    _move_files(images, args.output_dir)

    args.__dict__.update({"direction": "from", "export_root": args.input_dir})
    converter = Converter(args)

    converter.convert_to_sa()

    logger.info("Conversion completed")
