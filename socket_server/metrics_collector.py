import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self, elasticsearch_url: str = "http://localhost:9200"):
        self.elasticsearch_url = elasticsearch_url
        self.index_name = "game_of_life_metrics"
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Inicializar índice se não existir
        self._create_index_if_not_exists()
    
    def _create_index_if_not_exists(self):
        """Cria o índice no ElasticSearch se não existir"""
        try:
            # Verificar se o índice existe
            response = self.session.head(f"{self.elasticsearch_url}/{self.index_name}")
            if response.status_code == 404:
                # Criar índice com mapping
                mapping = {
                    "mappings": {
                        "properties": {
                            "timestamp": {"type": "date"},
                            "client_id": {"type": "keyword"},
                            "engine_type": {"type": "keyword"},
                            "execution_time_ms": {"type": "long"},
                            "status": {"type": "keyword"},
                            "grid_size": {"type": "integer"},
                            "iterations": {"type": "integer"},
                            "total_requests": {"type": "long"},
                            "concurrent_clients": {"type": "integer"},
                            "request_type": {"type": "keyword"}
                        }
                    }
                }
                
                response = self.session.put(
                    f"{self.elasticsearch_url}/{self.index_name}",
                    json=mapping
                )
                
                if response.status_code == 200:
                    logger.info(f"Índice {self.index_name} criado com sucesso")
                else:
                    logger.error(f"Erro ao criar índice: {response.text}")
            else:
                logger.info(f"Índice {self.index_name} já existe")
                
        except Exception as e:
            logger.error(f"Erro ao verificar/criar índice: {e}")
    
    def record_job_start(self, client_id: str, engine_type: str, grid_size: int, iterations: int):
        """Registra o início de um job"""
        try:
            doc = {
                "timestamp": datetime.utcnow().isoformat(),
                "client_id": client_id,
                "engine_type": engine_type,
                "status": "started",
                "grid_size": grid_size,
                "iterations": iterations,
                "request_type": "job_start"
            }
            
            response = self.session.post(
                f"{self.elasticsearch_url}/{self.index_name}/_doc",
                json=doc
            )
            
            if response.status_code == 201:
                logger.info(f"Job iniciado registrado: {client_id} - {engine_type}")
            else:
                logger.error(f"Erro ao registrar início do job: {response.text}")
                
        except Exception as e:
            logger.error(f"Erro ao registrar início do job: {e}")
    
    def record_job_completion(self, client_id: str, engine_type: str, execution_time_ms: int, 
                            status: str = "completed", grid_size: int = None, iterations: int = None):
        """Registra a conclusão de um job"""
        try:
            doc = {
                "timestamp": datetime.utcnow().isoformat(),
                "client_id": client_id,
                "engine_type": engine_type,
                "execution_time_ms": execution_time_ms,
                "status": status,
                "request_type": "job_completion"
            }
            
            if grid_size:
                doc["grid_size"] = grid_size
            if iterations:
                doc["iterations"] = iterations
            
            response = self.session.post(
                f"{self.elasticsearch_url}/{self.index_name}/_doc",
                json=doc
            )
            
            if response.status_code == 201:
                logger.info(f"Job completado registrado: {client_id} - {engine_type} - {execution_time_ms}ms")
            else:
                logger.error(f"Erro ao registrar conclusão do job: {response.text}")
                
        except Exception as e:
            logger.error(f"Erro ao registrar conclusão do job: {e}")
    
    def record_client_connection(self, client_id: str):
        """Registra conexão de um cliente"""
        try:
            doc = {
                "timestamp": datetime.utcnow().isoformat(),
                "client_id": client_id,
                "request_type": "client_connection"
            }
            
            response = self.session.post(
                f"{self.elasticsearch_url}/{self.index_name}/_doc",
                json=doc
            )
            
            if response.status_code == 201:
                logger.info(f"Conexão de cliente registrada: {client_id}")
            else:
                logger.error(f"Erro ao registrar conexão: {response.text}")
                
        except Exception as e:
            logger.error(f"Erro ao registrar conexão: {e}")
    
    def record_client_disconnection(self, client_id: str):
        """Registra desconexão de um cliente"""
        try:
            doc = {
                "timestamp": datetime.utcnow().isoformat(),
                "client_id": client_id,
                "request_type": "client_disconnection"
            }
            
            response = self.session.post(
                f"{self.elasticsearch_url}/{self.index_name}/_doc",
                json=doc
            )
            
            if response.status_code == 201:
                logger.info(f"Desconexão de cliente registrada: {client_id}")
            else:
                logger.error(f"Erro ao registrar desconexão: {response.text}")
                
        except Exception as e:
            logger.error(f"Erro ao registrar desconexão: {e}")
    
    def get_metrics_summary(self, time_range_hours: int = 24) -> Dict:
        """Obtém resumo das métricas das últimas N horas"""
        try:
            # Calcular timestamp de início
            start_time = datetime.utcnow() - timedelta(hours=time_range_hours)
            
            # Query para métricas gerais
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"range": {"timestamp": {"gte": start_time.isoformat()}}},
                            {"terms": {"request_type": ["job_completion", "client_connection"]}}
                        ]
                    }
                },
                "aggs": {
                    "total_jobs": {
                        "filter": {"term": {"request_type": "job_completion"}},
                        "aggs": {
                            "avg_execution_time": {"avg": {"field": "execution_time_ms"}},
                            "success_rate": {
                                "filter": {"term": {"status": "completed"}}
                            }
                        }
                    },
                    "engine_distribution": {
                        "filter": {"term": {"request_type": "job_completion"}},
                        "aggs": {
                            "engines": {"terms": {"field": "engine_type"}}
                        }
                    },
                    "execution_times": {
                        "filter": {"term": {"request_type": "job_completion"}},
                        "aggs": {
                            "times": {
                                "date_histogram": {
                                    "field": "timestamp",
                                    "calendar_interval": "1h"
                                },
                                "aggs": {
                                    "avg_time": {"avg": {"field": "execution_time_ms"}}
                                }
                            }
                        }
                    },
                    "concurrent_clients": {
                        "filter": {"term": {"request_type": "client_connection"}},
                        "aggs": {
                            "clients": {
                                "date_histogram": {
                                    "field": "timestamp",
                                    "calendar_interval": "1h"
                                },
                                "aggs": {
                                    "unique_clients": {"cardinality": {"field": "client_id"}}
                                }
                            }
                        }
                    }
                }
            }
            
            response = self.session.post(
                f"{self.elasticsearch_url}/{self.index_name}/_search",
                json=query
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._process_metrics_result(result)
            else:
                logger.error(f"Erro ao buscar métricas: {response.text}")
                return self._get_default_metrics()
                
        except Exception as e:
            logger.error(f"Erro ao obter métricas: {e}")
            return self._get_default_metrics()
    
    def _process_metrics_result(self, result: Dict) -> Dict:
        """Processa o resultado da query do ElasticSearch"""
        try:
            aggs = result.get("aggregations", {})
            
            # Total de jobs
            total_jobs_bucket = aggs.get("total_jobs", {})
            total_jobs = total_jobs_bucket.get("doc_count", 0)
            
            # Tempo médio de execução
            avg_execution_time = total_jobs_bucket.get("avg_execution_time", {}).get("value", 0)
            
            # Taxa de sucesso
            success_bucket = total_jobs_bucket.get("success_rate", {})
            success_count = success_bucket.get("doc_count", 0)
            success_rate = success_count / total_jobs if total_jobs > 0 else 0
            
            # Distribuição por engine
            engine_dist = aggs.get("engine_distribution", {}).get("engines", {}).get("buckets", [])
            engines = [bucket["key"] for bucket in engine_dist]
            engine_counts = [bucket["doc_count"] for bucket in engine_dist]
            
            # Tempos de execução ao longo do tempo
            execution_times_bucket = aggs.get("execution_times", {}).get("times", {}).get("buckets", [])
            time_labels = []
            execution_times = []
            
            for bucket in execution_times_bucket:
                time_labels.append(bucket["key_as_string"][:16])  # Formato: YYYY-MM-DDTHH:MM
                execution_times.append(bucket["avg_time"]["value"] or 0)
            
            # Clientes simultâneos
            concurrent_clients_bucket = aggs.get("concurrent_clients", {}).get("clients", {}).get("buckets", [])
            concurrent_clients = []
            for bucket in concurrent_clients_bucket:
                concurrent_clients.append(bucket["unique_clients"]["value"] or 0)
            
            return {
                "total_jobs": total_jobs,
                "avg_execution_time": round(avg_execution_time, 2),
                "success_rate": round(success_rate, 2),
                "engines": engines,
                "engine_counts": engine_counts,
                "execution_times": execution_times,
                "time_labels": time_labels,
                "concurrent_clients": concurrent_clients
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar métricas: {e}")
            return self._get_default_metrics()
    
    def _get_default_metrics(self) -> Dict:
        """Retorna métricas padrão quando não há dados"""
        return {
            "total_jobs": 0,
            "avg_execution_time": 0,
            "success_rate": 0,
            "engines": ["Spark", "OpenMP", "MPI"],
            "engine_counts": [0, 0, 0],
            "execution_times": [],
            "time_labels": [],
            "concurrent_clients": []
        }
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict]:
        """Obtém atividades recentes"""
        try:
            query = {
                "query": {"match_all": {}},
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": limit
            }
            
            response = self.session.post(
                f"{self.elasticsearch_url}/{self.index_name}/_search",
                json=query
            )
            
            if response.status_code == 200:
                result = response.json()
                hits = result.get("hits", {}).get("hits", [])
                return [hit["_source"] for hit in hits]
            else:
                logger.error(f"Erro ao buscar atividades recentes: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao obter atividades recentes: {e}")
            return []

# Instância global do coletor
metrics_collector = MetricsCollector() 