from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

ELASTICSEARCH_URL = "http://elasticsearch.elasticsearch.svc.cluster.local:9200"
INDEX_NAME = "game-of-life-metrics"

@app.route('/api/metrics')
def get_metrics():
    """Endpoint para obter métricas do ElasticSearch"""
    try:
        # Query para obter métricas das últimas 24 horas
        query = {
            "query": {
                "range": {
                    "timestamp": {
                        "gte": "now-24h"
                    }
                }
            },
            "aggs": {
                "avg_execution_time": {
                    "avg": {"field": "execution_time_ms"}
                },
                "total_jobs": {
                    "value_count": {"field": "job_id"}
                },
                "success_rate": {
                    "filter": {"term": {"status": "completed"}}
                },
                "by_engine": {
                    "terms": {"field": "engine_type"}
                },
                "execution_times_over_time": {
                    "date_histogram": {
                        "field": "timestamp",
                        "calendar_interval": "1h"
                    },
                    "aggs": {
                        "avg_time": {
                            "avg": {"field": "execution_time_ms"}
                        }
                    }
                }
            },
            "sort": [
                {"timestamp": {"order": "desc"}}
            ],
            "size": 100
        }
        
        response = requests.post(
            f"{ELASTICSEARCH_URL}/{INDEX_NAME}/_search",
            json=query,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            return jsonify({"error": "Erro ao buscar métricas"}), 500
        
        data = response.json()
        hits = data.get('hits', {}).get('hits', [])
        aggregations = data.get('aggregations', {})
        
        # Processar dados
        metrics = {
            "total_jobs": aggregations.get('total_jobs', {}).get('value', 0),
            "avg_execution_time": aggregations.get('avg_execution_time', {}).get('value', 0),
            "success_rate": 0,
            "engines": [],
            "engine_counts": [],
            "execution_times": [],
            "time_labels": []
        }
        
        # Calcular taxa de sucesso
        total_jobs = metrics["total_jobs"]
        if total_jobs > 0:
            success_count = aggregations.get('success_rate', {}).get('doc_count', 0)
            metrics["success_rate"] = success_count / total_jobs
        
        # Processar dados por engine
        by_engine = aggregations.get('by_engine', {}).get('buckets', [])
        for bucket in by_engine:
            metrics["engines"].append(bucket['key'])
            metrics["engine_counts"].append(bucket['doc_count'])
        
        # Processar dados de tempo
        time_buckets = aggregations.get('execution_times_over_time', {}).get('buckets', [])
        for bucket in time_buckets:
            timestamp = bucket['key_as_string']
            avg_time = bucket.get('avg_time', {}).get('value', 0)
            metrics["time_labels"].append(timestamp)
            metrics["execution_times"].append(avg_time)
        
        return jsonify(metrics)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/metrics/detailed')
def get_detailed_metrics():
    """Endpoint para obter métricas detalhadas"""
    try:
        engine_type = request.args.get('engine_type')
        time_range = request.args.get('time_range', '24h')
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "timestamp": {
                                    "gte": f"now-{time_range}"
                                }
                            }
                        }
                    ]
                }
            },
            "aggs": {
                "jobs_by_status": {
                    "terms": {"field": "status"}
                },
                "execution_time_stats": {
                    "stats": {"field": "execution_time_ms"}
                },
                "output_size_stats": {
                    "stats": {"field": "output_size"}
                }
            },
            "sort": [
                {"timestamp": {"order": "desc"}}
            ],
            "size": 50
        }
        
        if engine_type:
            query["query"]["bool"]["must"].append({
                "term": {"engine_type": engine_type}
            })
        
        response = requests.post(
            f"{ELASTICSEARCH_URL}/{INDEX_NAME}/_search",
            json=query,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            return jsonify({"error": "Erro ao buscar métricas detalhadas"}), 500
        
        data = response.json()
        hits = data.get('hits', {}).get('hits', [])
        aggregations = data.get('aggregations', {})
        
        # Processar jobs recentes
        recent_jobs = []
        for hit in hits:
            source = hit['_source']
            recent_jobs.append({
                "job_id": source.get('job_id'),
                "engine_type": source.get('engine_type'),
                "status": source.get('status'),
                "execution_time_ms": source.get('execution_time_ms'),
                "timestamp": source.get('timestamp')
            })
        
        # Processar estatísticas
        stats = {
            "recent_jobs": recent_jobs,
            "status_distribution": {},
            "execution_time_stats": aggregations.get('execution_time_stats', {}),
            "output_size_stats": aggregations.get('output_size_stats', {})
        }
        
        # Distribuição por status
        status_buckets = aggregations.get('jobs_by_status', {}).get('buckets', [])
        for bucket in status_buckets:
            stats["status_distribution"][bucket['key']] = bucket['doc_count']
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        response = requests.get(f"{ELASTICSEARCH_URL}/_cluster/health")
        if response.status_code == 200:
            return jsonify({"status": "healthy", "elasticsearch": "connected"})
        else:
            return jsonify({"status": "unhealthy", "elasticsearch": "disconnected"}), 500
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 