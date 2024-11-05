FROM python:3.13.0-alpine3.20
LABEL maintainer="https://github.com/JoaoPedroCavalcanti"

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instala o bash e outras dependências necessárias
RUN apk add --no-cache bash

# Copia a pasta "myapp" e "scripts" para dentro do contêiner
COPY myapp /myapp
COPY scripts /scripts

# Define o diretório de trabalho
WORKDIR /myapp

# Exponha a porta
EXPOSE 8000

# Executa os comandos para preparar o ambiente e instalar as dependências globalmente
RUN pip install --upgrade pip && \
  pip install -r /myapp/requirements.txt && \
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
CMD ["commands.sh"]
