from typing import Any, TypeVar

ModelType = TypeVar("ModelType", bound="BaseModel")

class BaseModel:
    def __init__(self, **data: Any) -> None: ...
    @classmethod
    def model_validate(cls: type[ModelType], obj: Any, /) -> ModelType: ...

def Field(*args: Any, **kwargs: Any) -> Any: ...
