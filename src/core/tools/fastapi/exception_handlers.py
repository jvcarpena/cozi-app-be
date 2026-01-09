import logging

from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import NoResultFound
from starlette.exceptions import HTTPException
from fastapi import Request
from starlette.responses import JSONResponse


async def custom_http_exception_handler(request: Request, exception: HTTPException):

    logging.exception(exception)

    return await http_exception_handler(request, exception)


async def custom_no_result_found_handler(_request: Request, exception: NoResultFound):

    logging.exception(exception)

    return JSONResponse({"detail": "No Results Found"}, status_code=404)


async def custom_request_validation_exception_handler(request: Request, exception: RequestValidationError):

    logging.exception(exception)

    return await request_validation_exception_handler(request, exception)


async def custom_exception_handler(_request: Request, exception: Exception):

    logging.exception(exception)

    return JSONResponse({"detail": "Internal Server Error"}, status_code=500)


exception_handlers = {
    HTTPException: custom_http_exception_handler,
    RequestValidationError: custom_request_validation_exception_handler,
    Exception: custom_exception_handler,
    NoResultFound: custom_no_result_found_handler,
}
