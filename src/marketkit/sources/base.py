from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class Source(Protocol):
    name: str
    requires_key: bool

    def fetch(self, ticker: str, start: Any, end: Any, interval: str) -> pd.DataFrame:
        """Return a RAW frame (any shape). The engine will normalize it.
        Raise RateLimited / SourceError on failure."""
        ...


_REGISTRY: dict[str, Source] = {}


def register(source: Source) -> None:
    _REGISTRY[source.name] = source


def get_source(name: str) -> Source:
    return _REGISTRY[name]
