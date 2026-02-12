"""
COCO to SA conversion method
"""
import logging

from .coco_api import _maskfrRLE
from .coco_api import decode

logger = logging.getLogger("sa")


def annot_to_bitmask(annot):
    if isinstance(annot["counts"], list):
        bitmask = _maskfrRLE(annot)
    elif isinstance(annot["counts"], str):
        bitmask = decode(annot)

    return bitmask
