import socket
import threading
import json
import logging
import time
import os
from dotenv import load_dotenv
from typing import Set, Dict, Any, Optional

from models.state import RedisClusterStateManager

class WhiteboardServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        load_dotenv()
        self.host = host
        self.port = port
        self.state_manager = RedisClusterStateManager(
            startup_nodes=[
                {'host': 'redis-cluster', 'port': 7000},
                {'host': 'redis-cluster-2', 'port': 7001},
                {'host': 'redis-cluster-3', 'port': 7002}
            ]
        )

        self.clients: Set[socket.socket] = set()
        self.client_sessions: Dict[socket.socket, str] = {}
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('WhiteboardServer')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def broadcast(self, message: Dict[str, Any], sender_socket: Optional[socket.socket] = None) -> None:
        """Broadcast message to all clients except sender."""
        encoded_message = json.dumps(message).encode()
        
        for client in self.clients:
            if client != sender_socket:  # Don't send back to sender
                try:
                    client.sendall(encoded_message)
                except socket.error as e:
                    self.logger.error(f"Error broadcasting to client: {e}")
                    self.remove_client(client)

    def remove_client(self, client_socket: socket.socket) -> None:
        """Remove a client from the server."""
        if client_socket in self.clients:
            self.clients.remove(client_socket)
            self.client_sessions.pop(client_socket, None)
            try:
                client_socket.close()
            except socket.error:
                pass
            self.logger.info(f"Client disconnected. Active connections: {len(self.clients)}")

    def handle_client(self, client_socket: socket.socket) -> None:
        """Handle individual client connections."""
        buffer = b""
        
        while True:
            try:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                buffer += data
                
                try:
                    # Try to decode and process the message
                    message = json.loads(buffer.decode())
                    
                    # Store the client's session ID if provided
                    if 'sender_id' in message:
                        self.client_sessions[client_socket] = message['sender_id']
                    
                    # Broadcast the message to all other clients
                    self.broadcast(message, client_socket)
                    
                    # Clear the buffer after successful processing
                    buffer = b""
                    
                except json.JSONDecodeError:
                    # If we can't decode the JSON yet, continue collecting data
                    continue
                    
            except socket.error as e:
                self.logger.error(f"Error receiving data from client: {e}")
                break
        
        self.remove_client(client_socket)

    def handle_draw_message(self, message: Dict, client_socket: socket.socket) -> None:
        """Handle drawing action from client."""
        action = {
            "points": message["data"]["points"],
            "timestamp": time.time(),
            "session_id": message["sender_id"]
        }
        
        # Save to Redis
        self.state_manager.save_action(action)
        
        # Broadcast to other clients
        broadcast_message = {
            "type": "draw",
            "data": action
        }
        self.broadcast(broadcast_message, client_socket)

    def handle_clear_message(self, message: Dict, client_socket: socket.socket) -> None:
        """Handle canvas clear command."""
        self.state_manager.clear_state()
        clear_message = {
            "type": "clear",
            "timestamp": self.state_manager.get_last_clear_timestamp()
        }
        self.broadcast(clear_message, client_socket)

    def handle_client_connect(self, client_socket: socket.socket, session_id: str, last_timestamp: float) -> None:
        """Handle new client connection or reconnection."""
        self.clients[client_socket] = session_id
        
        # Get state from Redis
        actions = self.state_manager.get_actions_since(last_timestamp)
        sync_message = {
            "type": "sync",
            "data": {
                "actions": actions,
                "last_clear_timestamp": self.state_manager.get_last_clear_timestamp()
            }
        }
        
        try:
            client_socket.sendall(json.dumps(sync_message).encode())
        except socket.error as e:
            self.logger.error(f"Error sending sync data: {e}")

    def start(self) -> None:
        """Start the whiteboard server."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                # Allow port reuse
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                server_socket.bind((self.host, self.port))
                server_socket.listen(5)
                
                self.logger.info(f"Whiteboard server listening on {self.host}:{self.port}")

                while True:
                    try:
                        client_socket, address = server_socket.accept()
                        self.logger.info(f"New connection from {address}")
                        
                        self.clients.add(client_socket)
                        
                        # Start a new thread to handle the client
                        client_thread = threading.Thread(
                            target=self.handle_client,
                            args=(client_socket,)
                        )
                        client_thread.daemon = True
                        client_thread.start()
                        
                    except socket.error as e:
                        self.logger.error(f"Error accepting connection: {e}")
                        continue
                        
        except socket.error as e:
            self.logger.error(f"Server error: {e}")
        finally:
            # Clean up all client connections
            for client in self.clients.copy():
                self.remove_client(client)

# server_main.py
def main():
    server = WhiteboardServer()
    server.start()

if __name__ == "__main__":
    main()
