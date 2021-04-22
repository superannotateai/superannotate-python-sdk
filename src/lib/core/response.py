class Response:
    def __init__(self, status: str = None, data: dict = None):
        self._status = status
        self._data = data

    @property
    def data(self):
        return self.data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def status(self):
        return self.data

    @status.setter
    def status(self, value):
        self._status = value
