import logging
import os
import sys
import typing

__version__ = "4.4.10dev8"

sys.path.append(os.path.split(os.path.realpath(__file__))[0])

import logging.config  # noqa
import requests  # noqa
from packaging.version import parse  # noqa
from superannotate.lib.app.input_converters import convert_json_version  # noqa
from superannotate.lib.app.input_converters import convert_project_type  # noqa
from superannotate.lib.app.exceptions import AppException  # noqa
from superannotate.lib.app.input_converters import convert_json_version  # noqa
from superannotate.lib.app.input_converters import convert_project_type  # noqa
from superannotate.lib.app.input_converters import export_annotation  # noqa
from superannotate.lib.app.input_converters import import_annotation  # noqa
from superannotate.lib.app.interface.sdk_interface import SAClient  # noqa
from superannotate.lib.app.server import SAServer  # noqa
from superannotate.lib.app.server.utils import setup_app  # noqa
from superannotate.lib.core import PACKAGE_VERSION_INFO_MESSAGE  # noqa
from superannotate.lib.core import PACKAGE_VERSION_MAJOR_UPGRADE  # noqa
from superannotate.lib.core import PACKAGE_VERSION_UPGRADE  # noqa
import superannotate.lib.core.enums as enums  # noqa

SESSIONS = {}


def create_app(apps: typing.List[str] = None) -> SAServer:
    setup_app(apps)
    server = SAServer()
    return server


__all__ = [
    "__version__",
    "SAClient",
    "SAServer",
    "create_app",
    # Utils
    "enums",
    "AppException",
    # converters
    "convert_json_version",
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


if not os.environ.get("SA_VERSION_CHECK", "True").lower() == "false":
    log_version_info()
