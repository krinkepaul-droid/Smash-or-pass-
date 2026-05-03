import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import os
import json
import threading
from game_logic import GameLogic
from network import Network

def create_default_config():
    """Create default config.json if it doesn't exist"""
    config_path = 'config.json'
    if not os.path.exists(config_path):
        default_config = {
            "default_image_folder": "./images",
            "default_port": 55555,
            "default_username": "Player"
        }
        try:
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"Created default {config_path}")
        except IOError as e:
            print(f"Error creating config file: {e}")

def load_config():
    """Load config from config.json with validation"""
    create_default_config()
    try:
        with open('config.json') as f:
            config = json.load(f)
        
        # Validate required keys
        required_keys = ['default_image_folder', 'default_port', 'default_username']
        for key in required_keys:
            if key not in config:
                print(f"Warning: Missing key '{key}' in config, using default")
                return get_default_config()
        
        # Validate port is an integer
        if not isinstance(config['default_port'], int) or config['default_port'] <= 0 or config['default_port'] > 65535:
            print("Warning: Invalid port in config, using default")
            return get_default_config()
        
        return config
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading config: {e}, using defaults")
        return get_default_config()

def get_default_config():
    """Return default configuration"""
    return {
        "default_image_folder": "./images",
        "default_port": 55555,
        "default_username": "Player"
    }

class SmashOrPassApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smash or Pass")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Load config
        config = load_config()
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
        # Main container
        self.main_frame = tk.Frame(self.root, padx=10, pady=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # --- TOOLBAR (Top) ---
        self.toolbar = tk.Frame(self.main_frame, bd=1, relief=tk.RAISED, padx=5, pady=5)
        self.toolbar.pack(fill=tk.X, pady=(0, 10))

        # Toolbar buttons
        tk.Button(
            self.toolbar,
            text="📁 Select Image Folder",
            command=self.select_folder,
            width=20,
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            self.toolbar,
            text="🏠 Host Game",
            command=self.host_game,
            width=15,
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            self.toolbar,
            text="��� Join Game",
            command=self.join_game,
            width=15,
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=5)

        # --- IMAGE DISPLAY (Center) ---
        self.image_frame = tk.Frame(self.main_frame, bd=2, relief=tk.SUNKEN, bg="black")
        self.image_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.image_label = tk.Label(self.image_frame, bg="black", text="No image loaded", fg="white")
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- VOTING BUTTONS (Below Image) ---
        self.vote_frame = tk.Frame(self.main_frame)
        self.vote_frame.pack(fill=tk.X, pady=10)

        self.smash_btn = tk.Button(
            self.vote_frame,
            text="✅ SMASH",
            command=self.vote_smash,
            state=tk.DISABLED,
            width=12,
            height=2,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold")
        )
        self.smash_btn.pack(side=tk.LEFT, padx=20)

        self.pass_btn = tk.Button(
            self.vote_frame,
            text="❌ PASS",
            command=self.vote_pass,
            state=tk.DISABLED,
            width=12,
            height=2,
            bg="#F44336",
            fg="white",
            font=("Arial", 12, "bold")
        )
        self.pass_btn.pack(side=tk.LEFT, padx=20)

        # --- RESULTS PANEL (Bottom) ---
        self.results_frame = tk.LabelFrame(
            self.main_frame,
            text="📊 Live Votes",
            bd=1,
            relief=tk.GROOVE,
            padx=5,
            pady=5
        )
        self.results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.results_text = tk.Text(
            self.results_frame,
            height=6,
            width=60,
            state=tk.DISABLED,
            font=("Arial", 10),
            wrap=tk.WORD,
            padx=5,
            pady=5
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)

        # --- STATUS BAR (Very Bottom) ---
        self.status_label = tk.Label(
            self.main_frame,
            text=f"Welcome, {self.username}! Select an image folder and host/join a game.",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Arial", 10),
            padx=5
        )
        self.status_label.pack(fill=tk.X, pady=(10, 0))

        # Initial state
        self.current_image = None
        self.current_image_path = None

    # --- REST OF THE CODE (Unchanged) ---
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
            self.image_label.config(image=img, text="")
            self.image_label.image = img
            self.votes = {}
            self.update_results()
            if self.network and self.network.is_host:
                self.network.send('next_image', {'path': path})

    def receive_next_image(self, data, addr=None):
        self.root.after(0, lambda: self._receive_next_image(data))

    def _receive_next_image(self, data):
        path = data.get('path')
        if not path:
            print("Error: No path provided in next_image")
            return
        try:
            img = Image.open(path)
            img = self.game._scale_image(img)
            img_tk = ImageTk.PhotoImage(img)
            self.current_image = img_tk
            self.current_image_path = path
            self.image_label.config(image=img_tk, text="")
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
        if not self.network or not addr:
            return
        username = self.network.clients.get(addr, "Unknown")
        vote = data.get('vote', 'unknown')
        self.votes[username] = vote
        self.update_results()

    def user_joined(self, data, addr=None):
        username = data.get('username', 'Unknown')
        self.results_text.config(state=tk.NORMAL)
        self.results_text.insert(tk.END, f"👤 {username} joined the game.\n")
        self.results_text.config(state=tk.DISABLED)

    def update_results(self):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        if not self.votes:
            self.results_text.insert(tk.END, "No votes yet.\n")
        else:
            for user, vote in self.votes.items():
                emoji = "✅" if vote == "smash" else "❌"
                self.results_text.insert(tk.END, f"{emoji} {user}: {vote.upper()}\n")
        self.results_text.config(state=tk.DISABLED)

    def on_close(self):
        if self.network:
            self.network.close()
        self.root.quit()

if __name__ == '__main__':
    root = tk.Tk()
    app = SmashOrPassApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()