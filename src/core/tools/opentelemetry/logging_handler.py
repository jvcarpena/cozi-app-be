import logging

from opentelemetry.attributes import BoundedAttributes

# noinspection PyProtectedMember
from opentelemetry.sdk._logs import LoggingHandler, LogRecord
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import get_current_span


class CustomLoggingHandler(LoggingHandler):

    def _translate(self, record: logging.LogRecord) -> LogRecord:

        log_record = super()._translate(record)

        current_span = get_current_span()

        if isinstance(log_record.attributes, BoundedAttributes) and isinstance(current_span, ReadableSpan):

            log_record.attributes["http.route"] = current_span.attributes.get("http.route")

        return log_record
