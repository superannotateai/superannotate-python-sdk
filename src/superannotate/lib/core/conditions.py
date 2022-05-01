from collections import namedtuple
from typing import Any
from typing import List
from typing import NamedTuple

CONDITION_OR = "|"
CONDITION_AND = "&"
CONDITION_EQ = "="
CONDITION_GT = ">"
CONDITION_GE = ">="
CONDITION_LT = "<"
CONDITION_LE = "<="


class EmptyCondition:
    def __or__(self, other):
        return other

    def __and__(self, other):
        return other

    def build_query(self):
        return ""


class Condition:
    def __init__(self, key: str, value: Any, condition_type: str):
        self._key = key
        self._value = value
        self._type = condition_type
        self._condition_set = []  # type: List[NamedTuple]

    @staticmethod
    def get_empty_condition():
        return EmptyCondition()

    def __str__(self):
        return f"{self._key}{self._type}{self._value}"

    def __or__(self, other):
        if not isinstance(other, Condition):
            raise Exception("Support the only Condition types")
        QueryCondition = namedtuple("QueryCondition", ("condition", "query"))
        self._condition_set.append(QueryCondition(CONDITION_OR, other.build_query()))
        return self

    def __and__(self, other):
        if isinstance(other, tuple) or isinstance(other, list):
            for elem in other:
                if isinstance(other, EmptyCondition):
                    continue
                if not isinstance(other, Condition):
                    raise Exception("Support the only Condition types")
                return self.__and__(elem)
        elif not isinstance(other, (Condition, EmptyCondition)):
            raise Exception("Support the only Condition types")
        QueryCondition = namedtuple("QueryCondition", ("condition", "query"))
        self._condition_set.append(QueryCondition(CONDITION_AND, other.build_query()))
        return self

    def build_query(self):
        return str(self) + "".join(
            [f"{condition[0]}{condition[1]}" for condition in self._condition_set]
        )
