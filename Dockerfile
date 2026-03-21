FROM python:3.12-slim

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    unzip \
    wget \
    ca-certificates \
    openjdk-17-jre \
    procps \
    iproute2 \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Copia os arquivos externos, incluindo o zip do GAMA
COPY external-libs /external-libs

# Descompacta o GAMA
RUN mkdir -p /opt/gama && \
    unzip -o /external-libs/GAMA_1.9.2_Linux_with_JDK.zip -d /opt/gama

# Ajusta permissões
RUN chmod +x /opt/gama/GAMA_1.9.2_Linux_with_JDK/headless/gama-headless.sh

# Script de inicialização
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 6868

CMD ["/docker-entrypoint.sh"]