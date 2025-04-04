import sys

from PyQt5 import uic
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
                             QMessageBox)
from classes.SignalHandler import SignalHandler
from classes.ChatClient import ChatClient
from utils.resource_path import resource_path
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore

# Load the UI file
FormClass, BaseClass = uic.loadUiType(resource_path('assets/chat_client.ui'))


class ChatTab(QWidget):
    """Tab for either public chat or a private conversation"""

    def __init__(self, recipient=None, is_public=False):
        super().__init__()
        self.recipient = recipient
        self.is_public = is_public
        self.unread_count = 0

        layout = QVBoxLayout()

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        # Message input area (only for active tabs)
        if recipient is not None or is_public:
            input_layout = QHBoxLayout()

            self.message_input = QLineEdit()
            self.message_input.setPlaceholderText(
                f"Type your message to {'everyone' if is_public else recipient}...")

            self.send_btn = QPushButton("Send")

            input_layout.addWidget(self.message_input)
            input_layout.addWidget(self.send_btn)

            layout.addLayout(input_layout)

        self.setLayout(layout)

    def add_message(self, sender, message, is_private=False, is_self=False):
        """Add a message to the chat display"""
        self.chat_display.moveCursor(self.chat_display.textCursor().End)

        # Format based on message type
        if is_self:
            # Messages from self
            format_str = f"<b style='color:blue'>{sender}:</b> {message}"
        elif sender.startswith("SERVER:"):
            # Server messages
            format_str = f"<i style='color:gray'>{sender} {message}</i>"
        elif is_private:
            # Private messages from others
            format_str = f"<b style='color:purple'>{sender} (private):</b> {message}"
        else:
            # Regular messages from others
            format_str = f"<b>{sender}:</b> {message}"

        self.chat_display.insertHtml(f"{format_str}<br>")
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def increment_unread(self):
        """Increment unread message count"""
        self.unread_count += 1
        return self.unread_count


class ChatWindow(BaseClass, FormClass):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon(
            resource_path("assets/icons/client_icon.png")))
        # disable maximize button
        self.setWindowFlags(self.windowFlags() & ~
                            QtCore.Qt.WindowMaximizeButtonHint)

        self.client = None
        self.signal_handler = SignalHandler()
        self.signal_handler.message_received.connect(self.handle_message)
        self.signal_handler.connection_error.connect(
            self.handle_connection_error)
        self.signal_handler.user_list_updated.connect(self.update_user_list)

        self.private_chats = {}  # {username: tab_index}

        # Connect UI signals
        self.connectButton.clicked.connect(self.toggle_connection)
        self.userList.itemDoubleClicked.connect(self.open_private_chat)
        self.chatTabs.tabCloseRequested.connect(self.close_tab)
        self.chatTabs.currentChanged.connect(self.tab_changed)
        self.publicMessageInput.returnPressed.connect(self.send_public_message)
        self.publicSendButton.clicked.connect(self.send_public_message)

        # Store public chat tab references
        self.public_chat_tab = self.publicChatTab
        self.public_chat_display = self.publicChatDisplay
        self.public_message_input = self.publicMessageInput
        self.public_send_btn = self.publicSendButton

        # Set initial sizes for the splitter (30% user list, 70% chat)
        self.mainSplitter.setSizes(
            [int(self.width() * 0.3), int(self.width() * 0.7)])

        # Enable/disable UI elements based on connection state
        self.update_ui_state(False)

    def update_ui_state(self, connected):
        """Update UI elements based on connection state"""
        self.publicMessageInput.setEnabled(connected)
        self.publicSendButton.setEnabled(connected)

        # Update private chat tabs if any
        for i in range(1, self.chatTabs.count()):
            tab = self.chatTabs.widget(i)
            if hasattr(tab, 'message_input'):
                tab.message_input.setEnabled(connected)
                tab.send_btn.setEnabled(connected)

        # Enable/disable connection inputs
        self.serverInput.setEnabled(not connected)
        self.tcpPortInput.setEnabled(not connected)
        self.udpPortInput.setEnabled(not connected)
        self.usernameInput.setEnabled(not connected)
        self.tcpRadio.setEnabled(not connected)
        self.udpRadio.setEnabled(not connected)

        # Update connect button text
        self.connectButton.setText("Disconnect" if connected else "Connect")

        # Clear user list if disconnected
        if not connected:
            self.userList.clear()

    def toggle_connection(self):
        if self.client and self.client.connected:
            # Disconnect
            self.client.disconnect()
            self.client = None
            self.update_ui_state(False)
            self.add_message_to_public_chat(
                "SERVER:", "Disconnected from server")

        else:
            # Connect
            protocol = "TCP" if self.tcpRadio.isChecked() else "UDP"
            host = self.serverInput.text()
            port = int(self.tcpPortInput.text()) if protocol == "TCP" else int(
                self.udpPortInput.text())
            username = self.usernameInput.text()

            if not username:
                QMessageBox.warning(self, "Input Error",
                                    "Please enter a username.")
                return

            # Create client
            self.client = ChatClient(
                protocol, host, port, username, self.signal_handler)

            if self.client.connect():
                self.update_ui_state(True)
                self.add_message_to_public_chat(
                    "SERVER:", f"Connecting to server via {protocol}...")

                # Update protocol info
                protocol_text = f"<b>Currently using: {protocol}</b><br><br>"
                if protocol == "TCP":
                    protocol_text += (
                        "- Messages are guaranteed to be delivered in order<br>"
                        "- Connection-oriented with handshaking<br>"
                        "- Higher overhead but reliable"
                    )
                else:
                    protocol_text += (
                        "- Messages may arrive out of order or be lost<br>"
                        "- Connectionless with no handshaking<br>"
                        "- Lower overhead but less reliable"
                    )
                self.protocolInfo.setHtml(protocol_text)
            else:
                self.client = None

    def send_public_message(self):
        """Send a message to the public chat"""
        if not self.client or not self.client.connected:
            return

        message = self.publicMessageInput.text().strip()
        if not message:
            return

        if self.client.send_message(message):
            self.add_message_to_public_chat(
                self.client.username, message, is_self=True)
            self.publicMessageInput.clear()

    def send_private_message(self, recipient):
        """Send a private message to a specific recipient"""
        if not self.client or not self.client.connected:
            return

        # Find the tab for this recipient
        if recipient in self.private_chats:
            tab_index = self.private_chats[recipient]
            tab = self.chatTabs.widget(tab_index)

            message = tab.message_input.text().strip()
            if not message:
                return

            if self.client.send_message(message, recipient):
                # Display in our own chat
                tab.add_message(self.client.username, message,
                                is_private=True, is_self=True)
                tab.message_input.clear()

    def add_message_to_public_chat(self, sender, message, is_self=False):
        """Add a message to the public chat tab"""
        self.publicChatDisplay.moveCursor(
            self.publicChatDisplay.textCursor().End)

        # Format based on message type
        if is_self:
            # Messages from self
            format_str = f"<b style='color:blue'>{sender}:</b> {message}"
        elif sender.startswith("SERVER:"):
            # Server messages
            format_str = f"<i style='color:gray'>{sender} {message}</i>"
        else:
            # Regular messages from others
            format_str = f"<b>{sender}:</b> {message}"

        self.publicChatDisplay.insertHtml(f"{format_str}<br>")
        self.publicChatDisplay.verticalScrollBar().setValue(
            self.publicChatDisplay.verticalScrollBar().maximum()
        )

    def open_private_chat(self, item):
        """Open or focus a private chat tab with the selected user"""
        recipient = item.text()

        # Don't allow chatting with yourself
        if recipient == self.client.username:
            QMessageBox.information(
                self, "Private Chat", "You cannot start a chat with yourself.")
            return

        # Check if chat already exists
        if recipient in self.private_chats:
            self.chatTabs.setCurrentIndex(self.private_chats[recipient])
            return

        # Create new chat tab
        new_tab = ChatTab(recipient=recipient, is_public=False)
        tab_index = self.chatTabs.addTab(new_tab, recipient)
        self.private_chats[recipient] = tab_index

        # Connect signals for this tab
        new_tab.message_input.returnPressed.connect(
            lambda: self.send_private_message(recipient))
        new_tab.send_btn.clicked.connect(
            lambda: self.send_private_message(recipient))

        # Switch to the new tab
        self.chatTabs.setCurrentIndex(tab_index)

    def close_tab(self, index):
        """Close a chat tab"""
        # Don't allow closing the public chat
        if index == 0:
            return

        # Find which user this tab belongs to
        tab = self.chatTabs.widget(index)
        recipient = tab.recipient

        # Remove from tracking
        if recipient in self.private_chats:
            del self.private_chats[recipient]

        # Close the tab
        self.chatTabs.removeTab(index)

        # Update indices for remaining private chats
        for username, tab_idx in list(self.private_chats.items()):
            if tab_idx > index:
                self.private_chats[username] = tab_idx - 1

    def tab_changed(self, index):
        """Reset unread counter when switching to a tab"""
        if index >= 0:
            tab = self.chatTabs.widget(index)
            if hasattr(tab, 'unread_count'):
                tab.unread_count = 0
                if index == 0:
                    self.chatTabs.setTabText(index, "Public Chat")
                elif hasattr(tab, 'recipient'):
                    self.chatTabs.setTabText(index, tab.recipient)

    def update_tab_title(self, index):
        """Update tab title with unread message count"""
        tab = self.chatTabs.widget(index)
        if hasattr(tab, 'unread_count') and tab.unread_count > 0:
            if index == 0:
                self.chatTabs.setTabText(
                    index, f"Public Chat ({tab.unread_count})")
            elif hasattr(tab, 'recipient'):
                self.chatTabs.setTabText(
                    index, f"{tab.recipient} ({tab.unread_count})")

    def update_user_list(self, users):
        """Update the list of online users"""
        self.userList.clear()
        for username in sorted(users):
            # Don't add yourself to the list
            if self.client and username != self.client.username:
                self.userList.addItem(username)

    def handle_message(self, data):
        """Handle received messages based on their type"""
        message_type = data.get('type', 'legacy')

        if message_type == 'public':
            # Public message
            sender = data.get('from', 'Unknown')
            message = data.get('message', '')

            # Display in public chat
            self.add_message_to_public_chat(sender, message)

            # If not viewing the public chat, update unread count
            if self.chatTabs.currentIndex() != 0:
                # Create unread_count attribute for public chat tab if it doesn't exist
                if not hasattr(self.public_chat_tab, 'unread_count'):
                    self.public_chat_tab.unread_count = 0

                self.public_chat_tab.unread_count = self.public_chat_tab.unread_count + 1
                self.chatTabs.setTabText(
                    0, f"Public Chat ({self.public_chat_tab.unread_count})")

        elif message_type == 'private':
            # Private message received
            sender = data.get('from', 'Unknown')
            message = data.get('message', '')

            # Check if we have a tab open for this sender
            if sender in self.private_chats:
                tab_index = self.private_chats[sender]
                tab = self.chatTabs.widget(tab_index)
                tab.add_message(sender, message, is_private=True)

                # If not viewing this tab, update unread count
                if self.chatTabs.currentIndex() != tab_index:
                    tab.increment_unread()
                    self.update_tab_title(tab_index)
            else:
                # Create new tab for this sender
                new_tab = ChatTab(recipient=sender, is_public=False)
                tab_index = self.chatTabs.addTab(new_tab, sender)
                self.private_chats[sender] = tab_index

                # Add the message
                new_tab.add_message(sender, message, is_private=True)

                # Connect signals for this tab
                new_tab.message_input.returnPressed.connect(
                    lambda: self.send_private_message(sender))
                new_tab.send_btn.clicked.connect(
                    lambda: self.send_private_message(sender))

                # Update unread count
                new_tab.increment_unread()
                self.update_tab_title(tab_index)

        elif message_type == 'private_sent':
            # Confirmation of private message sent
            # We don't need to display anything here since we already
            # displayed the message when sending
            pass

        elif message_type == 'server':
            # Server message
            message = data.get('message', '')
            self.add_message_to_public_chat("SERVER:", message)

        elif message_type == 'error':
            # Error message
            message = data.get('message', '')
            QMessageBox.warning(self, "Server Error", message)

        elif message_type == 'legacy':
            # Legacy plain text message (backwards compatibility), for DECODE ERROS
            message = data.get('message', '')

            # Try to parse SERVER: prefix
            if message.startswith("SERVER:"):
                parts = message.split(":", 1)
                sender = parts[0]
                msg = parts[1].strip() if len(parts) > 1 else ""
                self.add_message_to_public_chat(sender, msg)
            else:
                # Try to parse username: message format
                parts = message.split(":", 1)
                if len(parts) > 1:
                    sender = parts[0]
                    msg = parts[1].strip()
                    self.add_message_to_public_chat(sender, msg)
                else:
                    # Just display as is
                    self.add_message_to_public_chat("SERVER:", message)

    def handle_connection_error(self, error_message):
        QMessageBox.warning(self, "Connection Error", error_message)

        # Reset UI
        if self.client:
            self.client.disconnect()
            self.client = None

        self.update_ui_state(False)

    def closeEvent(self, event):
        # Clean up before closing
        if self.client:
            self.client.disconnect()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec_())
