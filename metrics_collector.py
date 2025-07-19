import time
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional
import threading
import logging

class MetricsCollector:
    def __init__(self, elasticsearch_url: str = "http://elasticsearch.elasticsearch.svc.cluster.local:9200"):
        self.elasticsearch_url = elasticsearch_url
        self.index_name = "game-of-life-metrics"
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Inicializar índice se não existir
        self._ensure_index_exists()
    
    def _ensure_index_exists(self):
        """Garante que o índice existe no ElasticSearch"""
        try:
            # Verificar se o índice existe
            response = self.session.head(f"{self.elasticsearch_url}/{self.index_name}")
            if response.status_code != 200:
                # Criar índice com mapping
                mapping = {
                    "mappings": {
                        "properties": {
                            "timestamp": {"type": "date"},
                            "engine_type": {"type": "keyword"},
                            "job_id": {"type": "keyword"},
                            "execution_time_ms": {"type": "long"},
                            "input_size": {"type": "integer"},
                            "output_size": {"type": "integer"},
                            "status": {"type": "keyword"},
                            "error_message": {"type": "text"},
                            "memory_usage_mb": {"type": "float"},
                            "cpu_usage_percent": {"type": "float"},
                            "nodes_used": {"type": "integer"},
                            "iterations": {"type": "integer"}
                        }
                    }
                }
                response = self.session.put(
                    f"{self.elasticsearch_url}/{self.index_name}",
                    json=mapping
                )
                if response.status_code == 200:
                    self.logger.info(f"Índice {self.index_name} criado com sucesso")
                else:
                    self.logger.error(f"Erro ao criar índice: {response.text}")
        except Exception as e:
            self.logger.error(f"Erro ao verificar/criar índice: {e}")
    
    def record_metric(self, metric_data: Dict[str, Any]):
        """Registra uma métrica no ElasticSearch"""
        try:
            # Adicionar timestamp se não existir
            if 'timestamp' not in metric_data:
                metric_data['timestamp'] = datetime.utcnow().isoformat()
            
            response = self.session.post(
                f"{self.elasticsearch_url}/{self.index_name}/_doc",
                json=metric_data
            )
            
            if response.status_code in [200, 201]:
                self.logger.info(f"Métrica registrada: {metric_data.get('job_id', 'unknown')}")
            else:
                self.logger.error(f"Erro ao registrar métrica: {response.text}")
                
        except Exception as e:
            self.logger.error(f"Erro ao registrar métrica: {e}")
    
    def record_job_start(self, job_id: str, engine_type: str, input_params: Dict[str, Any]):
        """Registra o início de um job"""
        metric_data = {
            "job_id": job_id,
            "engine_type": engine_type,
            "status": "started",
            "input_params": input_params,
            "start_time": datetime.utcnow().isoformat()
        }
        self.record_metric(metric_data)
    
    def record_job_completion(self, job_id: str, execution_time_ms: int, 
                            output_size: int, status: str = "completed", 
                            error_message: Optional[str] = None,
                            memory_usage_mb: Optional[float] = None,
                            cpu_usage_percent: Optional[float] = None,
                            nodes_used: Optional[int] = None,
                            iterations: Optional[int] = None):
        """Registra a conclusão de um job"""
        metric_data = {
            "job_id": job_id,
            "status": status,
            "execution_time_ms": execution_time_ms,
            "output_size": output_size,
            "end_time": datetime.utcnow().isoformat()
        }
        
        if error_message:
            metric_data["error_message"] = error_message
        if memory_usage_mb:
            metric_data["memory_usage_mb"] = memory_usage_mb
        if cpu_usage_percent:
            metric_data["cpu_usage_percent"] = cpu_usage_percent
        if nodes_used:
            metric_data["nodes_used"] = nodes_used
        if iterations:
            metric_data["iterations"] = iterations
            
        self.record_metric(metric_data)
    
    def get_metrics_summary(self, engine_type: Optional[str] = None, 
                          time_range_hours: int = 24) -> Dict[str, Any]:
        """Obtém um resumo das métricas"""
        try:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "range": {
                                    "timestamp": {
                                        "gte": f"now-{time_range_hours}h"
                                    }
                                }
                            }
                        ]
                    }
                },
                "aggs": {
                    "avg_execution_time": {
                        "avg": {"field": "execution_time_ms"}
                    },
                    "total_jobs": {"value_count": {"field": "job_id"}},
                    "success_rate": {
                        "filter": {"term": {"status": "completed"}}
                    },
                    "by_engine": {
                        "terms": {"field": "engine_type"}
                    }
                }
            }
            
            if engine_type:
                query["query"]["bool"]["must"].append({
                    "term": {"engine_type": engine_type}
                })
            
            response = self.session.post(
                f"{self.elasticsearch_url}/{self.index_name}/_search",
                json=query
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Erro ao buscar métricas: {response.text}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar métricas: {e}")
            return {}

# Instância global do coletor de métricas
metrics_collector = MetricsCollector() 