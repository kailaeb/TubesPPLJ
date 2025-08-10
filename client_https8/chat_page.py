import os
import base64
import weakref # <--- ADD THIS IMPORT
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFrame, QScrollArea, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSlot, QTimer
from PyQt5.QtGui import QPixmap

class ChatPage(QWidget):
    """
    Final Chat page with support for text, image, and file messages,
    including timestamps and proper sent-image previews.
    """
    
    def __init__(self, current_user_info, friend_info, backend, parent=None):
        super().__init__(parent)
        self.current_user_info = current_user_info
        self.friend_info = friend_info
        self.backend = backend
        self.room_id = None
        self.setup_ui()
        self.connect_backend_signals()

        peer_id = self.friend_info.get('user_id')
        if peer_id:
            self.backend.find_or_create_room(peer_id)
        else:
            self.show_system_message("Error: Could not identify friend.")

    def showEvent(self, event):
        """Called when the widget is shown."""
        super().showEvent(event)
        self.backend.start_polling_for_messages()

    def hideEvent(self, event):
        """Called when the widget is hidden."""
        super().hideEvent(event)
        self.backend.stop_polling()
        
    def connect_backend_signals(self):
        self.backend.room_info_fetched.connect(self.on_room_info_received)
        self.backend.message_history_fetched.connect(self.on_message_history_received)
        self.backend.message_sent_response.connect(self.on_message_sent)
        self.backend.new_messages_received.connect(self.on_new_messages)

    def setup_ui(self):
        # This method remains unchanged from the previous step.
        # It sets up the header, scroll area, and input area.
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("QFrame { background-color: #E8E1E1; border-bottom: 1px solid #B0C4C6; }")
        header_layout = QHBoxLayout(header)
        friend_name_label = QLabel(self.friend_info.get('username', 'Chat'))
        friend_name_label.setStyleSheet("QLabel { font-size: 22px; font-weight: bold; color: #2C2C2C; padding-left: 15px; }")
        header_layout.addWidget(friend_name_label)
        header_layout.addStretch()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #F0F2F5; }")
        self.message_container = QWidget()
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(15, 15, 15, 15)
        self.message_layout.setSpacing(10)
        self.message_layout.addStretch()
        self.scroll_area.setWidget(self.message_container)
        input_area = QFrame()
        input_area.setFixedHeight(70)
        input_area.setStyleSheet("QFrame { background-color: #E8E1E1; border-top: 1px solid #B0C4C6; }")
        input_area_layout = QHBoxLayout(input_area)
        input_area_layout.setContentsMargins(15, 10, 15, 10)
        input_area_layout.setSpacing(10)
        attach_button = QPushButton("📎")
        attach_button.setFixedSize(40, 40)
        attach_button.setStyleSheet("QPushButton { font-size: 20px; border-radius: 20px; }")
        attach_button.clicked.connect(self.attach_file)
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.setStyleSheet("QLineEdit { border: 1px solid #B0C4C6; border-radius: 18px; padding: 10px 15px; font-size: 16px; }")
        self.message_input.returnPressed.connect(self.send_text_message)
        send_button = QPushButton("Send")
        send_button.setFixedSize(80, 40)
        send_button.setStyleSheet("QPushButton { background-color: #7A9499; color: white; border: none; border-radius: 20px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #6B8387; }")
        send_button.clicked.connect(self.send_text_message)
        input_area_layout.addWidget(attach_button)
        input_area_layout.addWidget(self.message_input)
        input_area_layout.addWidget(send_button)
        main_layout.addWidget(header)
        main_layout.addWidget(self.scroll_area)
        main_layout.addWidget(input_area)

    @pyqtSlot(dict)
    def on_room_info_received(self, data):
        if data.get("status") == "success":
            self.room_id = data.get("room_id")
            print(f"UI: Got room_id: {self.room_id}. Now fetching messages.")
            self.backend.get_messages(self.room_id)
        else:
            self.show_system_message(f"Error creating chat room: {data.get('message')}")

    @pyqtSlot(dict)
    def on_message_history_received(self, data):
        if data.get("status") == "success" and str(data.get("room_id")) == str(self.room_id):
            print(f"UI: Received {len(data.get('messages',[]))} messages.")
            self.clear_messages()
            for message in data.get("messages", []):
                self.add_message_to_display(message)
            QTimer.singleShot(100, self.scroll_to_bottom)

    @pyqtSlot(list)
    def on_new_messages(self, messages):
        """Handles new messages received from the long polling connection."""
        for message in messages:
            if message and str(message.get("room_id")) == str(self.room_id):
                print(f"UI: Received new message for this room: {message.get('content')}")
                self.add_message_to_display(message)
                self.scroll_to_bottom()

    @pyqtSlot(dict)
    def on_message_sent(self, data):
        # This slot now primarily serves as a confirmation log.
        if data.get("status") == "success":
            print("UI: Message sent to server successfully.")
        else:
            self.show_system_message(f"Failed to send message: {data.get('message')}")

    def send_text_message(self):
        message_text = self.message_input.text().strip()
        if not message_text or not self.room_id: return
        message_data = {"type": "text", "content": message_text, "filename": None}
        self.backend.send_message(self.room_id, message_data)
        self.optimistically_add_message(message_text, 'text')
        self.message_input.clear()

    def attach_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a file or image to send")
        if not file_path: return

        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            base64_content = base64.b64encode(file_content).decode('utf-8')
            filename = os.path.basename(file_path)
            image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
            message_type = 'image' if any(filename.lower().endswith(ext) for ext in image_extensions) else 'file'

            message_data = {"type": message_type, "content": base64_content, "filename": filename}
            self.backend.send_message(self.room_id, message_data)
            
            # --- FIX: Pass the full local file path for instant image preview ---
            content_for_preview = file_path if message_type == 'image' else filename
            self.optimistically_add_message(content_for_preview, message_type)

        except Exception as e:
            print(f"Error attaching file: {e}")

    def optimistically_add_message(self, content, msg_type):
        """Adds a sent message to the UI immediately for a snappy feel."""
        my_message = {
            "sender_id": self.current_user_info.get('user_id'),
            "content": content,
            "type": msg_type,
            "filename": content if msg_type != 'text' else None,
            # --- FIX: Add a client-side timestamp ---
            "timestamp": datetime.now().strftime("%I:%M %p").lower()
        }
        self.add_message_to_display(my_message)
        self.scroll_to_bottom()

    def add_message_to_display(self, message_data):
        """Creates and adds a message bubble based on the message type."""
        is_mine = message_data.get('sender_id') == self.current_user_info.get('user_id')
        msg_type = message_data.get('type', 'text')
        
        bubble = QFrame()
        bubble_layout = QVBoxLayout(bubble)
        bubble.setStyleSheet(f"""
            QFrame {{
                background-color: {'#D9FDD3' if is_mine else 'white'};
                color: #333;
                padding: 1px 1px;
                border-radius: 15px;
                border: 1px solid {'#C5EABA' if is_mine else '#E0E0E0'};
            }}
        """)
        
        content_widget = None
        
        # --- NEW LOGIC: Create bubble content based on message type ---
        if msg_type == 'text':
            content_widget = QLabel(message_data.get('content'))
            content_widget.setWordWrap(True)

        elif msg_type == 'image':
            image_path = message_data.get('content')
            content_widget = QLabel("Loading image...")
            content_widget.setMinimumSize(200, 150)
            content_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # --- FIX: Check if the path is a local file (for sent images) or a server URL ---
            if os.path.exists(image_path): # It's a local file we just sent
                pixmap = QPixmap(image_path)
                content_widget.setPixmap(pixmap.scaled(300, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else: # It's a path from the server, download it
                self.load_image_for_bubble(image_path, content_widget)

        elif msg_type == 'file':
            # This widget will act as the container for the file info and button
            content_widget = QWidget()
            file_layout = QVBoxLayout(content_widget)
            file_layout.setContentsMargins(0,0,0,0)
            file_layout.setSpacing(5)
            
            filename = message_data.get('filename', 'file')
            file_label = QLabel(f"📄 {filename}")
            file_label.setStyleSheet("font-weight: bold;")
            
            save_button = QPushButton("Save As...")
            save_button.setCursor(Qt.PointingHandCursor)
            save_button.setStyleSheet("background-color: transparent; border: none; color: blue; text-decoration: underline;")
            file_path = message_data.get('content')
            save_button.clicked.connect(lambda _, p=file_path, f=filename: self.download_and_save_file(p, f))
            
            file_layout.addWidget(file_label)
            file_layout.addWidget(save_button, alignment=Qt.AlignmentFlag.AlignLeft)

        if content_widget:
            content_widget.setStyleSheet("background-color: transparent; border: none; padding: 8px 12px;")
            bubble_layout.addWidget(content_widget)
        
        # --- FIX: Add timestamp to all bubble types ---
        timestamp_str = message_data.get('timestamp', '')
        # Handle full ISO format from server poll vs. pre-formatted from history/optimistic
        if 'T' in timestamp_str and 'Z' in timestamp_str:
            try:
                # Naively convert UTC to local time. For accuracy, pytz would be needed here too.
                ts_utc = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                timestamp_str = ts_utc.astimezone().strftime("%I:%M %p").lower()
            except ValueError:
                pass # Use the string as is if parsing fails
        
        time_label = QLabel(timestamp_str)
        time_label.setStyleSheet("background-color: transparent; border: none; color: #666; font-size: 11px; padding: 0 12px 4px 12px;")
        bubble_layout.addWidget(time_label)

        # Align the bubble left or right
        message_widget = QWidget()
        hbox = QHBoxLayout(message_widget)
        if is_mine:
            hbox.addStretch()
            hbox.addWidget(bubble)
        else:
            hbox.addWidget(bubble)
            hbox.addStretch()
            
        self.message_layout.insertWidget(self.message_layout.count() - 1, message_widget)
    '''
    def load_image_for_bubble(self, image_path, image_label):
        """Downloads and displays an image in a chat bubble."""
        if not image_path: return

        # Define a slot to handle the downloaded data
        def on_image_downloaded(image_data):
            if image_data:
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                # Scale pixmap to fit while maintaining aspect ratio
                image_label.setPixmap(pixmap.scaled(
                    300, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                ))
            else:
                image_label.setText("Failed to load image.")
        
        # Use a worker thread to download the file without freezing the UI
        self.backend._start_worker(
            lambda: self.backend.download_file_from_url(image_path),
            on_success=on_image_downloaded,
            on_error=lambda e: image_label.setText("Error loading image.")
        )
    '''
    def load_image_for_bubble(self, image_path, image_label):
        """
        Downloads and displays an image in a chat bubble using a weak reference
        to prevent crashes if the bubble is deleted during download.
        """
        if not image_path: return

        # --- FIX: Create a weak reference to the label ---
        # This allows us to safely check if it still exists later.
        label_ref = weakref.ref(image_label)

        def on_image_downloaded(image_data):
            # --- FIX: Check if the label still exists before updating it ---
            active_label = label_ref() # Get the real label from the weak reference
            if not active_label or not image_data:
                # If the label was deleted or download failed, do nothing.
                return 
            
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            active_label.setPixmap(pixmap.scaled(
                300, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        
        # Use a worker thread to download the file without freezing the UI
        self.backend._start_worker(
            lambda: self.backend.download_file_from_url(image_path),
            on_success=on_image_downloaded,
            on_error=lambda e: print(f"Error loading image: {e}")
        )
    def download_and_save_file(self, file_path, original_filename):
        """Downloads a file and opens a 'Save As' dialog."""
        # Open 'Save As' dialog first
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File As...", original_filename)
        if not save_path:
            return

        def on_file_downloaded(file_data):
            if file_data:
                try:
                    with open(save_path, 'wb') as f:
                        f.write(file_data)
                    print(f"File saved successfully to {save_path}")
                except Exception as e:
                    print(f"Error saving file: {e}")
        
        self.backend._start_worker(
            lambda: self.backend.download_file_from_url(file_path),
            on_success=on_file_downloaded,
            on_error=lambda e: print(f"Error downloading file for saving: {e}")
        )
    
    def show_system_message(self, text):
        sys_label = QLabel(text)
        sys_label.setAlignment(Qt.AlignCenter)
        sys_label.setStyleSheet("QLabel { color: #888; font-style: italic; padding: 10px; }")
        self.message_layout.insertWidget(self.message_layout.count() - 1, sys_label)

    def clear_messages(self):
        # Clears all message widgets from the layout
        while self.message_layout.count() > 1: # Keep the stretch item
            item = self.message_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def scroll_to_bottom(self):
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )