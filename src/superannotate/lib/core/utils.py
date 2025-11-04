import asyncio
import re
import typing
from threading import Thread


class AsyncThread(Thread):
    def __init__(
        self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None
    ):
        super().__init__(
            group=group,
            target=target,
            name=name,
            args=args,
            kwargs=kwargs,
            daemon=daemon,
        )
        self._exc = None
        self._response = None

    @property
    def response(self):
        return self._response

    def run(self):
        try:
            self._response = super().run()
        except BaseException as e:
            self._exc = e

    def join(self, timeout=None) -> typing.Any:
        Thread.join(self, timeout=timeout)
        if self._exc:
            raise self._exc
        return self._response


def run_async(f):
    response = [None]

    def wrapper(func: typing.Callable):
        response[0] = asyncio.run(func)  # noqa
        return response[0]

    thread = AsyncThread(target=wrapper, args=(f,))
    thread.start()
    thread.join()
    return response[0]


def parse_version(version_string):
    """Smart version parsing with support for various formats"""
    # Remove 'v' prefix if present
    version_string = version_string.lstrip("v")

    # Extract version parts using regex
    match = re.match(
        r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-.]?(a|b|rc|dev|alpha|beta)(\d*))?",
        version_string,
    )

    if not match:
        raise ValueError(f"Invalid version format: {version_string}")

    major = int(match.group(1))
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    pre_type = match.group(4)
    pre_num = int(match.group(5) or 0) if match.group(5) else 0

    class Version:
        def __init__(self, major, minor, patch, pre_type=None, pre_num=0):
            self.major = major
            self.minor = minor
            self.patch = patch
            self.pre_type = pre_type
            self.pre_num = pre_num

        @property
        def is_prerelease(self):
            return self.pre_type is not None

        def __str__(self):
            version = f"{self.major}.{self.minor}.{self.patch}"
            if self.pre_type:
                version += f"-{self.pre_type}{self.pre_num}"
            return version

        def __gt__(self, other):
            if self.major != other.major:
                return self.major > other.major
            if self.minor != other.minor:
                return self.minor > other.minor
            if self.patch != other.patch:
                return self.patch > other.patch
            # Handle prerelease comparison
            if self.is_prerelease and not other.is_prerelease:
                return False
            if not self.is_prerelease and other.is_prerelease:
                return True
            return self.pre_num > other.pre_num

    return Version(major, minor, patch, pre_type, pre_num)
