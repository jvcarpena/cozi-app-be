import os


class CeleryConfig:
    broker_url = os.environ.get("RABBITMQ_URL", "amqp://cozi:cozi1234@rabbitmq:5672/")
    task_ignore_result = True
    task_serializer = "json"
    accept_content = ["json"]
    result_serializer = "json"
    task_acks_late = True
    worker_prefetch_multiplier = 1
    timezone = "UTC"
    enable_utc = True

    worker_cancel_long_running_tasks_on_connection_loss = True
