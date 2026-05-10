FROM python:3.12-slim AS fastapi

ENV PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml ./

RUN pip install -e .

COPY src/ ./src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# FOR EMAIL CONSUMER

FROM fastapi AS email_consumer

CMD ["python", "src/core/tools/rabbitmq/consumers/email_consumer.py"]
