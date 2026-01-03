from datetime import datetime, timedelta
from typing import Optional, Any
from zoneinfo import ZoneInfo

from sqlalchemy import TypeDecorator, DateTime, Dialect


class UTCDateTime(TypeDecorator):
    """Custom SQLAlchemy type to enforce UTC datetime storage and retrieval."""

    impl = DateTime

    cache_ok = True

    def process_bind_param(self, value: Optional[Any], dialect: Dialect) -> Any:
        """Called when saving a value to the database. Ensuring the value is in UTC aware datetime"""

        if value is None:
            return value

        assert isinstance(value, datetime)

        assert value.utcoffset() == timedelta(seconds=0)

        return value

    def process_result_value(self, value: Optional[Any], dialect: Dialect) -> Optional[Any]:
        """Called when loading a value from the database. Ensuring the data from db is utc aware datetime"""

        return value.replace(tzinfo=ZoneInfo("UTC")) if isinstance(value, datetime) else value
