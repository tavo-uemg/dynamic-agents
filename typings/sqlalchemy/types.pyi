from __future__ import annotations

from typing import Any

class TypeDecorator:
    impl: Any
    cache_ok: bool

class CHAR:
    def __init__(self, length: int | None = ...) -> None: ...
