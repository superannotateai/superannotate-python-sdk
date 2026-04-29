from __future__ import annotations

from collections.abc import Callable
from collections.abc import Iterator
from typing import Generic
from typing import overload
from typing import TypeVar

T = TypeVar("T")


class BaseResult(Generic[T]):
    """A generic list-like wrapper for results with lazy loading support.

    This class wraps a list of results while maintaining full backward
    compatibility with list-like operations (iteration, indexing, len()).
    Data is fetched lazily on first access.
    """

    def __init__(self, data_fetcher: Callable[[], list[T]]) -> None:
        self._data: list[T] | None = None
        self._data_fetcher = data_fetcher

    def _ensure_data(self) -> list[T]:
        """Lazily fetch data if not already loaded."""
        if self._data is None:
            self._data = self._data_fetcher()
        return self._data

    def __iter__(self) -> Iterator[T]:
        return iter(self._ensure_data())

    def __len__(self) -> int:
        return len(self._ensure_data())

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> list[T]: ...

    def __getitem__(self, index: int | slice) -> T | list[T]:
        return self._ensure_data()[index]

    def __repr__(self) -> str:
        return repr(self._ensure_data())

    def __bool__(self) -> bool:
        return bool(self._ensure_data())

    def __contains__(self, item: T) -> bool:
        return item in self._ensure_data()


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
