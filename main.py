import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import os
import json
import threading
from game_logic import GameLogic
from network import Network

class SmashOrPassApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smash or Pass")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Load config
        with open('config.json') as f:
            config = json.load(f)
        self.image_folder = config['default_image_folder']
        self.port = config['default_port']
        self.username = simpledialog.askstring("Username", "Enter your username:", parent=self.root) or config['default_username']

        # Game logic
        self.game = GameLogic(self.image_folder)
        self.network = None
        self.votes = {}  # {username: vote}

        # UI
        self.setup_ui()

    def setup_ui(self):
        # Main frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Image display
        self.image_label = tk.Label(self.main_frame)
        self.image_label.pack(pady=20)

        # Buttons
        self.btn_frame = tk.Frame(self.main_frame)
        self.btn_frame.pack(pady=20)

        self.smash_btn = tk.Button(
            self.btn_frame,
            text="SMASH",
            command=self.vote_smash,
            state=tk.DISABLED,
            width=10,
            height=2,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold")
        )
        self.smash_btn.pack(side=tk.LEFT, padx=20)

        self.pass_btn = tk.Button(
            self.btn_frame,
            text="PASS",
            command=self.vote_pass,
            state=tk.DISABLED,
            width=10,
            height=2,
            bg="#F44336",
            fg="white",
            font=("Arial", 12, "bold")
        )
        self.pass_btn.pack(side=tk.LEFT, padx=20)

        # Results
        self.results_frame = tk.Frame(self.main_frame)
        self.results_frame.pack(fill=tk.BOTH, expand=True, pady=20)

        self.results_label = tk.Label(
            self.results_frame,
            text="Votes will appear here:",
            font=("Arial", 12)
        )
        self.results_label.pack(anchor="w")

        self.results_text = tk.Text(
            self.results_frame,
            height=8,
            width=60,
            state=tk.DISABLED,
            font=("Arial", 10)
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)

        # Menu
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)

        file_menu = tk.Menu(self.menu, tearoff=0)
        file_menu.add_command(label="Select Image Folder", command=self.select_folder)
        file_menu.add_command(label="Host Game", command=self.host_game)
        file_menu.add_command(label="Join Game", command=self.join_game)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        self.menu.add_cascade(label="File", menu=file_menu)

        # Status
        self.status_label = tk.Label(
            self.main_frame,
            text=f"Welcome, {self.username}! Select an image folder and host/join a game.",
            font=("Arial", 10)
        )
        self.status_label.pack(pady=10)

        # Initial state
        self.current_image = None
        self.current_image_path = None

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.image_folder = folder
            self.game = GameLogic(folder)
            self.status_label.config(text=f"Image folder: {folder}")

    def host_game(self):
        if not self.game.images:
            messagebox.showerror("Error", "No images in folder!")
            return
        self.network = Network(port=self.port, username=self.username)
        self.network.on('vote', self.receive_vote)
        self.network.on('next_image', self.receive_next_image)
        self.network.on('user_joined', self.user_joined)
        self.status_label.config(text=f"Hosting game. Room key: {self.network.room_key}")
        self.start_game()

    def join_game(self):
        host_ip = simpledialog.askstring("Join Game", "Enter host IP:")
        room_key = simpledialog.askstring("Join Game", "Enter room key:")
        if host_ip and room_key:
            self.network = Network(host_ip=host_ip, port=self.port, room_key=room_key, username=self.username)
            self.network.on('next_image', self.receive_next_image)
            self.network.on('vote', self.receive_vote)
            self.network.on('user_joined', self.user_joined)
            self.status_label.config(text=f"Joined game at {host_ip}")
            self.smash_btn.config(state=tk.NORMAL)
            self.pass_btn.config(state=tk.NORMAL)

    def start_game(self):
        self.next_image()
        self.smash_btn.config(state=tk.NORMAL)
        self.pass_btn.config(state=tk.NORMAL)

    def next_image(self):
        img, path = self.game.get_random_image()
        if img:
            self.current_image = img
            self.current_image_path = path
            self.image_label.config(image=img)
            self.image_label.image = img
            self.votes = {}
            self.update_results()
            if self.network and self.network.is_host:
                self.network.send('next_image', {'path': path})

    def receive_next_image(self, data, addr=None):
        self.root.after(0, lambda: self._receive_next_image(data))

    def _receive_next_image(self, data):
        path = data['path']
        try:
            img = Image.open(path)
            img = img.resize((500, 500), Image.LANCZOS)
            img_tk = ImageTk.PhotoImage(img)
            self.current_image = img_tk
            self.current_image_path = path
            self.image_label.config(image=img_tk)
            self.image_label.image = img_tk
            self.votes = {}
            self.update_results()
        except Exception as e:
            print(f"Error loading image from network: {e}")

    def vote_smash(self):
        self.send_vote("smash")
        if self.network and self.network.is_host:
            self.next_image()

    def vote_pass(self):
        self.send_vote("pass")
        if self.network and self.network.is_host:
            self.next_image()

    def send_vote(self, vote):
        if self.network:
            self.votes[self.username] = vote
            self.update_results()
            self.network.send('vote', {'vote': vote, 'image': self.current_image_path})

    def receive_vote(self, data, addr=None):
        username = self.network.clients.get(addr, "Unknown")
        vote = data['vote']
        image = data['image']
        self.votes[username] = vote
        self.update_results()

    def user_joined(self, data, addr=None):
        username = data['username']
        self.results_text.config(state=tk.NORMAL)
        self.results_text.insert(tk.END, f"{username} joined the game.\n")
        self.results_text.config(state=tk.DISABLED)

    def update_results(self):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        if not self.votes:
            self.results_text.insert(tk.END, "No votes yet.\n")
        else:
            for user, vote in self.votes.items():
                self.results_text.insert(tk.END, f"{user}: {vote.upper()}\n")
        self.results_text.config(state=tk.DISABLED)

    def on_close(self):
        if self.network:
            self.network.close()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = SmashOrPassApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
