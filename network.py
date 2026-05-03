import socket
import threading
import json
import uuid
import hashlib
import base64
import os

def generate_secure_room_key():
    salt = os.urandom(16)
    key = str(uuid.uuid4()).encode()
    hashed = hashlib.pbkdf2_hmac('sha256', key, salt, 100000)
    return base64.urlsafe_b64encode(salt + hashed).decode()[:22]

class Network:
    def __init__(self, host_ip=None, port=55555, room_key=None, username=None):
        self.host_ip = host_ip
        self.port = port
        self.room_key = room_key or generate_secure_room_key()
        self.username = username or "Player"
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.is_host = host_ip is None
        self.clients = {}  # {address: username}
        if self.is_host:
            self.socket.bind(('0.0.0.0', self.port))
        else:
            self.socket.connect((self.host_ip, self.port))
            self.socket.sendto(
                json.dumps({'type': 'join', 'username': self.username, 'room_key': self.room_key}).encode(),
                (self.host_ip, self.port)
            )
        self.running = True
        self.thread = threading.Thread(target=self._listen)
        self.thread.daemon = True
        self.thread.start()
        self.callbacks = {}

    def _listen(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = json.loads(data.decode())
                if message.get('room_key') == self.room_key:
                    if message['type'] == 'join':
                        self.clients[addr] = message['username']
                        if self.is_host:
                            self.send('user_joined', {'username': message['username']}, exclude=addr)
                    elif message['type'] in self.callbacks:
                        self.callbacks[message['type']](message['data'], addr)
            except Exception as e:
                print(f"Network error: {e}")
                break

    def send(self, message_type, data, exclude=None):
        message = json.dumps({
            'type': message_type,
            'data': data,
            'username': self.username,
            'room_key': self.room_key
        }).encode()
        if self.is_host:
            for client in self.clients:
                if exclude and client == exclude:
                    continue
                self.socket.sendto(message, client)
        else:
            self.socket.sendto(message, (self.host_ip, self.port))

    def on(self, message_type, callback):
        self.callbacks[message_type] = callback

    def close(self):
        self.running = False
        self.socket.close()
        self.thread.join()
