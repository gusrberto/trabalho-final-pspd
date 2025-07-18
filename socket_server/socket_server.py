# server.py

import socket
import subprocess
import threading
import time
from kubernetes import client, config
import yaml

HOST = '0.0.0.0'
PORT = 5000

# Carregar configuração dentro do cluster
config.load_incluster_config()
api = client.CustomObjectsApi()

def create_spark_app(powmin, powmax, job_id):
    namespace = "spark"
    name = f"game-of-life-{job_id}"
    spark_app = {
        "apiVersion": "sparkoperator.k8s.io/v1beta2",
        "kind": "SparkApplication",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "type": "Python",
            "mode": "cluster",
            "image": "life-spark:latest",
            "mainApplicationFile": "local:///app/game_of_life_spark.py",
            "arguments": [str(powmin), str(powmax)],
            "driver": {"cores": 1, "memory": "1g", "serviceAccount": "spark"},
            "executor": {"cores": 1, "memory": "1g", "instances": 2}
        }
    }
    api.create_namespaced_custom_object(
        group="sparkoperator.k8s.io",
        version="v1beta2",
        namespace=namespace,
        plural="sparkapplications",
        body=spark_app
    )
    return name

def wait_for_completion(name):
    namespace = "spark"
    while True:
        app = api.get_namespaced_custom_object(
            group="sparkoperator.k8s.io", version="v1beta2",
            namespace=namespace, plural="sparkapplications",
            name=name
        )
        state = app.get("status", {}).get("applicationState", {}).get("state", "")
        if state in ("COMPLETED", "FAILED"):
            return state
        time.sleep(2)

def filter_game_result(logs: str) -> str:
    lines = logs.splitlines()
    filtered = []
    for line in lines:
        line = line.strip()
        # verificar se linha tem o formato x,y,1 (3 valores, último é 1, x e y inteiros)
        parts = line.split(",")
        if len(parts) == 3 and parts[2] == "1":
            try:
                x = int(parts[0])
                y = int(parts[1])
                filtered.append(line)
            except ValueError:
                pass
    if not filtered:
        return "[nenhuma célula viva]"
    return "\n".join(filtered)

def get_driver_logs(app_name, namespace="spark"):
    core_v1 = client.CoreV1Api()
    label_selector = f"sparkoperator.k8s.io/app-name={app_name},spark-role=driver"
    pods = core_v1.list_namespaced_pod(namespace, label_selector=label_selector)
    if not pods.items:
        return "Erro: driver pod não encontrado"
    pod_name = pods.items[0].metadata.name
    logs = core_v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)
    return logs

def handle_client(conn, addr):
    print(f"[+] Conexão de {addr}")
    with conn:
        try:
            data = conn.recv(1024)
            if not data:
                conn.sendall(b"Erro: Nenhum dado recebido.\n")
                return

            try:
                powmin, powmax = map(int, data.decode().strip().split(","))
            except ValueError:
                conn.sendall(b"Erro: Formato invalido. Use: inteiro,inteiro\n")
                return

            job_id = int(time.time())
            app_name = create_spark_app(powmin, powmax, job_id)

            conn.sendall(f"JOB {app_name} criado. Aguardando conclusão...\n".encode())

            state = wait_for_completion(app_name)

            if state == "COMPLETED":
                logs = get_driver_logs(app_name)
                filtered_logs = filter_game_result(logs)
                response = f"SUCESSO JOB {app_name} finalizado com sucesso!\nResultado:\n{filtered_logs}\n"
            else:
                response = f"FALHA JOB {app_name} falhou na execução.\n"

            conn.sendall(response.encode())

        except Exception as e:
            error_msg = f"Erro interno do servidor: {str(e)}\n"
            conn.sendall(error_msg.encode())
            print(f"[!] Erro com {addr}: {e}")
        finally:
            print(f"[-] Desconectado {addr}")

def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind((HOST, PORT))
    srv.listen()
    print(f"[+] Servidor escutando {HOST}:{PORT}")

    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()

if __name__ == "__main__":
    main()
