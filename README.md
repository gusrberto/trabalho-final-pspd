# Game of Life Distribuído com Spark e Kubernetes

Este projeto implementa uma versão distribuída do Game of Life utilizando Apache Spark rodando em um cluster Kubernetes. A comunicação entre cliente e servidor é feita via socket TCP, e os jobs Spark são criados dinamicamente com acesso ao Kubernetes API.

## Estrutura do Projeto
```
.
├── k8s
│   ├── rolebinding_pod_reader.yaml
│   ├── role_pod_reader.yaml
│   ├── serviceaccount.yaml
│   ├── socket_server_sa.yaml
│   └── socket_server.yaml
├── README.md
├── socket_server
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── socket_client.py
│   └── socket_server.py
└── spark_engine
    ├── Dockerfile
    ├── game_of_life_spark.py
    └── requirements.txt
```

## Pré-requisitos

- Docker
- k3d
- kubectl
- Python 3.8+
- `nc` (netcat) para enviar comandos ao socket

## Subindo o projeto

### 1.1 Build das Imagens Docker
```bash
docker build -t socket-server:latest ./socket_server

docker build -t life-spark:latest ./spark_engine
```

### 1.2 Criar o cluster com `k3d`

```bash
k3d cluster create life-game-cluster \
  --servers-memory 4G \
  --agents 2 \
  --agents-memory 4G \
  --api-port 6443
```

### 1.3 Import das imagens para o cluster K3D
```bash
k3d image import socket-server:latest -c life-game-cluster

k3d image import spark-engine:latest -c life-game-cluster
```

### 2. Criar o namespace spark
```bash
kubectl create namespace spark
```

### 3. Aplicar as configurações do Kubernetes
```bash
kubectl apply -f k8s/
```

### 4. Port forwarding para o socket
```bash
kubectl port-forward deployment/socket-server
```

### 5. Netcat para realizar requisição para Socket Server
```bash
echo "3,4" | nc localhost 5000
```