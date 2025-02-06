import urllib.parse
from abc import abstractmethod
from collections import defaultdict
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple


class OperatorEnum(str, Enum):
    EQ = "$eq"
    NE = "$ne"
    GT = "$gt"
    GTE = "$gte"
    LT = "$lt"
    LTE = "$lte"
    IS = "$is"
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

    @abstractmethod
    def body_build(self) -> Tuple[str, Any]:
        """Abstract method to build the body query."""
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

    def body_builder(self):
        search: Dict[str, list] = defaultdict(list)
        join: List[str] = []
        limit: Optional[int] = None
        offset: Optional[int] = None

        for condition in self.condition_set:
            if not isinstance(condition, EmptyQuery):
                c_type, c_value = condition.body_build()
                if isinstance(condition, Filter):
                    search[c_type].extend(c_value)
                elif isinstance(condition, Join):
                    join.append(c_value)
                elif isinstance(condition, Limit):
                    limit = c_value
                elif isinstance(condition, Offset):
                    offset = c_value
        return {
            "query": {
                "limit": limit,
                "offset": offset,
                "search": search,
                "join": join,
            }
        }


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

    def body_build(self) -> Tuple[str, List[Dict]]:
        filter_value: List[Dict] = []
        if self._value is None and self._operator == OperatorEnum.EQ:
            filter_value.append({self._key: {"$isnull": True}})
        elif self._operator == OperatorEnum.NOTIN:
            filter_value.append(
                {
                    "$or": [
                        {self._key: {self._operator.value: self._value}},
                        {self._key: {"$isnull": True}},
                    ]
                }
            )
        else:
            filter_value.append({self._key: {self._operator.value: self._value}})
            if self._key.startswith("customField.custom_field_values."):
                filter_value.append({self._key: {"$notnull": True}})
        return "$and", filter_value


class OrFilter(Filter):
    def __init__(self, key: str, value: Any, operator: OperatorEnum):
        super().__init__(key, value, operator)

    def build(self) -> str:
        return f"or={self._build()}"

    def body_build(self) -> Tuple[str, List[Dict]]:
        raise NotImplementedError


class Join(Query):
    def __init__(self, relation: str, fields: List[str] = None):
        super().__init__()
        self._relation = relation
        self._fields = fields
        self.condition_set = [self]

    def build(self) -> str:
        fields_str = f"||{','.join(self._fields)}" if self._fields else ""
        return f"join={self._relation}{fields_str}"

    def body_build(self) -> Tuple[str, str]:
        fields_str = f"||{','.join(self._fields)}" if self._fields else ""
        return "join", f"{self._relation}{fields_str}"


class Limit(Query):
    def __init__(self, limit: int):
        super().__init__()
        self._limit = limit
        self.condition_set = [self]

    def build(self) -> str:
        raise NotImplementedError

    def body_build(self) -> Tuple[str, int]:
        return "limit", self._limit


class Offset(Query):
    def __init__(self, offset: int):
        super().__init__()
        self._offset = offset
        self.condition_set = [self]

    def build(self) -> str:
        raise NotImplementedError

    def body_build(self) -> Tuple[str, int]:
        return "offset", self._offset
