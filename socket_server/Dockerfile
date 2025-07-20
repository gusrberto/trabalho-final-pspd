# socket_engine/Dockerfile
FROM python:3.10

WORKDIR /app

COPY socket_server.py requirements.txt ./
COPY metrics_collector.py ./

RUN pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["python", "socket_server.py"]
