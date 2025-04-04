import json
import socket
import threading
import time


class ChatClient:
    def __init__(self, protocol, host, port, username, signal_handler):
        self.protocol = protocol
        self.host = host
        self.port = port
        self.username = username
        self.signal_handler = signal_handler
        self.connected = False
        self.socket = None
        self.udp_heartbeat_interval = 5  # seconds

    def connect(self):
        try:
            if self.protocol == "TCP":
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                self.connected = True

                self.socket.send(json.dumps({
                    "username": self.username
                }).encode('utf-8'))

                threading.Thread(target=self.receive_tcp, daemon=True).start()

            elif self.protocol == "UDP":
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.server_address = (self.host, self.port)
                self.connected = True

                # Register with server
                self.socket.sendto(json.dumps({
                    "type": "register",
                    "username": self.username
                }).encode('utf-8'), self.server_address)

                # Start listener and heartbeat
                threading.Thread(target=self.receive_udp, daemon=True).start()
                threading.Thread(target=self.udp_heartbeat,
                                 daemon=True).start()

            return True
        except Exception as e:
            self.signal_handler.connection_error.emit(
                f"Connection error: {str(e)}")
            return False

    def disconnect(self):
        if self.connected and self.socket:
            self.connected = False
            try:
                if self.protocol == "TCP":
                    self.socket.close()
                # For UDP, just stop sending heartbeats
            except:
                pass

    def send_message(self, message, recipient=None):
        if not self.connected or not self.socket:
            return False

        try:
            if recipient:  # Private message
                if self.protocol == "TCP":
                    data = json.dumps({
                        "type": "private",
                        "to": recipient,
                        "message": message
                    }).encode('utf-8')
                    self.socket.send(data)

                elif self.protocol == "UDP":
                    data = json.dumps({
                        "type": "private",
                        "to": recipient,
                        "message": message
                    }).encode('utf-8')
                    self.socket.sendto(data, self.server_address)

            else:  # Public message
                if self.protocol == "TCP":
                    data = json.dumps({
                        "type": "message",
                        "message": message
                    }).encode('utf-8')
                    self.socket.send(data)

                elif self.protocol == "UDP":
                    data = json.dumps({
                        "type": "message",
                        "message": message
                    }).encode('utf-8')
                    self.socket.sendto(data, self.server_address)

            return True

        except Exception as e:
            self.signal_handler.connection_error.emit(
                f"Error sending message: {str(e)}")
            self.connected = False
            return False

    def process_message(self, data_str):
        """Process received message and emit appropriate signals"""
        try:
            data = json.loads(data_str)

            # Handle user list updates
            if data.get('type') == 'user_list':
                user_list = data.get('users', [])
                self.signal_handler.user_list_updated.emit(user_list)
                return

            # Handle all other messages
            self.signal_handler.message_received.emit(data)

        except json.JSONDecodeError:
            self.signal_handler.message_received.emit({
                "type": "legacy",
                "message": data_str
            })

    def receive_tcp(self):
        while self.connected:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break

                message = data.decode('utf-8')
                self.process_message(message)

            except Exception as e:
                if self.connected:  # Only show error if we're supposed to be connected
                    self.signal_handler.connection_error.emit(
                        f"Connection lost: {str(e)}")
                break

        self.connected = False

    def receive_udp(self):
        # 10 seconds timeout to check connected flag
        self.socket.settimeout(10)

        while self.connected:
            try:
                data, addr = self.socket.recvfrom(1024)
                message = data.decode('utf-8')
                self.process_message(message)

            except socket.timeout:
                # Timeout
                continue
            except Exception as e:
                if self.connected:  # Only show error if we're supposed to be connected
                    self.signal_handler.connection_error.emit(
                        f"UDP error: {str(e)}")
                break

        self.connected = False

    def udp_heartbeat(self):
        while self.connected:
            try:
                self.socket.sendto(json.dumps({
                    "type": "heartbeat",
                    "username": self.username
                }).encode('utf-8'), self.server_address)
            except:
                pass

            time.sleep(self.udp_heartbeat_interval)
