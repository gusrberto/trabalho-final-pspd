# Implementação do ElasticSearch no Game of Life Distribuído

## Visão Geral

Este documento descreve a implementação do sistema de métricas baseado em ElasticSearch para o projeto Game of Life Distribuído. O sistema coleta métricas de processamento dos engines (Spark, OpenMP, MPI) e fornece visualizações através de um dashboard web.

## Arquitetura do Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Socket Client │    │  Socket Server  │    │  Spark Engine   │
│                 │───▶│                 │───▶│                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Metrics Collector│
                       │                 │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  ElasticSearch  │
                       │                 │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Metrics API    │    │    Dashboard    │
                       │                 │───▶│                 │
                       └─────────────────┘    └─────────────────┘
```

## Componentes Implementados

### 1. ElasticSearch Cluster
- **Arquivo**: `k8s/elasticsearch.yaml`
- **Configuração**: StatefulSet com 1 réplica
- **Recursos**: 1 CPU, 2GB RAM
- **Persistência**: Volume temporário (emptyDir)
- **Segurança**: Desabilitada para simplicidade

### 2. Metrics Collector
- **Arquivo**: `metrics_collector.py`
- **Função**: Coleta métricas dos engines
- **Métricas coletadas**:
  - Tempo de execução
  - Tipo de engine
  - Status do job
  - Tamanho da entrada/saída
  - Uso de recursos
  - Número de iterações

### 3. Dashboard Web
- **Arquivo**: `k8s/dashboard.yaml`
- **Tecnologia**: HTML + JavaScript + Chart.js
- **Visualizações**:
  - Gráfico de pizza por engine
  - Gráfico de linha de tempo de execução
  - Resumo estatístico
  - Métricas detalhadas

### 4. API de Métricas
- **Arquivo**: `metrics_api_server.py`
- **Framework**: Flask
- **Endpoints**:
  - `/api/metrics`: Métricas gerais
  - `/api/metrics/detailed`: Métricas detalhadas
  - `/health`: Health check

## Integração com Engines Existentes

### Socket Server Modificado
- **Arquivo**: `socket_server/socket_server.py`
- **Modificações**:
  - Importação do `metrics_collector`
  - Registro de início de job
  - Registro de conclusão de job
  - Coleta de métricas de execução

### Estrutura de Dados no ElasticSearch

```json
{
  "timestamp": "2025-07-18T18:30:00Z",
  "job_id": "1731865800",
  "engine_type": "spark",
  "status": "completed",
  "execution_time_ms": 1500,
  "output_size": 5,
  "input_params": {
    "powmin": 3,
    "powmax": 4
  },
  "iterations": 1,
  "memory_usage_mb": 512.5,
  "cpu_usage_percent": 75.2,
  "nodes_used": 2
}
```

## Configuração Kubernetes

### Namespaces
- `elasticsearch`: Para o cluster ElasticSearch
- `dashboard`: Para o dashboard e API de métricas
- `spark`: Para os jobs Spark (existente)

### Services
- `elasticsearch`: ClusterIP na porta 9200
- `metrics-dashboard`: NodePort para acesso externo
- `socket-server`: NodePort para acesso externo

## Scripts de Automação

### Setup Automático
- **Arquivo**: `setup.sh`
- **Função**: Configuração completa do sistema
- **Inclui**:
  - Verificação de pré-requisitos
  - Criação do cluster k3d
  - Build das imagens Docker
  - Aplicação das configurações Kubernetes
  - Configuração de port forwarding

### Teste do Sistema
- **Arquivo**: `test_system.py`
- **Função**: Verificação de todos os componentes
- **Testes**:
  - Conectividade Kubernetes
  - ElasticSearch
  - Socket Server
  - Dashboard
  - API de Métricas
  - Game of Life

## Métricas Coletadas

### Por Job
- **Identificação**: job_id único
- **Tempo**: timestamp de início e fim
- **Engine**: tipo (spark, openmp, mpi)
- **Parâmetros**: powmin, powmax
- **Resultado**: células vivas finais
- **Status**: completed, failed, started

### Por Execução
- **Duração**: tempo total em milissegundos
- **Recursos**: CPU, memória utilizados
- **Escalabilidade**: número de nós utilizados
- **Eficiência**: tamanho da entrada vs saída

## Visualizações Disponíveis

### Dashboard Principal
1. **Resumo Estatístico**
   - Total de jobs executados
   - Tempo médio de execução
   - Taxa de sucesso

2. **Distribuição por Engine**
   - Gráfico de pizza
   - Contagem por tipo de engine

3. **Tempo de Execução**
   - Gráfico de linha temporal
   - Média por hora

### API de Métricas
- **Endpoint**: `/api/metrics`
- **Formato**: JSON
- **Dados**: Agregações do ElasticSearch

## Próximos Passos

### Para Engines OpenMP/MPI
1. **Integração**: Adicionar `metrics_collector` aos engines
2. **Configuração**: Criar imagens Docker para OpenMP/MPI
3. **Kubernetes**: Configurar deployments para novos engines
4. **Métricas**: Coletar métricas específicas de cada engine

### Melhorias do Sistema
1. **Persistência**: Configurar PersistentVolume para ElasticSearch
2. **Segurança**: Habilitar autenticação no ElasticSearch
3. **Escalabilidade**: Configurar múltiplos nós ElasticSearch
4. **Alertas**: Implementar sistema de alertas baseado em métricas
5. **Backup**: Configurar backup automático das métricas

## Comandos Úteis

### Verificar Status
```bash
# Status dos pods
kubectl get pods --all-namespaces

# Logs do ElasticSearch
kubectl logs -n elasticsearch deployment/elasticsearch

# Logs do socket server
kubectl logs deployment/socket-server

# Status dos serviços
kubectl get services --all-namespaces
```

### Acessar Serviços
```bash
# Port forwarding
kubectl port-forward deployment/socket-server 5000:5000
kubectl port-forward deployment/metrics-dashboard -n dashboard 8080:8080
kubectl port-forward deployment/metrics-dashboard -n dashboard 5001:5001

# Testar Game of Life
echo "3,4" | nc localhost 5000

# Acessar dashboard
open http://localhost:8080
```

### Consultar ElasticSearch
```bash
# Health check
curl http://localhost:9200/_cluster/health

# Buscar métricas
curl -X POST "http://localhost:9200/game-of-life-metrics/_search" \
  -H "Content-Type: application/json" \
  -d '{"query":{"match_all":{}}}'
```

## Conclusão

A implementação do ElasticSearch fornece uma base sólida para coleta e visualização de métricas de processamento. O sistema está preparado para expansão com novos engines (OpenMP/MPI) e pode ser facilmente estendido com funcionalidades adicionais como alertas, backup e análise avançada de performance. 