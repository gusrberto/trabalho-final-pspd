FROM python:3.9-slim

WORKDIR /app

# Instalar dependências
RUN pip install flask requests

# Copiar arquivos do ConfigMap (serão montados via volume)
COPY . .

EXPOSE 8080

CMD ["python", "metrics_api_server.py"] 