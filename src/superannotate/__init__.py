import logging.config
import os
import sys

import requests
from packaging.version import parse
from superannotate.lib.app.analytics.class_analytics import class_distribution
from superannotate.lib.app.exceptions import AppException
from superannotate.lib.app.input_converters.conversion import convert_json_version
from superannotate.lib.app.input_converters.conversion import convert_project_type
from superannotate.lib.app.input_converters.conversion import export_annotation
from superannotate.lib.app.input_converters.conversion import import_annotation
from superannotate.lib.app.interface.sdk_interface import SAClient
from superannotate.lib.core import PACKAGE_VERSION_INFO_MESSAGE
from superannotate.lib.core import PACKAGE_VERSION_MAJOR_UPGRADE
from superannotate.lib.core import PACKAGE_VERSION_UPGRADE
from superannotate.logger import get_default_logger
from superannotate.version import __version__


__all__ = [
    "__version__",
    "SAClient",
    # Utils
    "AppException",
    # analytics
    "class_distribution",
    # converters
    "convert_json_version",
    "import_annotation",
    "export_annotation",
    "convert_project_type",
]

__author__ = "Superannotate"

sys.path.append(os.path.split(os.path.realpath(__file__))[0])
logging.getLogger("botocore").setLevel(logging.CRITICAL)
logger = get_default_logger()


def log_version_info():
    local_version = parse(__version__)
    if local_version.is_prerelease:
        logger.info(PACKAGE_VERSION_INFO_MESSAGE.format(__version__))
    req = requests.get("https://pypi.python.org/pypi/superannotate/json")
    if req.ok:
        releases = req.json().get("releases", [])
        pip_version = parse("0")
        for release in releases:
            ver = parse(release)
            if not ver.is_prerelease or local_version.is_prerelease:
                pip_version = max(pip_version, ver)
        if pip_version.major > local_version.major:
            logger.warning(
                PACKAGE_VERSION_MAJOR_UPGRADE.format(
                    local_version, pip_version
                )
            )
        elif pip_version > local_version:
            logger.warning(
                PACKAGE_VERSION_UPGRADE.format(local_version, pip_version)
            )


if not os.environ.get("SA_VERSION_CHECK", "True").lower() == "false":
    log_version_info()
