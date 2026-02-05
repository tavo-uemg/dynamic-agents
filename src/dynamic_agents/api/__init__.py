"""REST API module exports."""

from collections.abc import Callable

from fastapi import FastAPI

from .app import create_app as _create_app

create_app: Callable[[], FastAPI] = _create_app

__all__ = ["create_app"]
