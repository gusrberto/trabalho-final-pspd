import socket
import threading
import time
from kubernetes import client, config

# --- Configuração ---
HOST, PORT = '0.0.0.0', 5000
config.load_incluster_config()
custom_api = client.CustomObjectsApi()
core_api = client.CoreV1Api()

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
    custom_api.create_namespaced_custom_object(
        group="sparkoperator.k8s.io",
        version="v1beta2",
        namespace="spark",
        plural="sparkapplications",
        body=spec
    )
    return spec["metadata"]["name"]

def create_mpi_job(powmin, powmax, job_id, num_workers=2):
    name = f"gol-mpi-{job_id}"
    spec = {
      "apiVersion": "kubeflow.org/v2beta1",
      "kind": "MPIJob",
      "metadata": {"name": name, "namespace": "default"},
      "spec": {
        "slotsPerWorker": 1,
        "runPolicy": {"cleanPodPolicy": "Running"},
        "sshAuthMountPath": "/home/mpiuser/.ssh",
        "mpiReplicaSpecs": {
          "Launcher": {
            "replicas": 1,
            "template": {
              "spec": {
                "serviceAccountName": "default",
                "securityContext": {"runAsUser": 1000},
                "volumes": [
                  {
                    "name": "ssh-config",
                    "configMap": {
                      "name": "ssh-config",
                      "items": [
                        {"key": "config", "path": "config"}
                      ]
                    }
                  }
                ],
                "containers": [{
                  "name": "mpi-launcher",
                  "image": "life-mpi-launcher:latest",
                  "imagePullPolicy": "IfNotPresent",
                  "command": ["mpirun"],
                  "args": [
                    "-n", str(num_workers),
                    "/app/life_mpi_omp", str(powmin), str(powmax)
                  ],
                  "env": [
                    {"name": "OMPI_MCA_plm_rsh_args", "value": "-p 2222"},
                    {"name": "OMPI_MCA_orte_rsh_agent", "value": "ssh -F /etc/ssh_config_mpi/config"}
                  ],
                  "resources": {"limits": {"cpu": "1", "memory": "1Gi"}},
                  "volumeMounts": [
                    {
                      "name": "ssh-config",
                      "mountPath": "/etc/ssh_config_mpi/config",
                      "subPath": "config"
                    }
                  ]
                }]
              }
            }
          },
          "Worker": {
            "replicas": num_workers,
            "template": {
              "spec": {
                "serviceAccountName": "default",
                "securityContext": {"runAsUser": 1000},
                "containers": [{
                  "name": "mpi-worker",
                  "image": "life-mpi-worker:latest",
                  "imagePullPolicy": "IfNotPresent",
                  "command": ["/usr/sbin/sshd"],
                  "args": ["-De", "-f", "/home/mpiuser/.sshd_config"],
                  "ports": [{"containerPort": 2222}],
                  "resources": {"limits": {"cpu": "1", "memory": "1Gi"}}
                }]
              }
            }
          }
        }
      }
    }
    custom_api.create_namespaced_custom_object(
      group="kubeflow.org", version="v2beta1",
      namespace="default", plural="mpijobs", body=spec
    )
    return name

def wait_for_completion(name, namespace, group, version, plural, timeout=600):
    """Aguarda a conclusão de um job (Spark ou MPI)."""
    print(f"Aguardando job '{name}' em '{namespace}'...")
    start_time = time.time()
    last_state = ""
    while time.time() - start_time < timeout:
        try:
            job = custom_api.get_namespaced_custom_object(
                group=group, version=version, namespace=namespace, plural=plural, name=name
            )
            state = ""
            if plural == "sparkapplications":
                state = job.get("status", {}).get("applicationState", {}).get("state", "SUBMITTED")
            elif plural == "mpijobs":
                conditions = job.get("status", {}).get("conditions", [])
                if conditions: state = conditions[-1].get("type", "RUNNING")

            if state != last_state:
                print(f"Job '{name}' mudou para o estado: {state}")
                last_state = state

            if state in ("COMPLETED", "Succeeded", "FAILED", "Failed"):
                return state
        except client.ApiException as e:
            if e.status != 404: raise e
        time.sleep(10)
    raise TimeoutError(f"Timeout para o job '{name}'")

def get_job_logs(name, namespace, label_selector_key):
    """Obtém os logs do pod principal de um job (Spark Driver ou MPI Launcher)."""
    print(f"Obtendo logs para o job '{name}'...")
    selector = f"{label_selector_key}={name}"
    pods = core_api.list_namespaced_pod(namespace, label_selector=selector).items
    if not pods: return f"[ERRO] Nenhum pod principal encontrado para o job '{name}'."
    pod_name = pods[0].metadata.name
    return core_api.read_namespaced_pod_log(pod_name, namespace)

def delete_job(name, namespace, group, version, plural):
    """Deleta um job (Spark ou MPI) para limpeza."""
    print(f"Limpando e deletando o job '{name}'...")
    try:
        # CORREÇÃO: Usando a variável correta 'custom_api'
        custom_api.delete_namespaced_custom_object(
            group=group, version=version, namespace=namespace, plural=plural, name=name
        )
    except client.ApiException as e:
        if e.status != 404: print(f"[ERRO] Falha ao deletar job '{name}': {e}")

def handle_client(conn, addr):
    print(f"[+] Conexão de {addr}")
    job_name, namespace, group, version, plural, log_label = "", "", "", "", "", ""
    try:
        data = conn.recv(1024).decode().strip()
        parts = data.split(",")
        engine = parts[0].strip().lower()
        powmin, powmax = map(int, parts[1:])
        job_id = int(time.time())

        if engine == "spark":
            namespace, group, version, plural = "spark", "sparkoperator.k8s.io", "v1beta2", "sparkapplications"
            log_label = "sparkoperator.k8s.io/app-name"
            job_name = create_spark_app(powmin, powmax, job_id)
        elif engine == "mpi":
            namespace, group, version, plural = "default", "kubeflow.org", "v2beta1", "mpijobs"
            log_label = "mpi-job-name"
            job_name = create_mpi_job(powmin, powmax, job_id)
        else:
            raise ValueError("Engine desconhecida. Use 'spark' ou 'mpi'.")

        conn.sendall(f"JOB {job_name} ({engine}) criado. Aguardando conclusão...\n".encode())
        state = wait_for_completion(job_name, namespace, group, version, plural)
        
        logs = get_job_logs(job_name, namespace, log_label)
        
        if state in ("COMPLETED", "Succeeded"):
            # A função de filtro pode ser a mesma se a saída for padronizada
            conn.sendall(logs.encode())
        else:
            conn.sendall(f"\nJob {job_name} falhou com estado '{state}'.\n\n--- LOGS ---\n{logs}".encode())

    except Exception as e:
        print(f"[ERRO] no handle_client: {e}")
        conn.sendall(f"[ERRO NO SERVIDOR] {e}\n".encode())
    finally:
        if job_name:
            delete_job(job_name, namespace, group, version, plural)
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