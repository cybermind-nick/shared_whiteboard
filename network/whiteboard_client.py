import socket
import json
import threading
import uuid
from typing import Callable, Optional, List, Tuple
from queue import Queue
import logging
from models.message import WhiteboardMessage, MessageType, DrawData

class WhiteboardNetworkClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.session_id = str(uuid.uuid4())
        self.message_queue = Queue()
        self.message_callback: Optional[Callable] = None
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('WhiteboardClient')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            receive_thread = threading.Thread(target=self._receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            process_thread = threading.Thread(target=self._process_messages)
            process_thread.daemon = True
            process_thread.start()
            
            self.logger.info("Connected to whiteboard server")
            return True
        except socket.error as e:
            self.logger.error(f"Connection failed: {e}")
            return False

    def disconnect(self) -> None:
        if self.socket and self.connected:
            self.connected = False
            self.socket.close()
            self.logger.info("Disconnected from server")

    def send_draw_data(self, points: List[Tuple[int, int, int, str]]) -> None:
        message = WhiteboardMessage(
            type=MessageType.DRAW,
            data=DrawData(points=points, session_id=self.session_id),
            sender_id=self.session_id
        )
        self._send_message(message)

    def send_clear_command(self) -> None:
        message = WhiteboardMessage(
            type=MessageType.CLEAR,
            sender_id=self.session_id
        )
        self._send_message(message)

    def _send_message(self, message: WhiteboardMessage) -> None:
        if not self.connected or not self.socket:
            self.logger.error("Not connected to server")
            return
            
        try:
            data = {
                "type": message.type.value,
                "data": message.data.__dict__ if message.data else None,
                "sender_id": message.sender_id
            }
            self.socket.sendall(json.dumps(data).encode())
        except socket.error as e:
            self.logger.error(f"Error sending message: {e}")

    def _receive_messages(self) -> None:
        buffer = b""
        while self.connected and self.socket:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                
                buffer += data
                try:
                    message = json.loads(buffer.decode())
                    self.message_queue.put(message)
                    buffer = b""
                except json.JSONDecodeError:
                    continue
                    
            except socket.error as e:
                self.logger.error(f"Error receiving message: {e}")
                break
                
        self.connected = False
        self.logger.info("Stopped receiving messages")

    def _process_messages(self) -> None:
        while self.connected:
            message = self.message_queue.get()
            if self.message_callback:
                self.message_callback(message)

    def set_message_callback(self, callback: Callable) -> None:
        self.message_callback = callback

