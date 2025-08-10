# home_page.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame)
from PyQt5.QtCore import Qt, pyqtSlot
from datetime import datetime

class HomePage(QWidget):
    """
    A content-only widget for the main home screen.
    It does NOT build its own sidebar.
    """
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.setup_ui()
        # Note: We remove the backend connections as this page is now static.
        # If you add dynamic content later, you can add them back.

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Welcome Header ---
        welcome_label = QLabel("Welcome to your Messenger")
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #2C2C2C;
                padding-bottom: 10px;
                border-bottom: 2px solid #7A9499;
            }
        """)
        
        # --- Info Panel ---
        info_panel = QFrame()
        info_panel.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border-radius: 15px;
            }
        """)
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(25, 25, 25, 25)

        info_text = QLabel("Select a friend from the 'Friend List' on the left to start chatting.")
        info_text.setWordWrap(True)
        info_text.setStyleSheet("QLabel { font-size: 18px; color: #333; }")
        
        info_layout.addWidget(info_text)

        # --- Add widgets to the main layout ---
        layout.addWidget(welcome_label)
        layout.addWidget(info_panel)
        layout.addStretch()
    
    @pyqtSlot(dict)
    def on_room_info_received(self, data):
        """Handles the fetched room ID from the backend."""
        if data.get("status") == "success":
            # Store the room_id for the current chat
            self.current_chat_room_id = data.get("room_id")
            print(f"UI: Got room_id: {self.current_chat_room_id}. Now fetching messages.")
            # Now that we have the room, get its message history
            self.backend.get_messages(self.current_chat_room_id)
        else:
            print(f"UI: Error getting room info: {data.get('message')}")

    def set_current_chat(self, friend_info):
        """Set current active chat and fetch its room_id and messages."""
        self.current_chat_username = friend_info.get('username')
        self.current_chat_friend_id = friend_info.get('user_id')
        self.current_chat_room_id = None # Reset room_id while we fetch it

        self.update_chat_header(self.current_chat_username)
        self.clear_chat_display() # Clear previous messages
        
        print(f"UI: Set current chat to {self.current_chat_username} (ID: {self.current_chat_friend_id})")

        # --- FIX: Ask the backend to find or create the room ---
        if self.backend and self.current_chat_friend_id:
            self.backend.find_or_create_room(self.current_chat_friend_id)
        
        # Enable the input fields now that a chat is active
        self.message_input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.message_input.setFocus()

    # REPLACE your existing send_message method with this one
    def send_message(self):
        """Send message in the current chat using the stored room_id."""
        if not self.current_chat_username or not hasattr(self, 'current_chat_room_id'):
            return
        
        message_text = self.message_input.text().strip()
        if not message_text:
            return
        
        # --- FIX: Send the room_id, not the username ---
        if self.backend and self.current_chat_room_id:
            self.backend.send_message(self.current_chat_room_id, message_text)
        else:
            print("UI Error: Cannot send message, room_id is not available yet.")
            return # Don't proceed if room_id isn't ready

        # Optimistically add the message to the UI
        current_time = datetime.now().strftime("%I:%M %p").lower()
        self.add_message_to_display({
            'message': message_text,
            'time': current_time,
            'sent': True # Messages we send are always 'sent'
        })
        
        self.message_input.clear()