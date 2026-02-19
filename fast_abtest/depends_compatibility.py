import contextvars
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import Request, FastAPI

if not TYPE_CHECKING:
    Request = Any
    FastAPI = Any

request_ctx: contextvars.ContextVar["Request"] = contextvars.ContextVar("request")


async def _set_request_context(request: "Request", call_next):
    request_ctx.set(request)
    response = await call_next(request)
    return response


def enable_dependency_support(
    app: "FastAPI",
) -> None:
    try:
        from fastapi import FastAPI
    except ImportError:
        raise ImportError("FastAPI integration requires 'fastapi'. Install it with: pip install fast-abtest[fastapi]")
    app.middleware("http")(_set_request_context)
