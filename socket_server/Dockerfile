# socket_engine/Dockerfile
FROM python:3.10

WORKDIR /app

COPY socket_server.py requirements.txt ./

RUN pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["python", "socket_server.py"]
