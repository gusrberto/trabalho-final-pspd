# client.py
import socket

HOST = '127.0.0.1'
PORT = 5000

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        while True:
            msg = input("powmin,powmax (ou 'exit'): ")
            if msg == 'exit':
                break
            sock.sendall(msg.encode())
            resp = sock.recv(1024).decode()
            print("Resposta:", resp)

if __name__ == "__main__":
    main()
