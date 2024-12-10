import socket
import threading
import json
import redis
import redis.exceptions
from redis.sentinel import Sentinel
import os
import time

HOST = ["0.0.0.0", "127.0.0.1"][0]
# PORT = 8080
PORT = 5000
BUFFER_SIZE = 8192

REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]
REDIS_MASTER_PASSWORD = os.environ["REDIS_MASTER_PASSWORD"]
REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])

sentinel = Sentinel([('sentinel', 5000)])

redis_client = sentinel.master_for('mymaster', password=REDIS_PASSWORD)

# redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, retry_on_error=[socket.gaierror, redis.exceptions.ConnectionError])
# redis_client = redis.RedisCluster(host=REDIS_HOST, port=REDIS_PORT)
# redis_client = redis.RedisCluster(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)
# redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, ssl=True)
# redis_client.set('canvas', b'')

redis_client.flushall()

canvas_state = []

def handle_client(client_socket, client_set, up_to_date=False):
    global canvas_state
    global redis_client
    # print("Global canvas state: ", canvas_state)
    try:
        canvas_state = json.loads(redis_client.get('canvas').decode())
    except AttributeError or redis.exceptions.ConnectionError: # canvas does not yet exist
        canvas_state = []

    if not up_to_date and len(client_set) > 1:
        if canvas_state != []:
            client_socket.sendall(json.dumps(canvas_state).encode())
    
    if len(client_set) == 1 and json.loads(redis_client.get("client_count")) > 1: # This circumvents the stateless pods
        if canvas_state != []:
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
                        redis_client.set('canvas', json.dumps(canvas_state).encode())
                    except socket.error:
                        # Handle socket errors when sending data to clients
                        print("Socket error occurred while sending data to a client.")
                        pass
            if len(client_set) == 1: # update canvas if there is only one client
                decoded_data = json.loads(data.decode())
                print(decoded_data)
                canvas_state += decoded_data
                redis_client.set('canvas', json.dumps(canvas_state).encode())


        except socket.error:
            # Handle socket errors when receiving data from the client
            print("Socket error occurred while receiving data from a client.")
            break

    print(f"removing client: {client_socket}")
    client_set.remove(client_socket)
    redis_client.decr("client_count")
    client_socket.close()

    if len(client_set) == 0 and json.loads(redis_client.get("client_count")) <= 0:
        print(f"No connected clients. Shutting down...")
        redis_client.flushall()
        # os._exit(0)

def update_state(client_set):
    global redis_client
    while True:
        time.sleep(2)
        if len(client_set) > 0:
            try:
                # canvas = json.loads(redis_client.get("canvas").decode())
                canvas = redis_client.get("canvas") # object needs to be of type bytes()
                for client in client_set:
                    client.sendall(canvas)
            except:
                print("Canvas doesn't exist")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)

        print("Server is listening on {}:{}".format(HOST, PORT))

        client_set = set()

        update_thread = threading.Thread(target=update_state, args=[client_set])
        update_thread.daemon = True
        update_thread.start()

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                print("Accepted connection from:", client_address)

                client_set.add(client_socket)
                if not redis_client.get("client_count"):
                    redis_client.set("client_count", 1) # first client
                else:
                    redis_client.incr("client_count")

                client_thread = threading.Thread(target=handle_client, args=(client_socket, client_set))
                client_thread.daemon = True
                client_thread.start()

            except socket.error:
                # Handle socket errors when accepting new connections
                print("Socket error occurred while accepting a new connection.")
                pass

if __name__ == "__main__":
    main()
