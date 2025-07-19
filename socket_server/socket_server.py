import socket
import threading
import time
import re
from kubernetes import client, config

# --- Configuração ---
HOST, PORT = '0.0.0.0', 5000
config.load_incluster_config()
api = client.CustomObjectsApi()

def create_spark_app(powmin, powmax, job_id):
    """Cria a especificação da SparkApplication e a submete ao K8s."""

    spec = {
      "apiVersion": "sparkoperator.k8s.io/v1beta2",
      "kind": "SparkApplication",
      "metadata": {"name": f"gol-{job_id}", "namespace": "spark"},
      "spec": {
        "type": "Python",
        "pythonVersion": "3",
        "mode": "cluster",
        "image": "life-spark:latest",
        "imagePullPolicy": "IfNotPresent",
        "mainApplicationFile": "local:///app/game_of_life_spark.py",
        "sparkVersion": "3.5.1",
        "arguments": [str(powmin), str(powmax)],
        "driver": {
            "cores": 1,
            "memory": "1g", 
            "serviceAccount": "spark"
        },
        "executor": {
            "cores": 1,
            "memory": "1g",
            "instances": 1
        }
      }
    }
    # Submete o objeto customizado para o Spark Operator
    api.create_namespaced_custom_object(
        group="sparkoperator.k8s.io",
        version="v1beta2",
        namespace="spark",
        plural="sparkapplications",
        body=spec
    )
    return spec["metadata"]["name"]

def wait_for_completion(name, timeout=600, interval=10):
    """Aguarda a conclusão de um SparkApplication, verificando seu status."""
    print(f"Aguardando job '{name}'...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            app = api.get_namespaced_custom_object(
                group="sparkoperator.k8s.io",
                version="v1beta2",
                namespace="spark",
                plural="sparkapplications",
                name=name
            )
            state = app.get("status", {}).get("applicationState", {}).get("state", "SUBMITTED")
            print(f"Job '{name}' está no estado: {state}")
            if state in ("COMPLETED", "FAILED"):
                return state
        except client.ApiException as e:
            if e.status == 404:
                print(f"Job '{name}' não encontrado, aguardando criação...")
            else:
                raise e # Lança outras exceções da API
        time.sleep(interval)
    raise TimeoutError(f"Timeout de {timeout}s atingido para o job SparkApplication '{name}'")

def get_driver_logs(app_name):
    """Obtém os logs do pod do driver de uma aplicação Spark."""
    v1 = client.CoreV1Api()
    # O label selector padrão usado pelo Spark Operator
    selector = f"sparkoperator.k8s.io/app-name={app_name},spark-role=driver"
    try:
        pods = v1.list_namespaced_pod("spark", label_selector=selector, timeout_seconds=60).items
        if not pods:
            return f"[ERRO] Nenhum pod de driver encontrado para o job '{app_name}'."
        # Pega o primeiro pod encontrado (só deve haver um)
        driver_pod_name = pods[0].metadata.name
        print(f"Encontrado pod do driver: {driver_pod_name}")
        # Lê os logs do container principal do pod
        return v1.read_namespaced_pod_log(driver_pod_name, "spark")
    except Exception as e:
        return f"[ERRO] Falha ao obter logs do driver para '{app_name}': {e}"

def filter_game_result(logs):
    """Extrai os blocos de resultado do log completo do Spark."""
    output_lines = []

    start_marker = re.compile(r"^--- Análise para tam=\d+ ---")
    
    analysis_blocks = start_marker.split(logs)

    # O primeiro elemento é o que vem antes do primeiro marcador, então o ignoramos.
    for block in analysis_blocks[1:]:
        # Remonta o bloco com seu marcador original
        full_block = "--- Análise para tam=" + block
        output_lines.append(full_block.strip())

    if not output_lines:
        return "[Nenhum bloco de resultado encontrado nos logs]"
        
    return "\n\n".join(output_lines)

def handle_client(conn, addr):
    """Lida com uma conexão de cliente individualmente."""
    print(f"[+] Conexão de {addr}")
    try:
        data = conn.recv(1024).decode().strip()
        if not re.match(r"^\d+,\d+$", data):
            raise ValueError("Formato inválido")
        powmin, powmax = map(int, data.split(","))
        
        job_id = int(time.time())
        name = create_spark_app(powmin, powmax, job_id)
        conn.sendall(f"JOB {name} criado, aguardando...\n".encode())
        
        state = wait_for_completion(name)
        
        print(f"Job '{name}' finalizou com estado: {state}")
        logs = get_driver_logs(name)
        
        if state != "COMPLETED":
            # MELHORIA: Envia os logs de erro para o cliente para depuração
            response = f"Job {name} falhou com estado '{state}'.\n\n--- LOGS DE ERRO ---\n{logs}"
            conn.sendall(response.encode())
        else:
            # CORREÇÃO: Usa o resultado filtrado ao invés dos logs completos
            result_block = filter_game_result(logs)
            conn.sendall(result_block.encode())

    except TimeoutError as e:
        conn.sendall(f"[ERRO] {e}\n".encode())
    except Exception as e:
        conn.sendall(f"[ERRO] Falha no servidor: {e}\n".encode())
    finally:
        conn.close()
        print(f"[-] Desconectado {addr}")

def main():
    """Função principal do servidor."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[+] Servidor escutando em {HOST}:{PORT}")
    
    while True:
        client_conn, client_addr = server_socket.accept()
        # Inicia uma nova thread para cada cliente
        thread = threading.Thread(target=handle_client, args=(client_conn, client_addr), daemon=True)
        thread.start()

if __name__ == "__main__":
    main()