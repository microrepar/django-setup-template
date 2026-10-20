# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

# Variáveis de ambiente para otimizar o comportamento do Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Definir locale
ENV LANG=pt_BR.UTF-8
ENV LANGUAGE=pt_BR:pt
ENV LC_ALL=pt_BR.UTF-8

# Atualiza pacotes do sistema e instala o cliente do PostgreSQL, curl e locales;
# gera pt_BR.UTF-8 para que os ENV de locale acima existam de fato (sem isso o
# bash emite "setlocale: LC_ALL: cannot change locale" ao iniciar)
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client curl locales && \
    sed -i '/pt_BR.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Baixar Tailwind CSS CLI v4 para Linux e VERIFICAR a integridade (sha256 pinado)
RUN curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.18/tailwindcss-linux-x64 && \
    echo "737becf8d4ad1115ea98df69fa94026d402ca8feb91306a035b5b004167da8dd  tailwindcss-linux-x64" | sha256sum -c - && \
    mv tailwindcss-linux-x64 /usr/local/bin/tailwindcss && \
    chmod +x /usr/local/bin/tailwindcss

# Definir diretório de trabalho
WORKDIR /code

# Copiar e instalar dependências do projeto
COPY requirements.txt /code/
RUN pip install -U pip
RUN pip install -r requirements.txt

# Copiar o resto do código da aplicação
COPY . /code/

# Build Tailwind CSS no container
RUN tailwindcss -i /code/core/static/core/css/input.css -o /code/core/static/core/css/output.css --minify

# Estagio de testes: dependencias de dev (pytest etc.) sobre a base
FROM base AS dev
COPY requirements-dev.txt /code/
RUN pip install -r requirements-dev.txt

# Estagio final (default do build): producao, sem dependencias de dev
FROM base AS production
