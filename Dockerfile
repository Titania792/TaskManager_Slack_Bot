# Imagen base de Python
FROM python:3.9-alpine

COPY ./requirements.txt /tmp/requirements.txt
COPY ./app /app
WORKDIR /app

RUN apk add gcc musl-dev python3-dev libffi-dev

RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm -rf /tmp/requirements.txt