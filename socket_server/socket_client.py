# client.py
import socket
import sys

# --- Configuração ---
SERVER_HOST = 'localhost' # ou o IP/serviço do seu servidor
SERVER_PORT = 5000
POWMIN = 3
POWMAX = 4
# --------------------

# Cria a mensagem a ser enviada
message = f"{POWMIN},{POWMAX}"

print(f"[*] Conectando a {SERVER_HOST}:{SERVER_PORT}...")
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_HOST, SERVER_PORT))
        print(f"[*] Conectado. Enviando: '{message}'")
        s.sendall(message.encode())

        # Loop para receber a resposta do servidor
        full_response = ""
        while True:
            # Recebe dados em chunks de 1024 bytes
            data = s.recv(1024)
            if not data:
                # Se não houver mais dados, o servidor fechou a conexão
                break
            response_part = data.decode()
            print(response_part, end='') # Imprime em tempo real
            full_response += response_part
        
    print("\n\n[*] Conexão fechada pelo servidor. Fim do programa.")

except ConnectionRefusedError:
    print(f"[ERRO] Conexão recusada. O servidor está rodando em {SERVER_HOST}:{SERVER_PORT}?")
except Exception as e:
    print(f"[ERRO] Ocorreu um erro inesperado: {e}")
