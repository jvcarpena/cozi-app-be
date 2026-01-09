import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.asyncexitstack import AsyncExitStackMiddleware
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.types import ASGIApp

from core.tools.fastapi.auto_tag_routes import auto_tag_routes
from core.tools.fastapi.exception_handlers import exception_handlers
from core.tools.fastapi.middlewares import middlewares


class CustomFastApi(FastAPI):

    def build_middleware_stack(self) -> ASGIApp:

        middleware = (
            [Middleware(ServerErrorMiddleware, debug=self.debug)]
            + self.user_middleware
            + [
                Middleware(ExceptionMiddleware, handlers=self.exception_handlers, debug=self.debug),
                Middleware(AsyncExitStackMiddleware),
            ]
        )

        asgi_app = self.router

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


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
