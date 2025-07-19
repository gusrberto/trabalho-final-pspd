#!/usr/bin/env python3

import requests
import socket
import time
import json
import sys

def test_elasticsearch():
    """Testa se o ElasticSearch está acessível"""
    try:
        response = requests.get("http://localhost:9200/_cluster/health", timeout=5)
        if response.status_code == 200:
            print("✅ ElasticSearch está acessível")
            return True
        else:
            print("❌ ElasticSearch retornou status:", response.status_code)
            return False
    except Exception as e:
        print("❌ ElasticSearch não está acessível:", str(e))
        return False

def test_socket_server():
    """Testa se o socket server está funcionando"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()
        
        if result == 0:
            print("✅ Socket Server está acessível na porta 5000")
            return True
        else:
            print("❌ Socket Server não está acessível na porta 5000")
            return False
    except Exception as e:
        print("❌ Erro ao testar Socket Server:", str(e))
        return False

def test_dashboard():
    """Testa se o dashboard está acessível"""
    try:
        response = requests.get("http://localhost:8080", timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard está acessível")
            return True
        else:
            print("❌ Dashboard retornou status:", response.status_code)
            return False
    except Exception as e:
        print("❌ Dashboard não está acessível:", str(e))
        return False

def test_metrics_api():
    """Testa se a API de métricas está funcionando"""
    try:
        response = requests.get("http://localhost:5001/api/metrics", timeout=5)
        if response.status_code == 200:
            print("✅ API de Métricas está funcionando")
            return True
        else:
            print("❌ API de Métricas retornou status:", response.status_code)
            return False
    except Exception as e:
        print("❌ API de Métricas não está acessível:", str(e))
        return False

def test_game_of_life():
    """Testa o Game of Life enviando uma requisição"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(('localhost', 5000))
        
        # Enviar comando de teste
        sock.send(b"3,4\n")
        
        # Receber resposta
        response = sock.recv(4096).decode()
        sock.close()
        
        if "SUCESSO" in response or "JOB" in response:
            print("✅ Game of Life está funcionando")
            return True
        else:
            print("❌ Game of Life retornou resposta inesperada")
            return False
    except Exception as e:
        print("❌ Erro ao testar Game of Life:", str(e))
        return False

def check_kubernetes_pods():
    """Verifica se os pods estão rodando"""
    try:
        import subprocess
        result = subprocess.run(['kubectl', 'get', 'pods', '--all-namespaces'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Kubernetes está acessível")
            print("📊 Status dos Pods:")
            print(result.stdout)
            return True
        else:
            print("❌ Erro ao verificar pods:", result.stderr)
            return False
    except Exception as e:
        print("❌ Erro ao verificar Kubernetes:", str(e))
        return False

def main():
    print("🧪 Testando Sistema Game of Life com ElasticSearch")
    print("=" * 50)
    
    tests = [
        ("Kubernetes Pods", check_kubernetes_pods),
        ("ElasticSearch", test_elasticsearch),
        ("Socket Server", test_socket_server),
        ("Dashboard", test_dashboard),
        ("API de Métricas", test_metrics_api),
        ("Game of Life", test_game_of_life)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testando {test_name}...")
        if test_func():
            passed += 1
        time.sleep(1)
    
    print("\n" + "=" * 50)
    print(f"📊 Resultado dos Testes: {passed}/{total} passaram")
    
    if passed == total:
        print("🎉 Todos os testes passaram! Sistema está funcionando corretamente.")
        print("\n📋 Próximos passos:")
        print("1. Acesse o dashboard: http://localhost:8080")
        print("2. Teste o Game of Life: echo '3,4' | nc localhost 5000")
        print("3. Visualize métricas no ElasticSearch: http://localhost:9200")
    else:
        print("⚠️ Alguns testes falharam. Verifique:")
        print("1. Se o setup.sh foi executado completamente")
        print("2. Se o port forwarding está ativo")
        print("3. Se todos os pods estão rodando: kubectl get pods --all-namespaces")
        sys.exit(1)

if __name__ == "__main__":
    main() 