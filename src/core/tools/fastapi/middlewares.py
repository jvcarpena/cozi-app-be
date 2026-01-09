import logging
from typing import Callable, Awaitable

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
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

    return response


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
