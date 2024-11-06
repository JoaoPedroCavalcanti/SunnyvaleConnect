FROM python:3.13.0-alpine3.20
LABEL maintainer="https://github.com/JoaoPedroCavalcanti"

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instala o bash, curl, gcc, e outras dependências necessárias
RUN apk add --no-cache bash curl gcc musl-dev postgresql-dev

# Instala o Poetry globalmente usando pip
RUN pip install poetry

# Configura o Poetry para instalar no ambiente global, evitando virtualenv
RUN poetry config virtualenvs.create false

# Define o diretório de trabalho na pasta 'myapp'
WORKDIR /myapp

# Copia o projeto e as dependências do Poetry para dentro do contêiner
COPY myapp /myapp
COPY scripts /scripts

# Exponha a porta
EXPOSE 8000

# Instala as dependências usando o Poetry
RUN poetry install --no-root --without dev && \
    adduser --disabled-password --no-create-home duser && \
    mkdir -p /data/web/static && \
    mkdir -p /data/web/media && \
    chown -R duser:duser /data/web/static && \
    chown -R duser:duser /data/web/media && \
    chmod -R 755 /data/web/static && \
    chmod -R 755 /data/web/media && \
    chmod -R +x /scripts

# Adiciona a pasta scripts ao $PATH do contêiner
ENV PATH="/scripts:$PATH"

# Muda o usuário para duser
USER duser

# Executa o arquivo scripts/commands.sh
CMD ["sh", "-c", "/scripts/commands.sh"]