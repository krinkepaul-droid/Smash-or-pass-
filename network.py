import socket
import json
import threading

# Constants
SOCKET_TIMEOUT = 5.0
PORT_RANGE = (1, 65535)
USERNAME_LIMIT = 50

# Thread-safe dictionary
shared_dict = threading.Lock()

def validate_username(username):
    if len(username) > USERNAME_LIMIT:
        raise ValueError(f"Username exceeds {USERNAME_LIMIT} characters.")
    return username

def validate_port(port):
    if not (PORT_RANGE[0] <= port <= PORT_RANGE[1]):
        raise ValueError(f"Port must be between {PORT_RANGE[0]} and {PORT_RANGE[1]}.")
    return port

def json_decode(data):
    try:
        return json.loads(data.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError('Invalid JSON data: ' + str(e))

def secure_room_key(room_key):
    # Implement room key security checks here
    pass

def socket_operations(socket_obj):
    try:
        socket_obj.settimeout(SOCKET_TIMEOUT)
        # Socket operations here
    except socket.timeout:
        print('Socket operation timed out.')
    except Exception as e:
        print('Socket error occurred: ' + str(e))

def validate_message_structure(message):
    required_fields = ['type', 'data']  # Example fields
    for field in required_fields:
        if field not in message:
            raise ValueError(f'Missing required field: {field}')
    return message

# Example usage
if __name__ == '__main__':
    username = validate_username('example_user')
    port = validate_port(8080)
    # Add the rest of the implementation here.