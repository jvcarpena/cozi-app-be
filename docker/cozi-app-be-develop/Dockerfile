FROM python:3.12-slim AS fastapi

ENV PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml ./

RUN pip install -e .

COPY src/ ./src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# FOR CELERY WORKER

FROM fastapi AS celery_worker

CMD ["celery", "-A", "core.tools.celery.celery_app", "worker", "--loglevel=info"]
