import os

import aio_pika

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://cozi:cozi1234@rabbitmq:5672/")

_connection: aio_pika.RobustConnection = None


async def get_connection() -> aio_pika.RobustConnection:
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(
            RABBITMQ_URL,
            reconnect_interval=5,
        )

    return _connection


async def close_connection():
    global _connection
    if _connection and not _connection.is_closed:
        await _connection.close()
