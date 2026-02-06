import logging
import typing
from typing import Callable, Awaitable

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

# noinspection PyProtectedMember
from opentelemetry._logs import get_logger_provider

# noinspection PyProtectedMember
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import get_current_span, StatusCode, get_tracer_provider
from pydantic import TypeAdapter
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


async def otel_handler(request: Request, call_next: Callable[..., Awaitable[Response]]):

    logging.warning(
        TypeAdapter(dict)
        .dump_json(
            {
                "headers": dict(request.headers),
                "path_params": request.path_params,
                "query_params": dict(request.query_params),
                "body": await request.body(),
            },
            indent=4,
        )
        .decode()
    )

    response = await call_next(request)

    if 600 > response.status_code >= 400:

        get_current_span().set_status(StatusCode.ERROR, "NO DESCRIPTION")

    if isinstance(get_tracer_provider(), TracerProvider):

        typing.cast(TracerProvider, get_tracer_provider()).force_flush()

    if isinstance(get_logger_provider(), LoggerProvider):

        typing.cast(LoggerProvider, get_logger_provider()).force_flush()

    return response


# noinspection PyTypeChecker

middlewares = [
    Middleware(
        CORSMiddleware,
        allow_origin_regex="|".join(
            [
                "https?://localhost:300[01]",
            ]
        ),
        allow_methods=["*"],
        allow_headers=["*"],
    ),
    Middleware(BaseHTTPMiddleware, dispatch=otel_handler),
]
