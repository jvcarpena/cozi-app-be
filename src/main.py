import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.asyncexitstack import AsyncExitStackMiddleware

# noinspection PyProtectedMember
from opentelemetry._logs import set_logger_provider

# noinspection PyProtectedMember
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# noinspection PyProtectedMember
from opentelemetry.sdk._logs import LoggerProvider

# noinspection PyProtectedMember
from opentelemetry.sdk._logs._internal.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_tracer_provider
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.types import ASGIApp

from core.tools.fastapi.auto_tag_routes import auto_tag_routes
from core.tools.fastapi.exception_handlers import exception_handlers
from core.tools.fastapi.middlewares import middlewares
from core.tools.opentelemetry.logging_handler import CustomLoggingHandler
from domains.guest.router import guest_router


class CustomFastApi(FastAPI):

    def build_middleware_stack(self) -> ASGIApp:

        # noinspection PyTypeChecker

        middleware = (
            [Middleware(ServerErrorMiddleware, debug=self.debug)]
            + self.user_middleware
            + [
                Middleware(ExceptionMiddleware, handlers=self.exception_handlers, debug=self.debug),
                Middleware(AsyncExitStackMiddleware),
            ]
        )

        asgi_app = self.router  # Request -> Router -> Response

        for cls, args, kwargs in reversed(middleware):

            asgi_app = cls(asgi_app, *args, **kwargs)

        return asgi_app


@asynccontextmanager
async def lifespan(_app: FastAPI):

    auto_tag_routes(_app)

    yield


app = CustomFastApi(
    root_path=f"/{os.environ.get("STAGE", "local")}/api/v1",
    middleware=middlewares,
    exception_handlers=exception_handlers,
    lifespan=lifespan,
)

# ROUTERS
app.include_router(guest_router)

resource = Resource.create(attributes={"service.name": "fastapi-app-cozi"})

# TEMPO

set_tracer_provider(tracer_provider := TracerProvider(resource=resource))

tracer_provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint="http://localhost:4317",
            insecure=True,
            timeout=3,
        )
    )
)

# LOKI

LoggingInstrumentor().instrument(set_logging_format=True)

set_logger_provider(logger_provider := LoggerProvider(resource=resource))

logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(OTLPLogExporter(endpoint="http://localhost:4318/v1/logs", timeout=3))
)

logging.getLogger().addHandler(CustomLoggingHandler(logger_provider=logger_provider))

# INSTRUMENT FastAPI

FastAPIInstrumentor.instrument_app(app, exclude_spans=["receive", "send"])


if __name__ == "__main__":

    uvicorn.run("main:app")
