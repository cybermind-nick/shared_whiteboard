import tkinter as tk
from tkinter import Canvas, Button, Scale, Frame
from network.whiteboard_client import WhiteboardNetworkClient

class WhiteboardUI:
    def __init__(self, root: tk.Tk, client: WhiteboardNetworkClient):
        self.root = root
        self.client = client
        self.setup_ui()
        self.setup_bindings()
        self.client.set_message_callback(self.handle_network_message)

    def setup_ui(self):
        self.canvas = Canvas(self.root, bg="white", width=800, height=600)
        self.canvas.pack(expand=True, fill=tk.BOTH)
        
        self.drawing = False
        self.pen_color = "black"
        self.pen_width = 5
        self.points_buffer = []
        
        self.create_toolbar()

    def create_toolbar(self):
        toolbar = Frame(self.root, bd=1, relief=tk.RAISED)
        toolbar.pack(fill=tk.X)

        colors = ["black", "red", "blue", "green", "orange", "yellow", "purple", "pink"]
        for color in colors:
            Button(
                toolbar, 
                bg=color, 
                width=3,
                command=lambda c=color: self.change_pen_color(c)
            ).pack(side=tk.LEFT)

        Scale(
            toolbar,
            from_=1,
            to=10,
            orient=tk.HORIZONTAL,
            label="Pen Width",
            command=self.change_pen_width
        ).pack(side=tk.LEFT, padx=5)

        Button(
            toolbar,
            text="Clear",
            command=self.clear_canvas
        ).pack(side=tk.LEFT, padx=10)

    def setup_bindings(self):
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonPress-1>", self.start_drawing)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drawing)
        self.canvas.bind("<Motion>", self.on_preview)

    def change_pen_color(self, color: str) -> None:
        self.pen_color = color

    def change_pen_width(self, width: str) -> None:
        self.pen_width = int(width)

    def clear_canvas(self) -> None:
        self.canvas.delete("all")
        self.client.send_clear_command()

    def start_drawing(self, event) -> None:
        self.drawing = True
        self.points_buffer = [(event.x, event.y, self.pen_width, self.pen_color)]

    def stop_drawing(self, event) -> None:
        if self.drawing:
            self.drawing = False
            if self.points_buffer:
                self.client.send_draw_data(self.points_buffer)
            self.points_buffer = []

    def on_drag(self, event) -> None:
        if self.drawing:
            x, y = event.x, event.y
            self.canvas.create_oval(
                x, y, 
                x + self.pen_width, 
                y + self.pen_width, 
                fill=self.pen_color, 
                width=0
            )
            self.points_buffer.append((x, y, self.pen_width, self.pen_color))

    def on_preview(self, event) -> None:
        self.canvas.delete("preview_pen")
        x, y = event.x, event.y
        self.canvas.create_oval(
            x - self.pen_width, 
            y - self.pen_width,
            x + self.pen_width, 
            y + self.pen_width,
            fill=self.pen_color, 
            width=0, 
            tags="preview_pen"
        )

    def handle_network_message(self, message: dict) -> None:
        if message["type"] == "sync":
            # Clear canvas first
            self.canvas.delete("all")
            # Replay all actions
            for action in message["data"]["actions"]:
                for x, y, width, color in action["points"]:
                    self.canvas.create_oval(
                        x, y,
                        x + width,
                        y + width,
                        fill=color,
                        width=0
                    )
