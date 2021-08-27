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
        return "\n".join([error.message for error in self._errors])

    @errors.setter
    def errors(self, error: list):
        self._errors.append(error)

    def aggregate(self):
        return AggregatedResponse(self)


class AggregatedResponse(Response):
    def __init__(
        self, root: Response, status: str = None, data: Union[dict, list] = None
    ):
        super().__init__(status, data)
        self._root = root
        if self._data:
            self.data = data

    @property
    def data(self):
        return self._root.data

    @data.setter
    def data(self, value):
        if self._root.data:
            if isinstance(self._root.data, dict) and isinstance(value, dict):
                self._root._data.update(value)
            elif isinstance(self._root.data, list):
                self._root._data.append(value)
        else:
            self._root.data = value
