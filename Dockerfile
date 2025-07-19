FROM python:3.12-slim-bookworm

WORKDIR /app

# Установка системных зависимостей для PostgreSQL
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED 1

COPY pyproject.toml uv.lock ./

RUN pip install uv
RUN uv sync
