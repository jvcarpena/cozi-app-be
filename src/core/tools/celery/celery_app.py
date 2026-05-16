import os

from celery import Celery

from core.tools.celery.celery_config import CeleryConfig

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://cozi:cozi1234@rabbitmq:5672/")


celery = Celery(
    "cozi_app",
    broker=RABBITMQ_URL,
    include=["core.tools.celery.tasks.email_task"],
)

celery.config_from_object(CeleryConfig)
