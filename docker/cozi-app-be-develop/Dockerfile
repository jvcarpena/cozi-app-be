FROM python:3.12-slim

ENV PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml ./

RUN pip install -e .

COPY src/ ./src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
