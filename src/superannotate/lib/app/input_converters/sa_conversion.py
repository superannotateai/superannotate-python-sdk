import logging
import shutil


logger = logging.getLogger("sa")


def copy_file(src_path, dst_path):
    shutil.copy(src_path, dst_path)
