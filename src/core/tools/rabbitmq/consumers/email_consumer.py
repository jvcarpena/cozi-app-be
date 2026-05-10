import asyncio
import json
import logging
import os

from aio_pika.abc import AbstractIncomingMessage

from core.services.send_email import send_email, SendEmailRequestDTO
from core.tools.rabbitmq.connection_service import get_connection

QUEUE_NAME = os.environ.get("EMAIL_NOTIF_QUEUE", "email_notif_queue_develop")


async def on_message(message: AbstractIncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body)

            send_email(
                SendEmailRequestDTO(
                    to=data["to"],
                    sender=data["sender"] if data["sender"] else None,
                    subject=data["subject"],
                    template_name=data["template_name"],
                    html_substitutions=data["html_substitutions"] if data["html_substitutions"] else None,
                )
            )
        except Exception as e:
            logging.error(f"Failed to process message: {e}")
            raise


async def start_email_consumer():
    connection = await get_connection()
    channel = await connection.channel()

    await channel.set_qos(prefetch_count=10)

    queue = await channel.declare_queue(QUEUE_NAME, durable=True)

    await queue.consume(on_message)

    logging.info(f"Consumer listening on queue: {QUEUE_NAME}")

    await asyncio.Future()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_email_consumer())
