#!/usr/bin/env python3

from flask import Flask, jsonify
from metrics_collector import MetricsCollector
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Instanciar o coletor de métricas
metrics_collector = MetricsCollector()

@app.route('/api/metrics')
def get_metrics():
    """Endpoint para obter métricas do ElasticSearch"""
    try:
        # Buscar métricas das últimas 24 horas
        metrics = metrics_collector.get_metrics_summary(time_range_hours=24)
        
        # Formatar dados para o dashboard
        formatted_metrics = {
            "total_jobs": metrics.get("total_jobs", 0),
            "avg_execution_time": metrics.get("avg_execution_time", 0),
            "success_rate": metrics.get("success_rate", 0),
            "engines": metrics.get("engines", []),
            "engine_counts": metrics.get("engine_counts", []),
            "execution_times": metrics.get("execution_times", []),
            "time_labels": metrics.get("time_labels", []),
            "concurrent_clients": metrics.get("concurrent_clients", [])
        }
        
        logger.info(f"Métricas obtidas: {formatted_metrics}")
        return jsonify(formatted_metrics)
        
    except Exception as e:
        logger.error(f"Erro ao obter métricas: {e}")
        return jsonify({
            "error": str(e),
            "total_jobs": 0,
            "avg_execution_time": 0,
            "success_rate": 0,
            "engines": [],
            "engine_counts": [],
            "execution_times": [],
            "time_labels": [],
            "concurrent_clients": []
        }), 500

@app.route('/api/health')
def health_check():
    """Endpoint de health check"""
    return jsonify({"status": "healthy"})

@app.route('/')
def index():
    """Redirecionar para o dashboard"""
    return app.send_static_file('index.html')

if __name__ == '__main__':
    logger.info("Iniciando servidor de métricas...")
    app.run(host='0.0.0.0', port=8080, debug=False) 