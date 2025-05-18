# Chatter Wave

A cross-platform chat application built with PyQt5 supporting both TCP and UDP protocols for network communication.

<div align="center">
    <img src="https://i.ibb.co/Z1J7SXwK/client-icon.png" alt="Logo" width="200" height="200">
    <img src="https://i.ibb.co/Y7K28Cb8/server-icon.png" alt="Logo" width="200" height="200">
</div>

<div align="center">

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green.svg)](https://pypi.org/project/PyQt5/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## Features

### Communication Protocols

- **TCP Protocol**: Reliable, connection-oriented communication
- **UDP Protocol**: Lightweight, connectionless communication
- **Protocol Comparison**: In-app explanation of TCP vs UDP differences

### User Interface

- **Tab-Based Chat**: Public chat and private conversation tabs
- **Unread Message Indicators**: Visual notifications for new messages
- **Online User List**: Real-time display of connected users
- **Message Formatting**: Color-coded messages by sender type

### Network Features

- **Configurable Connection**: Customizable host and port settings
- **Username Selection**: Personalized identity in chats
- **Error Handling**: Robust management of network issues
- **Server Notifications**: System messages for user activity

### Client-Server Architecture

- **Multi-Client Support**: Handles multiple simultaneous connections
- **Protocol Mixing**: Manages both TCP and UDP clients
- **Message Routing**: Intelligent message delivery
- **Heartbeat Mechanism**: Connection maintenance for UDP clients

## Screenshots

![Application Main Window](https://i.imgur.com/9QNOrLJ.png)

![Private Chat Tab](https://i.imgur.com/z8UdvLu.png)

## Installation

### Prerequisites

- Python 3.6+
- PyQt5

### Setup

```bash
git clone https://github.com/medovanx/chatter_wave.git
cd chatter_wave
pip install -r requirements.txt
```

Alternatively, you can download pre-compiled executable files from the [Releases](https://github.com/medovanx/chatter_wave/releases) page.

## Usage

### Starting the Server

```bash
python server.py
```

Default ports: TCP 9090, UDP 9091

### Connecting

1. Launch client application: `python chat_client.py`
2. Enter server details and username
3. Select protocol (TCP/UDP)
4. Click "Connect"

### Chatting

- **Public Chat**: Type in main tab
- **Private Chat**: Double-click username to open private tab

## Technical Details

### Code Structure

- **ChatWindow**: Main UI logic
- **ChatTab**: Individual chat tabs
- **ChatClient**: Network communication
- **SignalHandler**: Qt signal management
- **ChatServer**: TCP/UDP server implementation

### Message Format

JSON-formatted messages:

```json
{
  "type": "public|private|server|error|user_list",
  "from": "username",
  "to": "recipient_username",
  "message": "content",
  "users": ["user1", "user2", "..."]
}
```
