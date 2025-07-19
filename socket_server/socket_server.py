# server.py

import socket
import subprocess
import threading
import time
from kubernetes import client, config
import yaml
# import sys
# import os

# # Adicionar o diretório pai ao path para importar o coletor de métricas
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from metrics_collector import metrics_collector

HOST = '0.0.0.0'
PORT = 5000

# Carregar configuração dentro do cluster
config.load_incluster_config()
api = client.CustomObjectsApi()

def create_spark_app(powmin, powmax, job_id):
    # Simular criação de job por enquanto
    print(f"Simulando criação de job Spark: {powmin}, {powmax}")
    return f"game-of-life-{job_id}"

def wait_for_completion(name):
    # Simular espera por conclusão
    print(f"Simulando espera por conclusão do job: {name}")
    time.sleep(3)  # Simular processamento
    return "COMPLETED"

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
    # Simular logs do driver
    print(f"Simulando logs do driver para: {app_name}")
    return "1,2,1\n2,3,1\n3,1,1\n3,2,1\n3,3,1"

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
            start_time = time.time()
            
            # Registrar início do job
            # metrics_collector.record_job_start(
            #     job_id=str(job_id),
            #     engine_type="spark",
            #     input_params={"powmin": powmin, "powmax": powmax}
            # )
            
            app_name = create_spark_app(powmin, powmax, job_id)

            conn.sendall(f"JOB {app_name} criado. Aguardando conclusão...\n".encode())

            state = wait_for_completion(app_name)
            execution_time_ms = int((time.time() - start_time) * 1000)

            if state == "COMPLETED":
                logs = get_driver_logs(app_name)
                filtered_logs = filter_game_result(logs)
                output_size = len(filtered_logs.split('\n')) if filtered_logs != "[nenhuma célula viva]" else 0
                
                # Registrar conclusão do job
                # metrics_collector.record_job_completion(
                #     job_id=str(job_id),
                #     execution_time_ms=execution_time_ms,
                #     output_size=output_size,
                #     status="completed",
                #     iterations=powmax - powmin
                # )
                
                response = f"SUCESSO JOB {app_name} finalizado com sucesso!\nResultado:\n{filtered_logs}\n"
            else:
                # Registrar falha do job
                # metrics_collector.record_job_completion(
                #     job_id=str(job_id),
                #     execution_time_ms=execution_time_ms,
                #     output_size=0,
                #     status="failed",
                #     error_message=f"Job {app_name} falhou na execução"
                # )
                
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
