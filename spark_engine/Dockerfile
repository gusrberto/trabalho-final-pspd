# 1. Imagem base com Python
FROM python:3.10-bullseye

# 2. Instalar Java (necessário para o Spark) e utilitários
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      openjdk-11-jdk wget ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 3. Definir variáveis de ambiente para Spark e Python
ENV SPARK_VERSION=3.5.1 \
    SPARK_HOME=/opt/spark \
    PATH=/opt/spark/bin:/opt/spark/sbin:$PATH \
    PYSPARK_PYTHON=python3

WORKDIR /opt

# 4. Baixar Spark da versão arquivada
RUN wget https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz && \
    tar xzf spark-${SPARK_VERSION}-bin-hadoop3.tgz && \
    mv spark-${SPARK_VERSION}-bin-hadoop3 spark && \
    rm spark-${SPARK_VERSION}-bin-hadoop3.tgz

# 5. Copiar código da engine Spark
COPY game_of_life_spark.py /opt/spark/app/game_of_life_spark.py

# 6. Instalar dependências Python
COPY requirements.txt /opt/spark/app/requirements.txt
RUN pip install -r /opt/spark/app/requirements.txt

# 7. Definir diretório de trabalho
WORKDIR /opt/spark/app

# 8. Entrypoint padrão: executa localmente
ENTRYPOINT ["spark-submit", "--master", "local[*]", "game_of_life_spark.py"]
