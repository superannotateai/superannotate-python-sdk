import urllib.parse
from abc import abstractmethod
from enum import Enum
from typing import Any
from typing import List


class OperatorEnum(str, Enum):
    EQ = "$eq"
    NE = "$ne"
    GT = "$gt"
    LT = "$lt"
    CONTAINS = "$cont"
    STARTS = "$starts"
    ENDS = "$ends"
    IN = "$in"
    NOTIN = "$notin"


class Query:
    def __init__(self):
        self.condition_set: List[Query] = []

    @abstractmethod
    def build(self) -> str:
        """Abstract method to build the query."""
        pass

    def __and__(self, other: "Query") -> "Query":
        if not isinstance(other, Query):
            raise TypeError("Only Query types are supported in 'and' operations.")
        self.condition_set.extend(other.condition_set)
        return self

    def build_query(self) -> str:
        """Builds a query string based on the condition set."""
        return "&".join(
            condition.build()
            for condition in self.condition_set
            if not isinstance(condition, EmptyQuery)
        )


class EmptyQuery(Query):
    def build(self) -> str:
        return ""


class Filter(Query):
    def __init__(self, key: str, value: Any, operator: OperatorEnum):
        super().__init__()
        self._key = key
        self._value = value
        self._operator = operator
        self.condition_set = [self]

    @property
    def key(self) -> str:
        return self._key

    @property
    def operator(self) -> OperatorEnum:
        return self._operator

    @property
    def value(self) -> Any:
        return self._value

    def _build(self):
        if isinstance(self._value, (list, set, tuple)):
            return f"{self._key}||{self._operator.value}||{','.join(map(urllib.parse.quote, map(str, self._value)))}"
        else:
            return f"{self._key}||{self._operator.value}||{urllib.parse.quote(str(self._value))}"

    def build(self) -> str:
        return f"filter={self._build()}"


class OrFilter(Filter):
    def __init__(self, key: str, value: Any, operator: OperatorEnum):
        super().__init__(key, value, operator)

    def build(self) -> str:
        return f"or={self._build()}"


class Join(Query):
    def __init__(self, relation: str, fields: List[str] = None):
        super().__init__()
        self._relation = relation
        self._fields = fields
        self.condition_set = [self]

    def build(self) -> str:
        fields_str = f"||{','.join(self._fields)}" if self._fields else ""
        return f"join={self._relation}{fields_str}"
