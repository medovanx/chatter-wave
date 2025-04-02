import socket
import threading
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class ChatServer:
    def __init__(self, host='0.0.0.0', tcp_port=9090, udp_port=9091):
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port

        # TCP setup
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind((self.host, self.tcp_port))

        # UDP setup
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host, self.udp_port))

        # Client management
        self.tcp_clients = {}  # {client_socket: {'username': username, 'address': address}}
        self.udp_clients = {}  # {address: username}

        # Username to socket/address mapping for private messaging
        self.username_to_tcp_socket = {}  # {username: client_socket}
        self.username_to_udp_address = {}  # {username: address}

        # Online users list
        self.online_users = set()

        logging.info(
            f"Server initialized on {host} (TCP: {tcp_port}, UDP: {udp_port})")

    def broadcast_tcp(self, message, exclude_client=None):
        """Send message to all TCP clients except the sender"""
        disconnected_clients = []

        for client_socket in self.tcp_clients:
            if client_socket != exclude_client:
                try:
                    client_socket.send(message.encode('utf-8'))
                except:
                    disconnected_clients.append(client_socket)

        # Clean up disconnected clients
        for client in disconnected_clients:
            self.remove_tcp_client(client)

    def broadcast_udp(self, message, exclude_address=None):
        """Send message to all UDP clients except the sender"""
        for address in self.udp_clients:
            if address != exclude_address:
                self.udp_socket.sendto(message.encode('utf-8'), address)

    def broadcast_user_list(self):
        """Broadcast the list of online users to all clients"""
        user_list = list(self.online_users)
        user_list_msg = json.dumps({
            "type": "user_list",
            "users": user_list
        })

        # Send to all TCP clients
        for client_socket in self.tcp_clients:
            try:
                client_socket.send(user_list_msg.encode('utf-8'))
            except:
                pass

        # Send to all UDP clients
        for address in self.udp_clients:
            try:
                self.udp_socket.sendto(user_list_msg.encode('utf-8'), address)
            except:
                pass

    def remove_tcp_client(self, client_socket):
        """Remove a TCP client and update user lists"""
        if client_socket in self.tcp_clients:
            username = self.tcp_clients[client_socket]['username']

            # Remove from mappings
            del self.tcp_clients[client_socket]
            if username in self.username_to_tcp_socket:
                del self.username_to_tcp_socket[username]

            # Update online users if the user is not connected via UDP
            if username not in self.username_to_udp_address:
                self.online_users.discard(username)
                self.broadcast_user_list()

            # Inform other clients
            self.broadcast_tcp(f"SERVER: {username} left the chat!")
            logging.info(f"TCP client disconnected: {username}")

    def remove_udp_client(self, address):
        """Remove a UDP client and update user lists"""
        if address in self.udp_clients:
            username = self.udp_clients[address]

            # Remove from mappings
            del self.udp_clients[address]
            if username in self.username_to_udp_address:
                del self.username_to_udp_address[username]

            # Update online users if the user is not connected via TCP
            if username not in self.username_to_tcp_socket:
                self.online_users.discard(username)
                self.broadcast_user_list()

            # Inform other clients
            self.broadcast_udp(f"SERVER: {username} left the chat!")
            logging.info(f"UDP client disconnected: {username}")

    def send_private_message_tcp(self, from_username, to_username, message_content):
        """Send a private message to a TCP client"""
        if to_username in self.username_to_tcp_socket:
            try:
                formatted_msg = json.dumps({
                    "type": "private",
                    "from": from_username,
                    "message": message_content
                })
                self.username_to_tcp_socket[to_username].send(
                    formatted_msg.encode('utf-8'))
                return True
            except:
                logging.error(
                    f"Failed to send private message to TCP user {to_username}")
                return False
        return False

    def send_private_message_udp(self, from_username, to_username, message_content):
        """Send a private message to a UDP client"""
        if to_username in self.username_to_udp_address:
            try:
                formatted_msg = json.dumps({
                    "type": "private",
                    "from": from_username,
                    "message": message_content
                })
                self.udp_socket.sendto(formatted_msg.encode(
                    'utf-8'), self.username_to_udp_address[to_username])
                return True
            except:
                logging.error(
                    f"Failed to send private message to UDP user {to_username}")
                return False
        return False

    def handle_tcp_client(self, client_socket, address):
        """Handle TCP client connection"""
        try:
            # Get username
            username_data = client_socket.recv(1024).decode('utf-8')
            username_info = json.loads(username_data)
            username = username_info['username']

            # Store client info
            self.tcp_clients[client_socket] = {
                'username': username, 'address': address}
            self.username_to_tcp_socket[username] = client_socket
            self.online_users.add(username)

            # Welcome message
            welcome_msg = f"SERVER: {username} joined via TCP!"
            logging.info(f"New TCP connection: {username} from {address}")
            self.broadcast_tcp(welcome_msg, client_socket)

            # Send welcome message to the client
            client_socket.send(json.dumps({
                "type": "server",
                "message": f"Welcome {username}! You are connected via TCP."
            }).encode('utf-8'))

            # Send user list to all clients
            self.broadcast_user_list()

            while True:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break

                    message = data.decode('utf-8')
                    message_data = json.loads(message)

                    # Handle different message types
                    if message_data.get('type') == 'private':
                        # Private message
                        to_username = message_data.get('to')
                        msg_content = message_data.get('message')

                        logging.info(
                            f"Private message from {username} to {to_username}")

                        # Try to send via TCP first, then UDP
                        tcp_sent = self.send_private_message_tcp(
                            username, to_username, msg_content)
                        udp_sent = False
                        if not tcp_sent:
                            udp_sent = self.send_private_message_udp(
                                username, to_username, msg_content)

                        # Send confirmation to sender
                        if tcp_sent or udp_sent:
                            confirm_msg = json.dumps({
                                "type": "private_sent",
                                "to": to_username,
                                "message": msg_content
                            })
                            client_socket.send(confirm_msg.encode('utf-8'))
                        else:
                            error_msg = json.dumps({
                                "type": "error",
                                "message": f"User {to_username} is not online."
                            })
                            client_socket.send(error_msg.encode('utf-8'))

                    else:  # Public message
                        formatted_msg = json.dumps({
                            "type": "public",
                            "from": username,
                            "message": message_data.get('message', '')
                        })

                        logging.info(
                            f"Public message from {username}: {message_data.get('message', '')}")

                        # Broadcast to all TCP clients
                        self.broadcast_tcp(formatted_msg, client_socket)

                        # Also broadcast to UDP clients
                        self.broadcast_udp(formatted_msg)

                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logging.error(f"TCP client error: {str(e)}")
                    break
        except Exception as e:
            logging.error(f"Error handling TCP client: {str(e)}")
        finally:
            # Clean up on disconnect
            self.remove_tcp_client(client_socket)
            client_socket.close()

    def handle_udp(self):
        """Handle UDP messages"""
        while True:
            try:
                data, address = self.udp_socket.recvfrom(1024)
                message = data.decode('utf-8')

                try:
                    message_data = json.loads(message)
                    message_type = message_data.get('type', '')

                    if message_type == 'register':
                        # New UDP client registration
                        username = message_data['username']

                        # Store client info
                        self.udp_clients[address] = username
                        self.username_to_udp_address[username] = address
                        self.online_users.add(username)

                        # Inform clients
                        welcome_msg = f"SERVER: {username} joined via UDP!"
                        logging.info(
                            f"New UDP client: {username} from {address}")

                        # Broadcast join message
                        self.broadcast_tcp(welcome_msg)
                        self.broadcast_udp(welcome_msg, address)

                        # Welcome the new client
                        self.udp_socket.sendto(
                            json.dumps({
                                "type": "server",
                                "message": f"Welcome {username}! You are connected via UDP."
                            }).encode('utf-8'),
                            address
                        )

                        # Send user list to all clients
                        self.broadcast_user_list()

                    elif message_type == 'heartbeat':
                        # Client is still alive
                        if address in self.udp_clients:
                            # If this is a reconnection, update the mapping
                            username = message_data.get('username')
                            if username and self.udp_clients[address] != username:
                                old_username = self.udp_clients[address]
                                self.udp_clients[address] = username
                                self.username_to_udp_address[username] = address

                                # Remove old mapping
                                if old_username in self.username_to_udp_address:
                                    del self.username_to_udp_address[old_username]

                                # Update online users
                                self.online_users.discard(old_username)
                                self.online_users.add(username)
                                self.broadcast_user_list()

                    elif message_type == 'message':
                        # Regular public message
                        if address in self.udp_clients:
                            username = self.udp_clients[address]
                            formatted_msg = json.dumps({
                                "type": "public",
                                "from": username,
                                "message": message_data.get('message', '')
                            })

                            logging.info(
                                f"UDP public message from {username}: {message_data.get('message', '')}")

                            # Send to all clients
                            self.broadcast_udp(formatted_msg, address)
                            self.broadcast_tcp(formatted_msg)

                    elif message_type == 'private':
                        # Private message
                        if address in self.udp_clients:
                            from_username = self.udp_clients[address]
                            to_username = message_data.get('to')
                            msg_content = message_data.get('message')

                            logging.info(
                                f"UDP private message from {from_username} to {to_username}")

                            # Try to send via TCP first, then UDP
                            tcp_sent = self.send_private_message_tcp(
                                from_username, to_username, msg_content)
                            udp_sent = False
                            if not tcp_sent:
                                udp_sent = self.send_private_message_udp(
                                    from_username, to_username, msg_content)

                            # Send confirmation to sender
                            if tcp_sent or udp_sent:
                                confirm_msg = json.dumps({
                                    "type": "private_sent",
                                    "to": to_username,
                                    "message": msg_content
                                })
                                self.udp_socket.sendto(
                                    confirm_msg.encode('utf-8'), address)
                            else:
                                error_msg = json.dumps({
                                    "type": "error",
                                    "message": f"User {to_username} is not online."
                                })
                                self.udp_socket.sendto(
                                    error_msg.encode('utf-8'), address)

                except json.JSONDecodeError:
                    logging.warning(f"Invalid JSON from UDP client: {address}")

            except Exception as e:
                logging.error(f"UDP error: {str(e)}")

    def run(self):
        """Start the server"""
        # Start UDP handler
        udp_thread = threading.Thread(target=self.handle_udp)
        udp_thread.daemon = True
        udp_thread.start()

        # Start TCP listener
        self.tcp_socket.listen(5)
        logging.info("Server is running and listening for connections...")

        while True:
            client_socket, address = self.tcp_socket.accept()
            client_thread = threading.Thread(
                target=self.handle_tcp_client, args=(client_socket, address))
            client_thread.daemon = True
            client_thread.start()


if __name__ == '__main__':
    server = ChatServer()
    try:
        server.run()
    except KeyboardInterrupt:
        logging.info("Server shutting down...")
    except Exception as e:
        logging.error(f"Server error: {str(e)}")
