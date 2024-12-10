# models/message.py
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum

class MessageType(Enum):
    DRAW = "draw"
    CLEAR = "clear"
    CURSOR = "cursor"

@dataclass
class DrawData:
    points: List[Tuple[int, int, int, str]]  # x, y, width, color
    session_id: str

@dataclass
class WhiteboardMessage:
    type: MessageType
    data: Optional[DrawData] = None
    sender_id: Optional[str] = None

