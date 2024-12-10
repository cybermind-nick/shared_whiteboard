import socket
import threading
import tkinter as tk
import json
from tkinter import Canvas, messagebox, Scale, Button
from queue import Queue
from ui import WhiteboardUI
from network import WhiteboardNetworkClient

def main():
    root = tk.Tk()
    root.title("Distributed Whiteboard")

    client = WhiteboardNetworkClient()
    if not client.connect():
        tk.messagebox.showerror(
            "Connection Error",
            "Could not connect to the whiteboard server."
        )
        return

    whiteboard = WhiteboardUI(root, client)
    
    def on_closing():
        client.disconnect()
        root.quit()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
