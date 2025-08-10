from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QScrollArea, QTextEdit,
                             QFileDialog, QDialog, QGridLayout, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QThread
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QIcon
from navigation_sidebar import NavigationSidebar
import datetime
import json
import asyncio
import websockets
import logging
import ssl
import base64
import os
import mimetypes
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileSelectionDialog(QDialog):
    """Dialog for selecting file or image to send"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file_path = None
        self.file_type = None  # 'image' or 'file'
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the file selection dialog UI"""
        self.setWindowTitle("Send File")
        self.setFixedSize(400, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #E8E1E1;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Choose what to send")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title)
        
        # Buttons
        button_layout = QGridLayout()
        button_layout.setSpacing(15)
        
        # Image button
        image_btn = QPushButton("📷\nSelect Image")
        image_btn.setStyleSheet("""
            QPushButton {
                background-color: #9DB4B8;
                color: #2C2C2C;
                border: none;
                border-radius: 10px;
                padding: 20px;
                font-size: 14px;
                font-weight: bold;
                min-height: 80px;
            }
            QPushButton:hover {
                background-color: #8BA5A9;
            }
        """)
        image_btn.clicked.connect(self.select_image)
        
        # File button
        file_btn = QPushButton("📄\nSelect File")
        file_btn.setStyleSheet("""
            QPushButton {
                background-color: #9DB4B8;
                color: #2C2C2C;
                border: none;
                border-radius: 10px;
                padding: 20px;
                font-size: 14px;
                font-weight: bold;
                min-height: 80px;
            }
            QPushButton:hover {
                background-color: #8BA5A9;
            }
        """)
        file_btn.clicked.connect(self.select_file)
        
        button_layout.addWidget(image_btn, 0, 0)
        button_layout.addWidget(file_btn, 0, 1)
        layout.addLayout(button_layout)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #7F8C8D;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #6C7B7C;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
    
    def select_image(self):
        """Open image file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        
        if file_path:
            self.selected_file_path = file_path
            self.file_type = 'image'
            self.accept()
    
    def select_file(self):
        """Open general file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "All Files (*.*)"
        )
        
        if file_path:
            self.selected_file_path = file_path
            self.file_type = 'file'
            self.accept()

class WebSocketThread(QThread):
    """Simplified WebSocket thread for messaging"""
    
    # Core signals
    previous_conversations_received = pyqtSignal(dict) 
    message_received = pyqtSignal(str, str, str, str, dict)  # from_username, message, timestamp, message_type, file_data
    connection_established = pyqtSignal()
    connection_lost = pyqtSignal()
    message_sent_confirmation = pyqtSignal(str, str, str, bool)
    
    def __init__(self, auth_token):
        super().__init__()
        self.auth_token = auth_token
        self.websocket = None
        self.running = False
        self.message_queue = []
        self.loop = None
    
    def run(self):
        """Main thread execution"""
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.websocket_main())
    
    async def websocket_main(self):
        """Main WebSocket connection handler"""
        while self.running:
            try:
                logger.info("Connecting to WebSocket server...")
                ssl_context = ssl._create_unverified_context()
                
                self.websocket = await websockets.connect("wss://localhost:8443", ssl=ssl_context)
                
                # Send authentication
                auth_message = {"token": self.auth_token, "session_id": "home_chat"}
                await self.websocket.send(json.dumps(auth_message))
                
                logger.info("Successfully connected and authenticated")
                self.connection_established.emit()
                
                # Send any queued messages
                await self.send_queued_messages()
                
                # Listen for messages
                await self.listen_for_messages()
                
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                self.connection_lost.emit()
                if self.running:
                    await asyncio.sleep(5)
    
    async def send_queued_messages(self):
        """Send any queued messages"""
        while self.message_queue and self.websocket:
            try:
                message_data = self.message_queue.pop(0)
                await self.websocket.send(json.dumps(message_data))
                logger.info(f"📤 Sent queued message: {message_data}")
            except Exception as e:
                logger.error(f"❌ Failed to send queued message: {e}")
                self.message_queue.insert(0, message_data)
                break
    
    async def listen_for_messages(self):
        """Listen for incoming messages"""
        try:
            async for message in self.websocket:
                print(f"DEBUG: Raw message fetched from server: {message}")
                data = json.loads(message)
                message_type = data.get("type")
                
                logger.info(f"📨 [WS] Received message type: {message_type}")
                
                if message_type == "previous_conversations":
                    logger.info("📚 [WS] Processing previous_conversations message...")
                    await self.handle_previous_conversations(data)
                elif message_type == "new_message":
                    logger.info("📨 [WS] Processing new_message...")
                    await self.handle_new_message(data)
                elif message_type == "message_sent":
                    logger.info("✅ [WS] Processing message_sent confirmation...")
                    await self.handle_message_sent(data)
                elif message_type == "auth_success":
                    logger.info("🔑 [WS] Authentication successful")
                else:
                    logger.info(f"❓ [WS] Unhandled message type: {message_type}")
                    
        except Exception as e:
            logger.error(f"❌ [WS] Error in listen_for_messages: {e}")
            import traceback
            traceback.print_exc()
    
    async def handle_previous_conversations(self, data):
        """Handle previous conversations from server"""
        try:
            logger.info("📚 [WS] Starting to process previous conversations...")
            conversations_data = data.get("conversations", {})
            
            logger.info(f"📚 [WS] Conversations data type: {type(conversations_data)}")
            logger.info(f"📚 [WS] Conversations data: {conversations_data}")
            
            friend_conversations = {}
            current_username = "indira123"  # TODO: Get from app state
            
            # Handle dict format: {room_id: [messages]}
            if isinstance(conversations_data, dict):
                logger.info(f"📚 [WS] Processing dict format with {len(conversations_data)} rooms")
                
                for room_id, messages in conversations_data.items():
                    logger.info(f"📚 [WS] Processing room {room_id} with {len(messages) if messages else 0} messages")
                    
                    if not messages:
                        logger.info(f"📚 [WS] Skipping empty room {room_id}")
                        continue
                    
                    # Find friend username - IMPROVED LOGIC
                    friend_username = None
                    participants = set()
                    
                    # First, collect all participants in this conversation
                    for msg in messages:
                        sender = msg.get("sender_username", "")
                        recipient_id = msg.get("recipient_id", "")
                        
                        if sender:
                            participants.add(sender)
                        if recipient_id and isinstance(recipient_id, str):
                            participants.add(recipient_id)
                    
                    logger.info(f"📚 [WS] Room {room_id} participants: {participants}")
                    
                    # Remove current user from participants to find the friend
                    participants.discard(current_username)
                    
                    if len(participants) == 1:
                        friend_username = list(participants)[0]
                        logger.info(f"📚 [WS] Found friend: {friend_username} in room {room_id}")
                    elif len(participants) > 1:
                        logger.warning(f"📚 [WS] Multiple participants in room {room_id}: {participants}")
                        # Take the first non-current-user participant
                        friend_username = list(participants)[0]
                        logger.info(f"📚 [WS] Using first participant as friend: {friend_username}")
                    else:
                        logger.warning(f"📚 [WS] No friend found in room {room_id} (only current user or empty)")
                        continue  # Skip this room
                    
                    # Verify friend_username is not the current user
                    if friend_username == current_username:
                        logger.warning(f"📚 [WS] Skipping room {room_id} - friend is current user (self-conversation)")
                        continue
                    
                    if friend_username:
                        if friend_username not in friend_conversations:
                            friend_conversations[friend_username] = []
                        
                        logger.info(f"📚 [WS] Processing {len(messages)} messages for {friend_username}")
                        
                        # Process messages
                        for msg in messages:
                            processed_msg = self.process_message(msg, current_username)
                            if processed_msg:
                                friend_conversations[friend_username].append(processed_msg)
                                logger.info(f"📚 [WS] Processed message: {processed_msg['message'][:30]}...")
                            else:
                                logger.warning(f"📚 [WS] Failed to process message: {msg}")
                    else:
                        logger.warning(f"📚 [WS] No friend username found for room {room_id}")
            
            # Handle list format
            elif isinstance(conversations_data, list):
                logger.info(f"📚 [WS] Processing list format with {len(conversations_data)} conversations")
                
                for conversation in conversations_data:
                    if isinstance(conversation, dict):
                        # Server currently sends metadata format: {room_id, other_user, last_message_time}
                        room_id = conversation.get("room_id")
                        other_user_id = conversation.get("other_user") 
                        last_message_time = conversation.get("last_message_time")
                        
                        logger.info(f"📚 [WS] Processing conversation metadata:")
                        logger.info(f"📚 [WS]   room_id: {room_id}")
                        logger.info(f"📚 [WS]   other_user_id: {other_user_id}")
                        
                        # QUICK FIX: Since we know iniahmad is the friend, map conversations to iniahmad
                        # TODO: Server should send full conversation data with actual messages
                        if room_id:
                            friend_username = "iniahmad"  # Map to known friend for now
                            
                            logger.info(f"📚 [WS] Mapping room {room_id} to friend: {friend_username}")
                            
                            if friend_username not in friend_conversations:
                                friend_conversations[friend_username] = []
                            
                            # Add placeholder message indicating conversation exists
                            placeholder_message = {
                                "sender": friend_username,
                                "message": f"Previous conversation available (click to load)",
                                "timestamp": self.format_timestamp(last_message_time, is_timestamp=False),
                                "is_sent": False,
                                "message_type": "text",
                                "room_id": room_id  # Store room_id for future message loading
                            }
                            
                            friend_conversations[friend_username].append(placeholder_message)
                            logger.info(f"📚 [WS] Added placeholder for {friend_username}")
                        
                        # Handle legacy format (full conversation data) if server is fixed
                        friend_username_full = conversation.get("friend_username") or conversation.get("username")
                        messages = conversation.get("messages", [])
                        
                        if friend_username_full and messages:
                            logger.info(f"📚 [WS] Processing full conversation data for {friend_username_full}")
                            if friend_username_full not in friend_conversations:
                                friend_conversations[friend_username_full] = []
                            for msg in messages:
                                processed_msg = self.process_message(msg, current_username)
                                if processed_msg:
                                    friend_conversations[friend_username_full].append(processed_msg)
            else:
                logger.error(f"📚 [WS] Unexpected conversations data type: {type(conversations_data)}")
                return
            
            logger.info(f"📚 [WS] *** FINAL RESULT: Processed conversations for {len(friend_conversations)} friends ***")
            for friend, msgs in friend_conversations.items():
                logger.info(f"📚 [WS]   {friend}: {len(msgs)} messages")
            
            # Emit the signal
            logger.info("📤 [WS] *** EMITTING previous_conversations_received SIGNAL ***")
            self.previous_conversations_received.emit(friend_conversations)
            logger.info("✅ [WS] *** SIGNAL EMITTED SUCCESSFULLY ***")
            
        except Exception as e:
            logger.error(f"❌ [WS] Error processing conversations: {e}")
            import traceback
            traceback.print_exc()
    
    async def handle_new_message(self, data):
        """Handle new incoming message with file support"""
        message_obj = data.get("message", {})
        from_username = message_obj.get("sender_username") or data.get("sender", {}).get("username")
        message_text = message_obj.get("content") or data.get("message")
        timestamp = message_obj.get("timestamp") or data.get("timestamp")
        
        # Check for file/image data
        message_type = message_obj.get("message_type", "text")
        file_data = {}
        
        if message_type in ['image', 'file']:
            file_data = {
                'file_name': message_obj.get('file_name'),
                'file_data': message_obj.get('file_data'),
                'file_size': message_obj.get('file_size'),
                'mime_type': message_obj.get('mime_type')
            }
            # For display purposes, use file name as message text for files
            if message_type == 'file':
                message_text = file_data.get('file_name', 'File')
        
        display_time = self.format_timestamp(timestamp)
        
        # Emit with enhanced parameters
        self.message_received.emit(from_username, message_text, display_time, message_type, file_data)
    
    async def handle_message_sent(self, data):
        """Handle message sent confirmation"""
        original_msg = data.get("original", {})
        recipient_id = original_msg.get("recipient_id")
        message_text = original_msg.get("content")
        timestamp = data.get("server_timestamp")
        delivered = data.get("status") == "delivered"
        
        display_time = self.format_timestamp(timestamp, is_timestamp=True)
        self.message_sent_confirmation.emit(str(recipient_id), message_text, display_time, delivered)
    
    def process_message(self, msg, current_username):
        """Convert server message to display format"""
        try:
            logger.info(f"📚 [WS] Processing message: {msg}")
            
            timestamp = msg.get("timestamp", "")
            display_time = self.format_timestamp(timestamp)
            sender = msg.get("sender_username", "")
            content = msg.get("content", "")
            is_sent = sender == current_username
            message_type = msg.get("message_type", "text")
            
            logger.info(f"📚 [WS] Processed: sender={sender}, content={content[:30]}..., is_sent={is_sent}, type={message_type}")
            
            result = {
                "sender": sender,
                "message": content,
                "timestamp": display_time,
                "is_sent": is_sent,
                "message_type": message_type
            }
            
            # Add file data if present
            if message_type in ['image', 'file']:
                result.update({
                    'file_name': msg.get('file_name'),
                    'file_size': msg.get('file_size'),
                    'mime_type': msg.get('mime_type')
                })
            
            logger.info(f"📚 [WS] Result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ [WS] Error processing message: {e}")
            logger.error(f"❌ [WS] Problem message was: {msg}")
            return None
    
    def format_timestamp(self, timestamp, is_timestamp=False):
        """Format timestamp for display"""
        try:
            if timestamp:
                if is_timestamp and isinstance(timestamp, (int, float)):
                    dt = datetime.datetime.fromtimestamp(timestamp)
                elif isinstance(timestamp, str):
                    dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    dt = datetime.datetime.fromtimestamp(timestamp)
                return dt.strftime("%H:%M")
            return datetime.datetime.now().strftime("%H:%M")
        except:
            return datetime.datetime.now().strftime("%H:%M")
    
    def send_message(self, recipient_id, message_text):
        """Send message to friend"""
        if not recipient_id.strip() or not message_text.strip():
            return False
        
        message_data = {"recipient_id": recipient_id, "message": message_text}
        
        if self.websocket and self.loop:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.websocket.send(json.dumps(message_data)), self.loop
                )
                future.result(timeout=1.0)
                logger.info("✅ Message sent successfully")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to send message: {e}")
                self.message_queue.append(message_data)
                return False
        else:
            self.message_queue.append(message_data)
            return False
    
    def send_file_message(self, message_data):
        """Send file message to friend"""
        if not message_data.get("recipient_id") or not message_data.get("file_data"):
            return False
        
        if self.websocket and self.loop:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.websocket.send(json.dumps(message_data)), self.loop
                )
                future.result(timeout=5.0)  # Longer timeout for files
                logger.info("✅ File message sent successfully")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to send file message: {e}")
                self.message_queue.append(message_data)
                return False
        else:
            self.message_queue.append(message_data)
            return False
    
    def stop(self):
        """Stop WebSocket thread"""
        self.running = False
        if self.websocket and self.loop:
            try:
                future = asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
                future.result(timeout=1.0)
            except:
                pass


class HomePage(QWidget):
    """Clean home page with chat interface"""
    
    logout_requested = pyqtSignal()
    friend_list_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.current_chat_user = None
        self.auth_token = None
        self.current_user = None
        self.chat_history = {}  # Store all chat history
        self.websocket_client = None
        
        # Create navigation sidebar
        self.sidebar = NavigationSidebar(active_page="home")
        self.sidebar.friend_list_clicked.connect(self.on_friend_list_clicked)
        
        self.setup_ui()
    
    def set_auth_token(self, token):
        """Set authentication token and start WebSocket"""
        self.auth_token = token
        self.start_websocket_connection()
    
    def set_current_user(self, user_info):
        """Set current user info"""
        self.current_user = user_info
    
    def show_page(self):
        """Called when navigating to home page - show appropriate interface"""
        print(f"📱 [HOME] show_page called")
        print(f"📱 [HOME] Current chat user: {self.current_chat_user}")
        print(f"📱 [HOME] Chat history keys: {list(self.chat_history.keys())}")
        print(f"📱 [HOME] Chat history length: {len(self.chat_history)}")
        
        # If we have chat history but no current chat, auto-select one
        if self.chat_history and not self.current_chat_user:
            print("📱 [HOME] Have chat history but no current chat, auto-selecting...")
            
            # Priority: iniahmad if exists, otherwise most recent
            if "iniahmad" in self.chat_history:
                print("📱 [HOME] Showing iniahmad chat on home page navigation")
                self.start_chat_with_friend("iniahmad")
            else:
                most_recent = self.find_most_recent_chat(self.chat_history)
                if most_recent:
                    print(f"📱 [HOME] Showing most recent chat with {most_recent}")
                    self.start_chat_with_friend(most_recent)
        
        # If we have a current chat, make sure it's displayed
        elif self.current_chat_user:
            print(f"📱 [HOME] Showing current chat with {self.current_chat_user}")
            self.display_chat_messages(self.current_chat_user)
            self.show_chat_interface()
        
        # Otherwise show welcome screen (no chats available)
        else:
            print("📱 [HOME] No chats available, showing welcome screen")
            print(f"📱 [HOME] Debug: chat_history empty? {not bool(self.chat_history)}")
            print(f"📱 [HOME] Debug: current_chat_user empty? {not bool(self.current_chat_user)}")
            self.show_welcome_screen()
    
    def start_websocket_connection(self):
        """Start WebSocket connection for messaging"""
        print("🔗 [HOME] Starting WebSocket connection...")
        
        # Stop existing connection
        if self.websocket_client:
            print("🔗 [HOME] Stopping existing WebSocket...")
            self.websocket_client.stop()
            self.websocket_client.wait()
        
        # Start new connection
        self.websocket_client = WebSocketThread(self.auth_token)
        
        # Connect signals with debug
        print("🔗 [HOME] Connecting WebSocket signals...")
        self.websocket_client.previous_conversations_received.connect(self.handle_chat_history)
        self.websocket_client.message_received.connect(self.handle_incoming_message)
        self.websocket_client.connection_established.connect(self.on_websocket_connected)
        self.websocket_client.connection_lost.connect(self.on_websocket_disconnected)
        self.websocket_client.message_sent_confirmation.connect(self.on_message_sent_confirmation)
        
        print("✅ [HOME] WebSocket signals connected, starting thread...")
        self.websocket_client.start()
    
    @pyqtSlot()
    def on_websocket_connected(self):
        """Handle WebSocket connection"""
        print("✅ Connected to backend server")
        # Don't auto-show chats here - wait for chat history to load
    
    @pyqtSlot()
    def on_websocket_disconnected(self):
        """Handle WebSocket disconnection"""
        print("❌ Disconnected from backend server")
    
    @pyqtSlot(str, str, str, bool)
    def on_message_sent_confirmation(self, recipient_id, message, timestamp, delivered):
        """Handle message delivery confirmation"""
        status = "delivered" if delivered else "pending"
        print(f"✅ Message to {recipient_id}: {status}")
    
    @pyqtSlot(dict)
    def handle_chat_history(self, friend_conversations):
        """Handle chat history from server"""
        print(f"📚 [HOME] *** RECEIVED CHAT HISTORY SIGNAL ***")
        print(f"📚 [HOME] Received chat history for {len(friend_conversations)} friends")
        
        for friend, messages in friend_conversations.items():
            print(f"📚 [HOME] {friend}: {len(messages)} messages")
        
        # Store chat history
        self.chat_history.update(friend_conversations)
        print(f"📚 [HOME] Updated self.chat_history, now has {len(self.chat_history)} friends")
        
        # Update chat list with friends who have conversations
        for friend_username in friend_conversations.keys():
            print(f"📚 [HOME] Adding {friend_username} to chat list...")
            self.add_friend_to_chat_list(friend_username)
        
        # Auto-open a chat if no chat is currently selected
        if not self.current_chat_user and friend_conversations:
            print("📚 [HOME] No current chat selected, auto-opening...")
            
            # Priority: open iniahmad's chat if it exists
            if "iniahmad" in friend_conversations:
                print("📱 [HOME] Auto-opening chat with iniahmad")
                self.start_chat_with_friend("iniahmad")
            else:
                # Otherwise, open the most recent chat (last message)
                most_recent_friend = self.find_most_recent_chat(friend_conversations)
                if most_recent_friend:
                    print(f"📱 [HOME] Auto-opening most recent chat with {most_recent_friend}")
                    self.start_chat_with_friend(most_recent_friend)
        
        # If currently viewing a chat, refresh it
        elif self.current_chat_user and self.current_chat_user in friend_conversations:
            print(f"📱 [HOME] Refreshing current chat with {self.current_chat_user}")
            self.display_chat_messages(self.current_chat_user)
        
        print(f"📚 [HOME] *** CHAT HISTORY PROCESSING COMPLETE ***")
    
    @pyqtSlot(str, str, str, str, dict)
    def handle_incoming_message(self, from_username, message_text, timestamp, message_type='text', file_data=None):
        """Handle incoming message with file/image support"""
        print(f"📥 Message from {from_username}: {message_text} (type: {message_type})")
    
    # Get current user's username for comparison
        current_username = self.current_user.get('username', '') if self.current_user else 'indira123'
    
    # IMPORTANT FIX: Ignore messages from ourselves (echoes/confirmations)
        # if from_username == current_username:
        #     print(f"📝 [HOME] Ignoring message from self: {from_username}")
        #     return
    
    # Store message in chat history
        if from_username not in self.chat_history:
            self.chat_history[from_username] = []
    
        message_data = {
            'message': message_text,
            'message_type': message_type,
            'is_sent': False,  # Always False for incoming messages
            'timestamp': timestamp,
            'sender': from_username
        }
        self.chat_history[from_username].append(message_data)
        print(f"💾 [HANDLER] Message from {from_username} stored in chat history.")

        self.add_friend_to_chat_list(from_username)

        # If the user is currently viewing this chat, add the new bubble to the display.
        if self.current_chat_user == from_username:
            print(f"✅ [HANDLER] Chat with {from_username} is active. Adding bubble to display.")
            self.add_message_to_display_with_type(message_data)
        else:
            print(f"ℹ️ [HANDLER] Chat with {from_username} is not active. UI will not be updated instantly.")

    # Handle file/image data
        if file_data and message_type in ['image', 'file']:
            message_data.update(file_data)
        
        # For images, save to temp folder for display
            if message_type == 'image' and file_data.get('file_data'):
                try:
                # Decode base64 image data
                    image_data = base64.b64decode(file_data['file_data'])
                
                # Create temp file
                    temp_dir = tempfile.gettempdir()
                    temp_file_path = os.path.join(temp_dir, f"chat_image_{from_username}_{timestamp.replace(':', '')}_{file_data.get('file_name', 'image.jpg')}")
                
                    with open(temp_file_path, 'wb') as f:
                        f.write(image_data)
                
                    message_data['file_path'] = temp_file_path
                    print(f"📷 Saved received image to: {temp_file_path}")
                
                except Exception as e:
                    print(f"❌ Error saving received image: {e}")
    
        self.chat_history[from_username].append(message_data)
    
    # Add friend to chat list (only for actual incoming messages, not self)
        print(f"📝 [HOME] Adding {from_username} to chat list...")
        self.add_friend_to_chat_list(from_username)
        print(f"✅ [HOME] Added {from_username} to chat list")
    
    # If viewing this chat, add message to display
        if self.current_chat_user == from_username:
            print(f"📱 [HOME] Currently viewing chat with {from_username}, adding message to display")
            self.add_message_to_display_with_type(message_data)
        else:
            print(f"📱 [HOME] Not currently viewing chat with {from_username} (current: {self.current_chat_user})")
    
    # Update chat list preview
        if message_type == 'image':
            preview_text = "📷 Image"
        elif message_type == 'file':
            preview_text = f"📎 {message_text}"
        else:
            preview_text = message_text
    
        self.update_chat_list_preview(from_username, preview_text, timestamp)

    def send_message(self):
        """Send message to current friend"""
        if not self.current_chat_user or not self.websocket_client:
            return
    
        message_text = self.message_input.text().strip()
        if not message_text:
            return
    
        timestamp = datetime.datetime.now().strftime("%H:%M")
    
        # Send via WebSocket
        success = self.websocket_client.send_message(self.current_chat_user, message_text)
    
        # Store locally and display
        if self.current_chat_user not in self.chat_history:
            self.chat_history[self.current_chat_user] = []
    
        message_data = {
            'message': message_text,
            'message_type': 'text',
            'is_sent': True,
            'timestamp': timestamp,
            'sender': self.current_user.get('username', '') if self.current_user else ''
        }
        self.chat_history[self.current_chat_user].append(message_data)
    
        # Ensure the recipient is in the chat list
        print(f"📝 [HOME] Ensuring recipient {self.current_chat_user} is in chat list...")
        self.add_friend_to_chat_list(self.current_chat_user)
    
        # Add to display
        self.add_message_to_display_with_type(message_data)
    
        # Update chat list preview
        self.update_chat_list_preview(self.current_chat_user, f"You: {message_text}", timestamp)
    
        # Clear input
        self.message_input.clear()
    
        print(f"📤 Sent message to {self.current_chat_user}: {message_text}")
    
    def open_file_dialog(self):
        """Open file selection dialog"""
        if not self.current_chat_user:
            QMessageBox.warning(self, "No Chat Selected", "Please select a friend to chat with first.")
            return
        
        dialog = FileSelectionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.selected_file_path and dialog.file_type:
                self.send_file(dialog.selected_file_path, dialog.file_type)

    def send_file(self, file_path, file_type):
        """Send file or image to current friend"""
        if not self.current_chat_user or not self.websocket_client:
            return
        
        try:
            # Get file info
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Check file size (limit to 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                QMessageBox.warning(self, "File Too Large", 
                                  f"File size ({file_size/1024/1024:.1f}MB) exceeds the 10MB limit.")
                return
            
            # Read and encode file
            with open(file_path, 'rb') as f:
                file_data = f.read()
                file_base64 = base64.b64encode(file_data).decode('utf-8')
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            timestamp = datetime.datetime.now().strftime("%H:%M")
            
            # Create message data for WebSocket
            message_data = {
                "recipient_id": self.current_chat_user,
                "message_type": file_type,  # 'image' or 'file'
                "file_name": file_name,
                "file_data": file_base64,
                "file_size": file_size,
                "mime_type": mime_type
            }
            
            # Send via WebSocket
            success = self.websocket_client.send_file_message(message_data)
            
            # Store locally and display
            if self.current_chat_user not in self.chat_history:
                self.chat_history[self.current_chat_user] = []
            
            local_message_data = {
                'message': file_name,
                'message_type': file_type,
                'file_path': file_path,  # Store local path for display
                'file_name': file_name,
                'file_size': file_size,
                'mime_type': mime_type,
                'is_sent': True,
                'timestamp': timestamp,
                'sender': self.current_user.get('username', '') if self.current_user else ''
            }
            self.chat_history[self.current_chat_user].append(local_message_data)
            
            # Ensure recipient is in chat list
            self.add_friend_to_chat_list(self.current_chat_user)
            
            # Add to display
            self.add_message_to_display_with_type(local_message_data)
            
            # Update chat list preview
            preview_text = f"📎 {file_name}" if file_type == 'file' else f"📷 Image"
            self.update_chat_list_preview(self.current_chat_user, f"You: {preview_text}", timestamp)
            
            print(f"📤 Sent {file_type} to {self.current_chat_user}: {file_name} ({file_size} bytes)")
            
        except Exception as e:
            print(f"❌ Error sending file: {e}")
            QMessageBox.critical(self, "Send Error", f"Failed to send file: {str(e)}")

    def add_message_to_display_with_type(self, message_data):
        """Add message with type info to chat display"""
        if not hasattr(self, 'messages_layout'):
            return
        
        # Remove stretch temporarily
        self.remove_layout_stretch(self.messages_layout)
        
        # Create message widget based on type
        message_widget = self.create_message_widget_enhanced(message_data)
        self.messages_layout.addWidget(message_widget)
        
        # Add stretch back
        self.messages_layout.addStretch()
        
        # Scroll to bottom
        QTimer.singleShot(50, self.scroll_to_bottom)

    def create_message_widget_enhanced(self, message_data):
        """Create enhanced message bubble widget that handles text, images, and files"""
        container = QFrame()
        container.setStyleSheet("background-color: transparent; border: none;")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Get message info
        message_text = message_data.get('message', '')
        is_sent = message_data.get('is_sent', False)
        timestamp = message_data.get('timestamp', '')
        message_type = message_data.get('message_type', 'text')
        
        # Message bubble
        bubble = QFrame()
        bubble.setMaximumWidth(400)
        
        if is_sent:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #A8B8BC;
                    border-radius: 15px;
                    padding: 10px 15px;
                }
            """)
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #D5CECE;
                    border-radius: 15px;
                    padding: 10px 15px;
                }
            """)
            layout.addWidget(bubble)
            layout.addStretch()
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(5, 5, 5, 5)
        bubble_layout.setSpacing(5)
        
        # Content based on message type
        if message_type == 'image':
            # Display image
            image_label = QLabel()
            
            # Try to load image from local path first, then from file_data if available
            image_path = message_data.get('file_path')
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path)
            else:
                # Fallback to placeholder
                pixmap = QPixmap(200, 150)
                pixmap.fill(QColor(200, 200, 200))
            
            # Scale image to fit
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_label.setPixmap(scaled_pixmap)
            
            image_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #B0C4C6;
                    border-radius: 8px;
                    background-color: white;
                }
            """)
            bubble_layout.addWidget(image_label)
            
            # File name below image
            if message_data.get('file_name'):
                name_label = QLabel(message_data['file_name'])
                name_label.setStyleSheet("""
                    QLabel {
                        color: #2C2C2C;
                        font-size: 12px;
                        border: none;
                        background-color: transparent;
                    }
                """)
                name_label.setAlignment(Qt.AlignCenter)
                bubble_layout.addWidget(name_label)
        
        elif message_type == 'file':
            # Display file icon and info
            file_container = QFrame()
            file_container.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 100);
                    border: 1px solid #B0C4C6;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            file_layout = QHBoxLayout(file_container)
            file_layout.setContentsMargins(10, 10, 10, 10)
            
            # File icon
            file_icon = QLabel("📄")
            file_icon.setStyleSheet("font-size: 24px;")
            file_layout.addWidget(file_icon)
            
            # File info
            info_layout = QVBoxLayout()
            
            file_name = message_data.get('file_name', 'Unknown file')
            name_label = QLabel(file_name)
            name_label.setStyleSheet("""
                QLabel {
                    color: #2C2C2C;
                    font-size: 14px;
                    font-weight: bold;
                    border: none;
                    background-color: transparent;
                }
            """)
            
            file_size = message_data.get('file_size', 0)
            size_text = self.format_file_size(file_size)
            size_label = QLabel(size_text)
            size_label.setStyleSheet("""
                QLabel {
                    color: #7F8C8D;
                    font-size: 12px;
                    border: none;
                    background-color: transparent;
                }
            """)
            
            info_layout.addWidget(name_label)
            info_layout.addWidget(size_label)
            file_layout.addLayout(info_layout)
            
            bubble_layout.addWidget(file_container)
        
        else:
            # Regular text message
            message_label = QLabel(message_text)
            message_label.setWordWrap(True)
            message_label.setStyleSheet("""
                QLabel {
                    color: #2C2C2C;
                    font-size: 14px;
                    border: none;
                }
            """)
            bubble_layout.addWidget(message_label)
        
        # Timestamp
        time_label = QLabel(timestamp)
        time_label.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 10px;
                border: none;
            }
        """)
        time_label.setAlignment(Qt.AlignRight if is_sent else Qt.AlignLeft)
        bubble_layout.addWidget(time_label)
        
        return container

    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def find_most_recent_chat(self, friend_conversations):
        """Find the friend with the most recent message"""
        try:
            most_recent_friend = None
            latest_timestamp = None
            
            for friend_username, messages in friend_conversations.items():
                if not messages:
                    continue
                
                # Get the last message timestamp
                last_message = messages[-1]
                timestamp_str = last_message.get('timestamp', '')
                
                try:
                    # Convert timestamp to comparable format
                    if timestamp_str:
                        # Assuming timestamp is in "HH:MM" format, use today's date
                        today = datetime.datetime.now().date()
                        time_obj = datetime.datetime.strptime(timestamp_str, "%H:%M").time()
                        full_timestamp = datetime.datetime.combine(today, time_obj)
                        
                        if latest_timestamp is None or full_timestamp > latest_timestamp:
                            latest_timestamp = full_timestamp
                            most_recent_friend = friend_username
                except:
                    # If timestamp parsing fails, just use the first friend as fallback
                    if most_recent_friend is None:
                        most_recent_friend = friend_username
            
            return most_recent_friend
        except Exception as e:
            print(f"❌ Error finding most recent chat: {e}")
            # Return first friend as fallback
            return list(friend_conversations.keys())[0] if friend_conversations else None
    
    def add_friend_to_chat_list(self, friend_username):
        """Add friend to chat list if not already there"""
        print(f"📝 [HOME] add_friend_to_chat_list called for: {friend_username}")
        
        # Check if already exists
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), 'objectName'):
                if item.widget().objectName() == f"chat_{friend_username}":
                    print(f"📝 [HOME] {friend_username} already in chat list")
                    return  # Already exists
        
        print(f"📝 [HOME] Adding {friend_username} to chat list...")
        
        # Remove any stretch items
        self.clear_layout_stretches(self.chat_layout)
        
        # Create chat item
        chat_item = self.create_chat_item(friend_username)
        chat_item.setObjectName(f"chat_{friend_username}")
        
        # Add click handler
        def on_chat_clicked():
            print(f"📝 [HOME] Chat item clicked: {friend_username}")
            self.start_chat_with_friend(friend_username)
        
        chat_item.mousePressEvent = lambda event: on_chat_clicked()
        
        # Add to layout
        self.chat_layout.insertWidget(0, chat_item)
        self.chat_layout.addStretch()
        
        print(f"✅ [HOME] Added {friend_username} to chat list")
    
    def start_chat_with_friend(self, friend_username):
        """Start or continue chat with friend"""
        print(f"💬 [HOME] Starting chat with {friend_username}")
        
        self.current_chat_user = friend_username
        
        # Show chat interface
        self.show_chat_interface()
        
        # Update chat header
        if hasattr(self, 'friend_name_label'):
            self.friend_name_label.setText(friend_username)
        
        # Check if we have actual conversation data or just metadata
        if friend_username in self.chat_history:
            messages = self.chat_history[friend_username]
            has_placeholder = any(msg.get('message', '').startswith('Previous conversation') for msg in messages)
            
            if has_placeholder:
                print(f"💬 [HOME] Only have conversation metadata for {friend_username}, requesting full history...")
                # TODO: Request full conversation data from server using room_id
                # For now, show placeholder and allow new messages
                self.display_chat_messages(friend_username)
                
                # Add a system message explaining the situation
                if hasattr(self, 'messages_layout'):
                    self.remove_layout_stretch(self.messages_layout)
                    system_msg = self.create_system_message("Previous conversation history will be loaded soon. You can start typing new messages.")
                    self.messages_layout.addWidget(system_msg)
                    self.messages_layout.addStretch()
            else:
                # Display full chat history
                self.display_chat_messages(friend_username)
        else:
            # No history, start fresh
            self.display_chat_messages(friend_username)
        
        # Enable message input
        self.message_input.setPlaceholderText(f"Message {friend_username}...")
        self.message_input.setEnabled(True)
        self.message_input.setFocus()
        
        print(f"✅ [HOME] Chat interface ready for {friend_username}")
    
    def create_system_message(self, text):
        """Create a system message widget"""
        container = QFrame()
        container.setStyleSheet("background-color: transparent; border: none;")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 5, 0, 5)
        
        # System message (centered, italic)
        message_label = QLabel(text)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 12px;
                font-style: italic;
                border: none;
                padding: 10px;
            }
        """)
        
        layout.addWidget(message_label)
        return container
    
    def display_chat_messages(self, friend_username):
        """Display chat messages for friend with file/image support"""
        if not hasattr(self, 'messages_layout'):
            return
        
        # Clear existing messages
        self.clear_layout(self.messages_layout)
        
        # Add messages if history exists
        if friend_username in self.chat_history:
            messages = self.chat_history[friend_username]
            print(f"📚 Displaying {len(messages)} messages for {friend_username}")
            
            for msg in messages:
                # Check if it's an enhanced message with type info
                if 'message_type' in msg:
                    self.add_message_to_display_with_type(msg)
                else:
                    # Legacy text message
                    message_text = msg.get('message', '')
                    is_sent = msg.get('is_sent', False)
                    timestamp = msg.get('timestamp', '')
                    self.add_message_to_display(message_text, is_sent, timestamp)
        
        # Add stretch to keep messages at top
        self.messages_layout.addStretch()
        
        # Scroll to bottom
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def add_message_to_display(self, message_text, is_sent, timestamp):
        """Add message to chat display"""
        if not hasattr(self, 'messages_layout'):
            return
        
        # Remove stretch temporarily
        self.remove_layout_stretch(self.messages_layout)
        
        # Create message widget
        message_widget = self.create_message_widget(message_text, is_sent, timestamp)
        self.messages_layout.addWidget(message_widget)
        
        # Add stretch back
        self.messages_layout.addStretch()
        
        # Scroll to bottom
        QTimer.singleShot(50, self.scroll_to_bottom)
    
    def update_chat_list_preview(self, friend_username, message_preview, timestamp):
        """Update chat list item with latest message"""
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), 'objectName'):
                if item.widget().objectName() == f"chat_{friend_username}":
                    # Update the preview (implementation depends on your chat item structure)
                    # This is a simplified version - adapt to your chat item layout
                    widget = item.widget()
                    try:
                        layout = widget.layout()
                        if layout and layout.count() >= 2:
                            # Find and update message label
                            for j in range(layout.count()):
                                child_item = layout.itemAt(j)
                                if child_item and isinstance(child_item.widget(), QLabel):
                                    label = child_item.widget()
                                    if ":" in label.text() or "message" in label.text().lower():
                                        preview = message_preview[:50] + "..." if len(message_preview) > 50 else message_preview
                                        label.setText(preview)
                                        break
                    except Exception as e:
                        print(f"❌ Error updating chat preview: {e}")
                    break
    
    # UI Setup Methods
    def setup_ui(self):
        """Setup main UI layout"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add sidebar
        main_layout.addWidget(self.sidebar)
        
        # Add chat list
        self.setup_chat_list_sidebar(main_layout)
        
        # Add main content
        self.setup_main_content_area(main_layout)
    
    def setup_chat_list_sidebar(self, parent_layout):
        """Setup chat list sidebar"""
        chat_sidebar = QFrame()
        chat_sidebar.setFixedWidth(350)
        chat_sidebar.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
            }
        """)
        
        layout = QVBoxLayout(chat_sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = self.create_chat_header()
        layout.addWidget(header)
        
        # Search
        search = self.create_search_area()
        layout.addWidget(search)
        
        # Chat list
        self.setup_chat_scroll_area(layout)
        
        parent_layout.addWidget(chat_sidebar)
    
    def create_chat_header(self):
        """Create chat list header"""
        header = QFrame()
        header.setFixedHeight(66)
        header.setStyleSheet("""
            QFrame {
                background-color: #9DB4B8;
            }
        """)
        
        layout = QVBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Start a new chat")
        title.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title)
        return header
    
    def create_search_area(self):
        """Create search area"""
        search_container = QFrame()
        search_container.setFixedHeight(66)
        search_container.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
            }
        """)
        
        layout = QHBoxLayout(search_container)
        layout.setContentsMargins(15, 13, 15, 13)
        
        # Search input
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #B0C4C6;
                border-radius: 8px;
            }
        """)
        
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(10, 0, 10, 0)
        search_layout.setSpacing(8)
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("color: #7F8C8D; font-size: 14px;")
        
        self.chat_search_input = QLineEdit()
        self.chat_search_input.setPlaceholderText("Search for messages ...")
        self.chat_search_input.setStyleSheet("""
            QLineEdit {
                border: none;
                font-size: 14px;
                color: #2C2C2C;
            }
        """)
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.chat_search_input)
        
        layout.addWidget(search_frame)
        return search_container
    
    def setup_chat_scroll_area(self, parent_layout):
        """Setup scrollable chat list"""
        self.chat_scroll_area = QScrollArea()
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #E8E1E1;
                border: none;
            }
        """)
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: #E8E1E1;")
        
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(0)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.addStretch()
        
        self.chat_scroll_area.setWidget(self.chat_container)
        parent_layout.addWidget(self.chat_scroll_area)
    
    def setup_main_content_area(self, parent_layout):
        """Setup main content area"""
        self.main_content = QFrame()
        self.main_content.setStyleSheet("background-color: #9DB4B8;")
        
        self.content_layout = QVBoxLayout(self.main_content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # Welcome area (shown initially)
        self.setup_welcome_area()
        
        # Message input (hidden initially)
        self.setup_message_input_area()
        
        parent_layout.addWidget(self.main_content)
    
    def setup_welcome_area(self):
        """Setup welcome message area"""
        self.welcome_area = QFrame()
        self.welcome_area.setStyleSheet("background-color: #9DB4B8;")
        
        layout = QVBoxLayout(self.welcome_area)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # Title
        title = QLabel("Welcome to Messenger!")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 36px;
                font-weight: bold;
            }
        """)
        
        # Subtitle
        subtitle = QLabel("Start by adding friends to begin chatting")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 20px;
            }
        """)
        
        # Button
        friend_list_btn = QPushButton("Go to Friend List")
        friend_list_btn.setStyleSheet("""
            QPushButton {
                background-color: #7A9499;
                color: white;
                border: none;
                border-radius: 15px;
                padding: 20px 40px;
                font-size: 18px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #6A8489;
            }
        """)
        friend_list_btn.clicked.connect(self.on_friend_list_clicked)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(friend_list_btn, 0, Qt.AlignCenter)
        
        self.content_layout.addWidget(self.welcome_area)
    
    def setup_message_input_area(self):
        """Setup message input area with file attachment support"""
        self.input_container = QFrame()
        self.input_container.setFixedHeight(80)
        self.input_container.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border-top: 2px solid #B0C4C6;
            }
        """)
        
        layout = QHBoxLayout(self.input_container)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        # Attachment button - ENHANCED
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #B0C4C6;
                border-radius: 8px;
                font-size: 18px;
                padding: 8px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        self.attach_btn.clicked.connect(self.open_file_dialog)  # Connect to file dialog
        
        # Message input
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Select a friend to start chatting...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #B0C4C6;
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 16px;
                color: #2C2C2C;
            }
            QLineEdit:focus {
                border: 2px solid #7A9499;
            }
        """)
        self.message_input.setFixedHeight(50)
        self.message_input.setEnabled(False)
        self.message_input.returnPressed.connect(self.send_message)
        
        # Send button
        send_btn = QPushButton("Send")
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #9DB4B8;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 25px;
                font-size: 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #8BA5A9;
            }
        """)
        send_btn.setFixedHeight(50)
        send_btn.clicked.connect(self.send_message)
        
        layout.addWidget(self.attach_btn)
        layout.addWidget(self.message_input)
        layout.addWidget(send_btn)
        
        self.input_container.hide()
        self.content_layout.addWidget(self.input_container)
    
    def show_chat_interface(self):
        """Show chat interface instead of welcome"""
        # Create or show chat area
        if not hasattr(self, 'chat_area'):
            self.create_chat_area()
        
        # Hide welcome, show chat and input
        self.welcome_area.hide()
        self.chat_area.show()
        self.input_container.show()
    
    def show_welcome_screen(self):
        """Show welcome screen (hide chat interface)"""
        if hasattr(self, 'chat_area'):
            self.chat_area.hide()
        self.input_container.hide()
        self.welcome_area.show()
        self.current_chat_user = None
    
    def create_chat_area(self):
        """Create chat messages area"""
        self.chat_area = QFrame()
        self.chat_area.setStyleSheet("background-color: #B8C4C8;")
        
        layout = QVBoxLayout(self.chat_area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Chat header
        chat_header = QFrame()
        chat_header.setFixedHeight(60)
        chat_header.setStyleSheet("""
            QFrame {
                background-color: #B8C4C8;
                border-bottom: 1px solid #A0A8AC;
            }
        """)
        
        header_layout = QHBoxLayout(chat_header)
        header_layout.setContentsMargins(30, 15, 30, 15)
        
        self.friend_name_label = QLabel("Friend")
        self.friend_name_label.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        
        header_layout.addWidget(self.friend_name_label)
        
        # Messages scroll area
        self.messages_scroll = QScrollArea()
        self.messages_scroll.setWidgetResizable(True)
        self.messages_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.messages_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #B8C4C8;
                border: none;
            }
        """)
        
        self.messages_container = QWidget()
        self.messages_container.setStyleSheet("background-color: #B8C4C8;")
        
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(20, 20, 20, 20)
        self.messages_layout.setSpacing(10)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.messages_layout.addStretch()
        
        self.messages_scroll.setWidget(self.messages_container)
        
        layout.addWidget(chat_header)
        layout.addWidget(self.messages_scroll)
        
        # Insert before input container
        self.content_layout.insertWidget(0, self.chat_area)
        self.chat_area.hide()  # Hidden initially
    
    def create_chat_item(self, friend_username):
        """Create chat list item"""
        chat_item = QFrame()
        chat_item.setFixedHeight(80)
        chat_item.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border-bottom: 1px solid #D0C9C9;
            }
            QFrame:hover {
                background-color: #D5CECE;
            }
        """)
        chat_item.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(chat_item)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        # Top row: name and time
        top_row = QHBoxLayout()
        
        name_label = QLabel(friend_username)
        name_label.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        time_label = QLabel("Now")
        time_label.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 12px;
            }
        """)
        time_label.setAlignment(Qt.AlignRight)
        
        top_row.addWidget(name_label)
        top_row.addStretch()
        top_row.addWidget(time_label)
        
        # Bottom row: last message
        message_preview = "No messages yet"
        if friend_username in self.chat_history and self.chat_history[friend_username]:
            last_msg = self.chat_history[friend_username][-1]
            msg_type = last_msg.get('message_type', 'text')
            
            if msg_type == 'image':
                preview_text = "📷 Image"
            elif msg_type == 'file':
                preview_text = f"📎 {last_msg.get('file_name', 'File')}"
            else:
                preview_text = last_msg.get('message', '')
            
            if last_msg.get('is_sent', False):
                message_preview = f"You: {preview_text[:30]}..."
            else:
                message_preview = preview_text[:40] + "..." if len(preview_text) > 40 else preview_text
        
        message_label = QLabel(message_preview)
        message_label.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 14px;
            }
        """)
        
        layout.addLayout(top_row)
        layout.addWidget(message_label)
        
        return chat_item
    
    def create_message_widget(self, message_text, is_sent, timestamp):
        """Create message bubble widget"""
        container = QFrame()
        container.setStyleSheet("background-color: transparent; border: none;")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Message bubble
        bubble = QFrame()
        bubble.setMaximumWidth(400)
        
        if is_sent:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #A8B8BC;
                    border-radius: 15px;
                    padding: 10px 15px;
                }
            """)
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #D5CECE;
                    border-radius: 15px;
                    padding: 10px 15px;
                }
            """)
            layout.addWidget(bubble)
            layout.addStretch()
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(5, 5, 5, 5)
        bubble_layout.setSpacing(2)
        
        # Message text
        message_label = QLabel(message_text)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 14px;
                border: none;
            }
        """)
        
        # Timestamp
        time_label = QLabel(timestamp)
        time_label.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 10px;
                border: none;
            }
        """)
        time_label.setAlignment(Qt.AlignRight if is_sent else Qt.AlignLeft)
        
        bubble_layout.addWidget(message_label)
        bubble_layout.addWidget(time_label)
        
        return container
    
    # Utility Methods
    def clear_layout(self, layout):
        """Clear all widgets from layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def clear_layout_stretches(self, layout):
        """Remove stretch items from layout"""
        for i in range(layout.count() - 1, -1, -1):
            item = layout.itemAt(i)
            if item and item.spacerItem():
                layout.removeItem(item)
    
    def remove_layout_stretch(self, layout):
        """Remove the last stretch item"""
        for i in range(layout.count() - 1, -1, -1):
            item = layout.itemAt(i)
            if item and item.spacerItem():
                layout.removeItem(item)
                break
    
    def scroll_to_bottom(self):
        """Scroll messages to bottom"""
        if hasattr(self, 'messages_scroll'):
            scrollbar = self.messages_scroll.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    @pyqtSlot()
    def on_friend_list_clicked(self):
        """Handle friend list navigation"""
        print("👥 Friend list navigation requested")
        self.friend_list_requested.emit()
    
    def add_chat_to_list(self, friend_username):
        """Public method to add chat (called from main app)"""
        self.add_friend_to_chat_list(friend_username)
        
        # If this is the first chat and no chat is currently selected, auto-open it
        if not self.current_chat_user:
            print(f"📱 Auto-opening first chat with {friend_username}")
            self.start_chat_with_friend(friend_username)
    
    def closeEvent(self, event):
        """Clean up on close"""
        if self.websocket_client:
            self.websocket_client.stop()
            self.websocket_client.wait()
        event.accept()