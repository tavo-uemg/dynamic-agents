from typing import Any, Protocol

class BaseSettings:
    model_config: Any

    def __init__(self, **data: Any) -> None: ...

class SettingsConfigDict(Protocol): ...
