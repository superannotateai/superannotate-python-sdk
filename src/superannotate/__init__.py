import logging
import os
import sys


__version__ = "4.4.36b1"


os.environ.update({"sa_version": __version__})
sys.path.append(os.path.split(os.path.realpath(__file__))[0])

import requests
from lib.core import enums
from packaging.version import parse
from lib.core import PACKAGE_VERSION_UPGRADE
from lib.core import PACKAGE_VERSION_INFO_MESSAGE
from lib.core import PACKAGE_VERSION_MAJOR_UPGRADE
from lib.core.exceptions import AppException
from lib.core.exceptions import FileChangedError
from superannotate.lib.app.input_converters import convert_project_type
from superannotate.lib.app.input_converters import export_annotation
from superannotate.lib.app.input_converters import import_annotation
from superannotate.lib.app.interface.sdk_interface import SAClient
from superannotate.lib.app.interface.sdk_interface import ItemContext


SESSIONS = {}


__all__ = [
    "__version__",
    "SAClient",
    "ItemContext",
    # Utils
    "enums",
    "AppException",
    "FileChangedError",
    "import_annotation",
    "export_annotation",
    "convert_project_type",
]

__author__ = "Superannotate"

logging.getLogger("botocore").setLevel(logging.CRITICAL)


def log_version_info():
    logging.StreamHandler(sys.stdout)
    local_version = parse(__version__)
    if local_version.is_prerelease:
        logging.info(PACKAGE_VERSION_INFO_MESSAGE.format(__version__))
    req = requests.get("https://pypi.org/pypi/superannotate/json")
    if req.ok:
        releases = req.json().get("releases", [])
        pip_version = parse("0")
        for release in releases:
            ver = parse(release)
            if not ver.is_prerelease or local_version.is_prerelease:
                pip_version = max(pip_version, ver)
        if pip_version.major > local_version.major:
            logging.warning(
                PACKAGE_VERSION_MAJOR_UPGRADE.format(local_version, pip_version)
            )
        elif pip_version > local_version:
            logging.warning(PACKAGE_VERSION_UPGRADE.format(local_version, pip_version))


if os.environ.get("SA_VERSION_CHECK", "True").lower() != "false":
    log_version_info()
