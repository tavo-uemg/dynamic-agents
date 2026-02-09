from typing import Literal

class Response:
    status_code: int
    text: str

    def json(self) -> object: ...
    def raise_for_status(self) -> None: ...

class HTTPStatusError(Exception):
    response: Response

class RequestError(Exception): ...

class _Codes:
    UNAUTHORIZED: int
    NOT_FOUND: int
    TOO_MANY_REQUESTS: int

codes: _Codes

class AsyncClient:
    def __init__(
        self,
        *,
        base_url: str | None = ...,
        timeout: float | None = ...,
        verify: bool | str | None = ...,
        headers: dict[str, str] | None = ...,
    ) -> None: ...
    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = ...,
        headers: dict[str, str] | None = ...,
    ) -> Response: ...
    async def aclose(self) -> None: ...
