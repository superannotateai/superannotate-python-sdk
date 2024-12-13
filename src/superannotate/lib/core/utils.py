import asyncio
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
