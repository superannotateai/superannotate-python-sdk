from typing import Union


class Response:
    def __init__(self, status: str = None, data: Union[dict, list] = None):
        self._status = status
        self._data = data
        self._errors = []

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def status(self):
        return self.data

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def errors(self):
        return "\n".join([str(error) for error in self._errors])

    @errors.setter
    def errors(self, error: list):
        self._errors.append(error)
