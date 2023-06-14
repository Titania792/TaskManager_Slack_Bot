# Imagen base de Python
FROM python:3.9-alpine

# Copiamos el archivo requirements.txt y la carpeta ./app dentro del contenedor
COPY ./requirements.txt /tmp/requirements.txt
COPY ./app /app
# Establecemos /app como el directorio de trabajo actual
WORKDIR /app

# Instalamos las dependencias necesarias para compilar e instalar algunos paquetes de Python
RUN apk add gcc musl-dev python3-dev libffi-dev

# Actualizamos pip y luego instalamos las dependencias del proyecto desde /tmp/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm -rf /tmp/requirements.txt
