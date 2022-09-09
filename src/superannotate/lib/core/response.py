from typing import Union


class Response:
    def __init__(self, status: str = None, data: Union[dict, list] = None):
        self._status = status
        self._data = data
        self._report = []
        self._errors = []

    def __str__(self):
        return f"Response object with status:{self.status}, data : {self.data}, errors: {self.errors} "

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def report(self):
        return "\n".join(self._report)

    @report.setter
    def report(self, value: str):
        self._report.append(value)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def errors(self):
        return "\n".join([str(error) for error in self._errors])

    @errors.setter
    def errors(self, error: list):
        self._errors.append(error)
