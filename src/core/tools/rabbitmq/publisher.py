import json

import aio_pika

from core.tools.rabbitmq.connection_service import get_connection


async def publish_message(event: dict, queue_name: str):
    connection = await get_connection()
    channel = await connection.channel()

    queue = await channel.declare_queue(queue_name, durable=True)

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(event).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        ),
        routing_key=queue.name,
    )

    await channel.close()
