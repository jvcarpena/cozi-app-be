import logging

from core.services.send_email import SendEmailRequestDTO, send_email
from core.tools.celery.celery_app import celery


@celery.task(bind=True, max_retries=4, default_retry_delay=40)
def send_email_task(self, request_dto: dict):
    try:
        send_email(SendEmailRequestDTO(**request_dto))

    except Exception as e:
        logging.error(f"Failed to send email to {request_dto.get("to")}: {e}")
