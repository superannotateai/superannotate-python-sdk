from __future__ import annotations

from collections.abc import Callable
from collections.abc import Iterator
from typing import Generic
from typing import overload
from typing import TypeVar

T = TypeVar("T")


class BaseResult(list, Generic[T]):
    """A generic list-like wrapper for results with lazy loading support.

    Inherits from ``list`` for full backward compatibility with code that
    expects a real list (``isinstance(x, list)``, JSON serializers, etc.).
    Data is fetched lazily on first access.
    """

    def __init__(self, data_fetcher: Callable[[], list[T]]) -> None:
        super().__init__()
        self._data_fetcher = data_fetcher
        self._loaded = False

    def _ensure_data(self) -> None:
        """Lazily fetch data if not already loaded."""
        if not self._loaded:
            list.extend(self, self._data_fetcher())
            self._loaded = True

    def data(self) -> list[T]:
        self._ensure_data()
        return list(self)

    def __iter__(self) -> Iterator[T]:
        self._ensure_data()
        return list.__iter__(self)

    def __len__(self) -> int:
        self._ensure_data()
        return list.__len__(self)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> list[T]: ...

    def __getitem__(self, index: int | slice) -> T | list[T]:
        self._ensure_data()
        return list.__getitem__(self, index)

    def __repr__(self) -> str:
        self._ensure_data()
        return list.__repr__(self)

    def __bool__(self) -> bool:
        self._ensure_data()
        return list.__len__(self) > 0

    def __contains__(self, item: object) -> bool:
        self._ensure_data()
        return list.__contains__(self, item)

    def __eq__(self, other: object) -> bool:
        self._ensure_data()
        return list.__eq__(self, other)

    __hash__ = None  # type: ignore[assignment]


class QueryResult(BaseResult[dict]):
    """A list-like wrapper for query results that supports .count() method.

    This class wraps a list of query results while maintaining full backward
    compatibility with list-like operations (iteration, indexing, len()).
    Data is fetched lazily - only when accessed. Calling .count() does not
    trigger data fetching.
    """

    def __init__(
        self,
        data_fetcher: Callable[[], list[dict]],
        count_fetcher: Callable[[], int],
    ) -> None:
        super().__init__(data_fetcher)
        self._count_fetcher = count_fetcher

    def count(self) -> int:
        """Return the count of items matching the query from the server.

        This method does not trigger data fetching - it makes a separate
        lightweight API call to get only the count.
        """
        return self._count_fetcher()
