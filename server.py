import socket
import threading
import json

HOST = "127.0.0.1"
PORT = 8080
BUFFER_SIZE = 4096

canvas_state = []

def handle_client(client_socket, client_set, up_to_date=False):
    global canvas_state
    print("Global canvas state: ", canvas_state)
    if not up_to_date and len(client_set) > 1:
        if canvas_state != b'':
            client_socket.sendall(json.dumps(canvas_state).encode())
    up_to_date = True
    while True:
        try:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                break

            for client in client_set:
                if client != client_socket:
                    try:
                        client.sendall(data)
                        decoded_data = json.loads(data.decode())
                        print(data)
                        canvas_state += decoded_data
                    except socket.error:
                        # Handle socket errors when sending data to clients
                        print("Socket error occurred while sending data to a client.")
                        pass
            if len(client_set) == 1: # update canvas if there is only one client
                decoded_data = json.loads(data.decode())
                print(decoded_data)
                canvas_state += decoded_data

        except socket.error:
            # Handle socket errors when receiving data from the client
            print("Socket error occurred while receiving data from a client.")
            break

    client_set.remove(client_socket)
    client_socket.close()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)

        print("Server is listening on {}:{}".format(HOST, PORT))

        client_set = set()

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                print("Accepted connection from:", client_address)

                client_set.add(client_socket)
                # if canvas_state:
                #     client_socket.sendall(canvas_state)
                client_thread = threading.Thread(target=handle_client, args=(client_socket, client_set))
                client_thread.start()

            except socket.error:
                # Handle socket errors when accepting new connections
                print("Socket error occurred while accepting a new connection.")
                pass

if __name__ == "__main__":
    main()
