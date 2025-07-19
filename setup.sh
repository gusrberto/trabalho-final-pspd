#!/bin/bash

set -e

echo " Configurando o Joga da Vida Distribuído com ElasticSearch"

# Verificar se k3d está instalado
if ! command -v k3d &> /dev/null; then
    echo "k3d não está instalado. Instale em: https://k3d.io/"
    exit 1
fi

# Verificar se kubectl está instalado
if ! command -v kubectl &> /dev/null; then
    echo " kubectl não está instalado. Instale em: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Verificar se Docker está rodando
if ! docker info &> /dev/null; then
    echo "Docker não está rodando. Inicie o Docker e tente novamente."
    exit 1
fi

echo " Pré-requisitos verificados"

# Criar cluster k3d se não existir
if ! k3d cluster list | grep -q "life-game-cluster"; then
    echo "Criando cluster k3d..."
    k3d cluster create life-game-cluster \
        --servers-memory 4G \
        --agents 2 \
        --agents-memory 4G \
        --api-port 6443
else
    echo "Cluster k3d já existe"
fi

# Build das imagens Docker
echo "Build das imagens Docker..."

echo "Building socket-server..."
docker build -t socket-server:latest ./socket_server

echo "Building spark-engine..."
docker build -t life-spark:latest ./spark_engine

# Importar imagens para o cluster
echo "Importando imagens para o cluster..."
k3d image import socket-server:latest -c life-game-cluster
k3d image import life-spark:latest -c life-game-cluster

# Criar namespaces
echo "Criando namespaces..."
kubectl create namespace spark --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace elasticsearch --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace dashboard --dry-run=client -o yaml | kubectl apply -f -

# Aplicar configurações Kubernetes
echo "Aplicando configurações Kubernetes..."

echo "Aplicando configurações do socket server..."
kubectl apply -f k8s/socket_server_sa.yaml
kubectl apply -f k8s/role_pod_reader.yaml
kubectl apply -f k8s/rolebinding_pod_reader.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/socket_server.yaml

echo "Aplicando configurações do ElasticSearch..."
kubectl apply -f k8s/elasticsearch.yaml

echo "Aplicando configurações do Dashboard..."
kubectl apply -f k8s/dashboard.yaml

# Aguardar ElasticSearch estar pronto
echo "Aguardando ElasticSearch estar pronto..."
kubectl wait --for=condition=ready pod -l app=elasticsearch -n elasticsearch --timeout=300s

# Aguardar socket server estar pronto
echo "Aguardando socket server estar pronto..."
kubectl wait --for=condition=ready pod -l app=socket-server --timeout=300s

# Aguardar dashboard estar pronto
echo "Aguardando dashboard estar pronto..."
kubectl wait --for=condition=ready pod -l app=metrics-dashboard -n dashboard --timeout=300s

echo "Setup concluído!"

# Mostrar informações de acesso
echo ""
echo "Informações de Acesso:"
echo ""

# Obter porta do socket server
SOCKET_PORT=$(kubectl get service socket-server -o jsonpath='{.spec.ports[0].nodePort}')
echo "Socket Server: localhost:$SOCKET_PORT"

# Obter porta do dashboard
DASHBOARD_PORT=$(kubectl get service metrics-dashboard -n dashboard -o jsonpath='{.spec.ports[0].nodePort}')
echo "Dashboard: http://localhost:$DASHBOARD_PORT"

# Obter porta do ElasticSearch
ES_PORT=$(kubectl get service elasticsearch -n elasticsearch -o jsonpath='{.spec.ports[0].nodePort}')
echo "🔍 ElasticSearch: http://localhost:$ES_PORT"

echo ""
echo "Teste o sistema:"
echo "echo '3,4' | nc localhost:$SOCKET_PORT"
echo ""
echo "Visualize métricas:"
echo "open http://localhost:$DASHBOARD_PORT"
echo ""

# Configurar port forwarding
echo " Configurando port forwarding..."
kubectl port-forward deployment/socket-server 5000:5000 &
SOCKET_PID=$!

kubectl port-forward deployment/metrics-dashboard -n dashboard 8080:8080 &
DASHBOARD_PID=$!

kubectl port-forward deployment/metrics-dashboard -n dashboard 5001:5001 &
API_PID=$!

echo "Port forwarding configurado"
echo "Pressione Ctrl+C para parar"

# Função de cleanup
cleanup() {
    echo ""
    echo "Parando port forwarding..."
    kill $SOCKET_PID $DASHBOARD_PID $API_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Manter script rodando
while true; do
    sleep 1
done 