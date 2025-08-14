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
import shutil

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
    new_message_received = pyqtSignal(dict)  # Define signal at top of class
    connection_lost = pyqtSignal()
    message_sent_confirmation = pyqtSignal(str, str, str, bool)
    
    def __init__(self, auth_token):
        super().__init__()
        self.auth_token = auth_token
        self.websocket = None
        self.running = False
        self.message_queue = []
        self.loop = None
        self.current_username = ""  # Track current username to avoid self-messages
    
    def set_current_username(self, username):
        """Set the current username for filtering self-messages"""
        self.current_username = username
        print(f"🔧 [WS] Current username set to: {username}")
    
    def run(self):
        """Main thread execution"""
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.websocket_main())
    
    async def websocket_main(self):
        """Main WebSocket connection handler with increased size limits"""
        while self.running:
            try:
                logger.info("Connecting to WebSocket server...")
                ssl_context = ssl._create_unverified_context()
                
                # IMPORTANT: Increase message size limit to handle chat history with images
                self.websocket = await websockets.connect(
                    "wss://localhost:8443", 
                    ssl=ssl_context,
                    max_size=10 * 1024 * 1024,  # 10MB limit instead of default 1MB
                    ping_interval=30,
                    ping_timeout=10,
                    compression=None  # Disable compression to save processing
                )
                
                # Send authentication
                auth_message = {"token": self.auth_token, "session_id": "home_chat"}
                await self.websocket.send(json.dumps(auth_message))
                
                logger.info("Successfully connected and authenticated")
                self.connection_established.emit()
                
                # Send any queued messages
                await self.send_queued_messages()
                
                # Listen for messages
                await self.listen_for_messages()
                
            except websockets.exceptions.ConnectionClosedError as e:
                if "message too big" in str(e):
                    logger.error(f"❌ [WS] Message size limit exceeded: {e}")
                    logger.error("💡 [WS] Server sent message larger than 10MB limit")
                    logger.error("🔧 [WS] This might indicate server needs to implement pagination")
                else:
                    logger.error(f"❌ [WS] WebSocket connection closed: {e}")
                self.connection_lost.emit()
                if self.running:
                    await asyncio.sleep(5)
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
        """Listen for incoming messages with improved error handling"""
        try:
            async for message in self.websocket:
                try:
                    print(f"DEBUG: Raw message fetched from server: {message[:200]}..." if len(message) > 200 else message)
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
                
                except json.JSONDecodeError as e:
                    logger.error(f"❌ [WS] Failed to decode JSON message: {e}")
                    continue
                except Exception as e:
                    logger.error(f"❌ [WS] Error processing individual message: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                    
        except websockets.exceptions.ConnectionClosedError as e:
            if "message too big" in str(e):
                logger.error(f"❌ [WS] Connection closed - message too big: {e}")
                logger.error("💡 [WS] The server sent a message that exceeded size limits")
                logger.error("🔧 [WS] Try clearing chat history or reducing file sizes")
            else:
                logger.error(f"❌ [WS] Connection closed: {e}")
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
            # Use the current username from WebSocket thread if available, otherwise fallback
            current_username = self.current_username or "indira123"  # Use set username, fallback only if not set
            
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
                        # Server sends metadata format: {room_id, other_user, last_message_time}
                        room_id = conversation.get("room_id")
                        other_user_id = conversation.get("other_user")  # This should be the friend's username
                        last_message_time = conversation.get("last_message_time")
                        
                        logger.info(f"📚 [WS] Processing conversation metadata:")
                        logger.info(f"📚 [WS]   room_id: {room_id}")
                        logger.info(f"📚 [WS]   other_user_id: {other_user_id}")
                        
                        # Use the actual other_user from server response
                        if room_id and other_user_id:
                            friend_username = other_user_id  # Use the actual friend username from server
                            
                            # Make sure it's not the current user
                            if friend_username == current_username:
                                logger.warning(f"📚 [WS] Skipping room {room_id} - other_user is current user")
                                continue
                            
                            logger.info(f"📚 [WS] Processing conversation with friend: {friend_username}")
                            
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
                        else:
                            logger.warning(f"📚 [WS] Missing room_id or other_user in conversation: {conversation}")
                        
                        # Handle legacy format (full conversation data) if server provides it
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
        """Handle new incoming message with file support - FIXED VERSION"""
        try:
            print(f"🔍 [WS] RAW NEW MESSAGE DATA: {data}")
            
            # FIXED: Handle different message structures consistently
            message_obj = data.get("message", {})
            
            # Get sender info - check multiple possible locations
            from_username = None
            
            # Method 1: Direct from message object
            if message_obj and isinstance(message_obj, dict):
                from_username = message_obj.get("sender_username")
            
            # Method 2: From sender object in data
            if not from_username:
                sender_obj = data.get("sender", {})
                if isinstance(sender_obj, dict):
                    from_username = sender_obj.get("username")
            
            # Method 3: Legacy format
            if not from_username:
                from_username = data.get("from_username") or data.get("sender_username")
            
            print(f"🔍 [WS] Extracted from_username: {from_username}")
            print(f"🔍 [WS] Current username: {self.current_username}")
            
            # CRITICAL: Skip messages from ourselves
            if from_username == self.current_username:
                print(f"📝 [WS] SKIPPING message from self: {from_username}")
                return
            
            if not from_username:
                print(f"❌ [WS] No sender username found in message: {data}")
                return
            
            # Get message content
            message_text = message_obj.get("content") or data.get("message", "")
            timestamp = message_obj.get("timestamp") or data.get("timestamp")
            
            # Check for file/image data
            message_type = message_obj.get("message_type", "text")
            file_data = {}
            
            print(f"🔍 [WS] Processing message: type={message_type}, from={from_username}")
            print(f"🔍 [WS] Message object keys: {list(message_obj.keys()) if message_obj else 'None'}")
            
            if message_type in ['image', 'file']:
                file_data = {
                    'file_name': message_obj.get('file_name'),
                    'file_data': message_obj.get('file_data'),  # Base64 encoded data
                    'file_size': message_obj.get('file_size'),
                    'mime_type': message_obj.get('mime_type')
                }
                
                print(f"🔍 [WS] File data extracted:")
                print(f"  file_name: {file_data.get('file_name')}")
                print(f"  file_size: {file_data.get('file_size')}")
                print(f"  mime_type: {file_data.get('mime_type')}")
                print(f"  has_file_data: {bool(file_data.get('file_data'))}")
                
                # For display purposes, use file name as message text for files
                if message_type == 'file':
                    message_text = file_data.get('file_name', 'File')
                elif message_type == 'image':
                    message_text = file_data.get('file_name', 'Image')
            
            display_time = self.format_timestamp(timestamp)
            
            print(f"🔍 [WS] Final emit data:")
            print(f"  from_username: {from_username}")
            print(f"  message_text: {message_text}")
            print(f"  message_type: {message_type}")
            print(f"  display_time: {display_time}")
            print(f"  file_data_present: {bool(file_data)}")
            
            # FIXED: Always emit for non-self messages
            print(f"✅ [WS] EMITTING message from {from_username}")
            self.message_received.emit(from_username, message_text, display_time, message_type, file_data)
            
        except Exception as e:
            logger.error(f"❌ [WS] Error in handle_new_message: {e}")
            import traceback
            traceback.print_exc()
    
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
        """Convert server message to display format with file reconstruction"""
        try:
            logger.info(f"📚 [WS] Processing message: {msg}")
            
            timestamp = msg.get("timestamp", "")
            display_time = self.format_timestamp(timestamp)
            sender = msg.get("sender_username", "")
            content = msg.get("content", "")
            is_sent = sender == current_username
            message_type = msg.get("message_type", "text")
            
            # FIX: Create message data with file support
            result = {
                "sender": sender,
                "message": content,
                "timestamp": display_time,
                "is_sent": is_sent,
                "message_type": message_type
            }
            
            # Handle file/image data from server
            if message_type in ['image', 'file']:
                result.update({
                    'file_name': msg.get('file_name'),
                    'file_size': msg.get('file_size'),
                    'mime_type': msg.get('mime_type')
                })
                
                # FIX: For images, decode and save the file data locally
                file_data_b64 = msg.get('file_data')
                if file_data_b64 and message_type == 'image':
                    try:
                        # Create persistent chat images directory
                        chat_images_dir = os.path.join(os.path.expanduser('~'), '.messenger_chat_images')
                        os.makedirs(chat_images_dir, exist_ok=True)
                        
                        # Create unique filename
                        file_name = msg.get('file_name', 'image.jpg')
                        clean_timestamp = display_time.replace(':', '').replace(' ', '_')
                        unique_filename = f"{sender}_{clean_timestamp}_{file_name}"
                        local_file_path = os.path.join(chat_images_dir, unique_filename)
                        
                        # Decode and save if not already exists
                        if not os.path.exists(local_file_path):
                            image_data = base64.b64decode(file_data_b64)
                            with open(local_file_path, 'wb') as f:
                                f.write(image_data)
                            logger.info(f"📷 [WS] Saved chat history image: {local_file_path}")
                        
                        # Set file path for display
                        result['file_path'] = local_file_path
                        result['message'] = file_name  # Use filename as display text
                        
                    except Exception as e:
                        logger.error(f"❌ [WS] Error saving chat history image: {e}")
                        result['message'] = msg.get('file_name', 'Image (failed to load)')
                
                elif message_type == 'file':
                    # For files, just use filename as display text
                    result['message'] = msg.get('file_name', 'File')
            
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
        """Send file message to friend with size checking"""
        if not message_data.get("recipient_id") or not message_data.get("file_data"):
            return False
        
        # Check message size before sending
        message_json = json.dumps(message_data)
        message_size = len(message_json.encode('utf-8'))
        max_size = 8 * 1024 * 1024  # 8MB limit for safety (server has 10MB limit)
        
        print(f"📤 [WS] File message size: {message_size/1024/1024:.2f}MB")
        
        if message_size > max_size:
            logger.error(f"❌ File message too large: {message_size/1024/1024:.1f}MB > {max_size/1024/1024:.1f}MB")
            return False
        
        if self.websocket and self.loop:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.websocket.send(message_json), self.loop
                )
                future.result(timeout=15.0)  # Longer timeout for large files
                logger.info("✅ File message sent successfully")
                return True
            except asyncio.TimeoutError:
                logger.error("❌ Timeout sending file message")
                self.message_queue.append(message_data)
                return False
            except websockets.exceptions.ConnectionClosedError as e:
                if "message too big" in str(e):
                    logger.error(f"❌ File message rejected - too large: {e}")
                else:
                    logger.error(f"❌ Connection closed while sending file: {e}")
                return False
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
        
        # FIX: Set current username in WebSocket client if it exists
        if self.websocket_client and user_info:
            username = user_info.get('username', '')
            self.websocket_client.set_current_username(username)
            print(f"🔧 [HOME] Set WebSocket username to: {username}")
    
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
        
        # FIX: Set current username immediately after creating client
        if self.current_user:
            username = self.current_user.get('username', '')
            self.websocket_client.set_current_username(username)
            print(f"🔧 [HOME] Set WebSocket username to: {username}")
        
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
        """Handle incoming message with file/image support - FIXED VERSION"""
        print(f"📥 [HOME] *** INCOMING MESSAGE ***")
        print(f"📥 [HOME] From: {from_username}")
        print(f"📥 [HOME] Message: {message_text}")
        print(f"📥 [HOME] Type: {message_type}")
        print(f"📥 [HOME] Timestamp: {timestamp}")
        print(f"📥 [HOME] File data present: {bool(file_data)}")

        # Get current user's username for comparison
        current_username = self.current_user.get('username', '') if self.current_user else 'indira123'
        print(f"📥 [HOME] Current user: {current_username}")

        # DOUBLE CHECK: This should already be filtered in WebSocket thread, but let's be extra sure
        if from_username == current_username:
            print(f"❌ [HOME] ERROR: Received message from self ({from_username}), this should have been filtered!")
            return

        # Store message in chat history
        if from_username not in self.chat_history:
            self.chat_history[from_username] = []
            print(f"📥 [HOME] Created new chat history for {from_username}")

        # Create base message data
        message_data = {
            'message': message_text,
            'message_type': message_type,
            'is_sent': False,  # Always False for incoming messages
            'timestamp': timestamp,
            'sender': from_username
        }

        # Handle file/image data
        if file_data and message_type in ['image', 'file']:
            print(f"🔍 [HOME] Processing {message_type} from {from_username}")
            print(f"🔍 [HOME] File data: {list(file_data.keys())}")
            
            # Add file metadata
            message_data.update({
                'file_name': file_data.get('file_name', 'Unknown file'),
                'file_size': file_data.get('file_size', 0),
                'mime_type': file_data.get('mime_type', 'application/octet-stream')
            })
            
            # For images, save to temp folder for display
            if message_type == 'image' and file_data.get('file_data'):
                try:
                    print(f"🔍 [HOME] Decoding image data...")
                    # Decode base64 image data
                    image_data = base64.b64decode(file_data['file_data'])
                    
                    # Create persistent chat images directory
                    chat_images_dir = os.path.join(os.path.expanduser('~'), '.messenger_chat_images')
                    os.makedirs(chat_images_dir, exist_ok=True)
                    
                    # Create temp file with proper extension
                    file_name = file_data.get('file_name', 'image.jpg')
                    # Clean timestamp for filename
                    clean_timestamp = timestamp.replace(':', '').replace(' ', '_')
                    temp_file_path = os.path.join(chat_images_dir, f"received_{from_username}_{clean_timestamp}_{file_name}")
                    
                    print(f"🔍 [HOME] Saving image to: {temp_file_path}")
                    with open(temp_file_path, 'wb') as f:
                        f.write(image_data)
                    
                    # Verify file was created and has content
                    if os.path.exists(temp_file_path):
                        file_size = os.path.getsize(temp_file_path)
                        print(f"✅ [HOME] Image saved successfully: {file_size} bytes")
                        
                        # Store the temp file path for display
                        message_data['file_path'] = temp_file_path
                        # Update message text to be more user-friendly
                        message_data['message'] = file_data.get('file_name', 'Image')
                    else:
                        print(f"❌ [HOME] Failed to save image file")
                        message_data['message'] = file_data.get('file_name', 'Image (failed to save)')
                    
                except Exception as e:
                    print(f"❌ [HOME] Error saving received image: {e}")
                    import traceback
                    traceback.print_exc()
                    # Fallback to showing filename
                    message_data['message'] = file_data.get('file_name', 'Image (failed to load)')
            
            elif message_type == 'file':
                # For files, just use filename as display text
                message_data['message'] = file_data.get('file_name', 'File')
                print(f"🔍 [HOME] File message processed: {message_data['message']}")

        # Add message to chat history
        self.chat_history[from_username].append(message_data)
        print(f"💾 [HOME] Message from {from_username} stored in chat history.")

        # Add friend to chat list
        self.add_friend_to_chat_list(from_username)

        # If the user is currently viewing this chat, add the new bubble to the display
        if self.current_chat_user == from_username:
            print(f"✅ [HOME] Chat with {from_username} is active. Adding bubble to display.")
            self.add_message_to_display_with_type(message_data)
        else:
            print(f"ℹ️ [HOME] Chat with {from_username} is not active. Message stored for later viewing.")

        # Update chat list preview
        if message_type == 'image':
            preview_text = "📷 Image"
        elif message_type == 'file':
            preview_text = f"📎 {file_data.get('file_name', 'File') if file_data else 'File'}"
        else:
            preview_text = message_text

        self.update_chat_list_preview(from_username, preview_text, timestamp)
        
        print(f"✅ [HOME] *** INCOMING MESSAGE PROCESSED SUCCESSFULLY ***")
    
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
        """Send file or image to current friend with size limits and compression"""
        if not self.current_chat_user or not self.websocket_client:
            return
        
        try:
            # Get file info
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            print(f"📎 [SEND] Preparing to send {file_type}: {file_name} ({file_size} bytes)")
            print(f"📎 [SEND] Original file path: {file_path}")
            
            # Check file size limits (stricter for WebSocket)
            if file_type == 'image':
                max_size = 2 * 1024 * 1024  # 2MB for images
            else:
                max_size = 1 * 1024 * 1024  # 1MB for other files
                
            if file_size > max_size:
                QMessageBox.warning(self, "File Too Large", 
                                  f"File size ({file_size/1024/1024:.1f}MB) exceeds the {max_size/1024/1024:.0f}MB limit for {file_type}s.\n"
                                  f"Please choose a smaller file or compress it first.")
                return
            
            # Read and process file
            if file_type == 'image':
                # Compress image if needed
                file_data, compressed_size = self.compress_image_if_needed(file_path, max_size)
                if compressed_size != file_size:
                    print(f"📷 [SEND] Image compressed: {file_size} → {compressed_size} bytes")
                    file_size = compressed_size
            else:
                # Read file normally
                with open(file_path, 'rb') as f:
                    file_data = f.read()
            
            # Encode to base64
            file_base64 = base64.b64encode(file_data).decode('utf-8')
            
            # Check final encoded size (base64 adds ~33% overhead)
            encoded_size = len(file_base64)
            max_encoded_size = 3 * 1024 * 1024  # 3MB encoded limit
            
            if encoded_size > max_encoded_size:
                QMessageBox.warning(self, "Encoded File Too Large", 
                                  f"After encoding, file size ({encoded_size/1024/1024:.1f}MB) exceeds the 3MB transmission limit.\n"
                                  f"Please choose a smaller file.")
                return
            
            print(f"✅ [SEND] File ready for transmission: {encoded_size} bytes encoded")
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            timestamp = datetime.datetime.now().strftime("%H:%M")
            
            # Create message data for WebSocket
            message_data = {
                "recipient_id": self.current_chat_user,
                "message_type": file_type,
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
            
            # FIX: For images, copy to a permanent location for display
            display_path = file_path  # Default to original path
            
            if file_type == 'image':
                try:
                    # Create a permanent copy in chat images folder for display
                    chat_images_dir = os.path.join(os.path.expanduser('~'), '.messenger_chat_images')
                    os.makedirs(chat_images_dir, exist_ok=True)
                    
                    # Use timestamp to make unique filename
                    clean_timestamp = timestamp.replace(':', '').replace(' ', '_')
                    current_username = self.current_user.get('username', 'user') if self.current_user else 'user'
                    temp_file_path = os.path.join(chat_images_dir, f"sent_{current_username}_{clean_timestamp}_{file_name}")
                    
                    # Copy file to persistent location
                    shutil.copy2(file_path, temp_file_path)
                    display_path = temp_file_path
                    
                    print(f"📷 [SEND] Copied image for display to: {display_path}")
                    
                    # Verify the copy was successful
                    if os.path.exists(display_path):
                        print(f"✅ [SEND] Display image exists: {os.path.getsize(display_path)} bytes")
                    else:
                        print(f"❌ [SEND] Display image copy failed, using original path")
                        display_path = file_path
                        
                except Exception as e:
                    print(f"⚠️ [SEND] Could not copy image for display: {e}")
                    display_path = file_path
            
            local_message_data = {
                'message': file_name,
                'message_type': file_type,
                'file_path': display_path,  # Use the display path
                'file_name': file_name,
                'file_size': file_size,
                'mime_type': mime_type,
                'is_sent': True,
                'timestamp': timestamp,
                'sender': self.current_user.get('username', '') if self.current_user else ''
            }
            
            print(f"📎 [SEND] Storing message data: {local_message_data}")
            
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
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Send Error", f"Failed to send file: {str(e)}")

    def compress_image_if_needed(self, image_path, max_size):
        """Compress image if it exceeds size limit"""
        try:
            from PIL import Image
            import io
            
            # Open image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Get original size
                original_size = os.path.getsize(image_path)
                
                if original_size <= max_size:
                    # No compression needed
                    with open(image_path, 'rb') as f:
                        return f.read(), original_size
                
                # Try different compression levels
                for quality in [85, 70, 55, 40, 25]:
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=quality, optimize=True)
                    compressed_data = output.getvalue()
                    
                    if len(compressed_data) <= max_size:
                        print(f"📷 [COMPRESS] Compressed to quality {quality}%")
                        return compressed_data, len(compressed_data)
                
                # If still too large, resize the image
                width, height = img.size
                for scale in [0.8, 0.6, 0.4, 0.2]:
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    output = io.BytesIO()
                    resized_img.save(output, format='JPEG', quality=70, optimize=True)
                    compressed_data = output.getvalue()
                    
                    if len(compressed_data) <= max_size:
                        print(f"📷 [COMPRESS] Resized to {scale*100}% and compressed")
                        return compressed_data, len(compressed_data)
                
                # If all else fails, return original and let error handling deal with it
                with open(image_path, 'rb') as f:
                    return f.read(), original_size
                    
        except ImportError:
            print("⚠️ [COMPRESS] PIL not available, cannot compress images")
            # Fall back to original file
            with open(image_path, 'rb') as f:
                return f.read(), os.path.getsize(image_path)
        except Exception as e:
            print(f"❌ [COMPRESS] Error compressing image: {e}")
            # Fall back to original file
            with open(image_path, 'rb') as f:
                return f.read(), os.path.getsize(image_path)

    def debug_message_data(self, message_data, context=""):
        """Debug helper to print message data structure"""
        print(f"🔍 DEBUG {context}:")
        print(f"  message: {message_data.get('message', 'N/A')}")
        print(f"  message_type: {message_data.get('message_type', 'N/A')}")
        print(f"  file_name: {message_data.get('file_name', 'N/A')}")
        print(f"  file_path: {message_data.get('file_path', 'N/A')}")
        print(f"  file_size: {message_data.get('file_size', 'N/A')}")
        print(f"  is_sent: {message_data.get('is_sent', 'N/A')}")
        print(f"  sender: {message_data.get('sender', 'N/A')}")
        if message_data.get('file_path'):
            file_exists = os.path.exists(message_data['file_path'])
            file_size = os.path.getsize(message_data['file_path']) if file_exists else 0
            print(f"  file_exists: {file_exists}")
            print(f"  actual_file_size: {file_size}")

    def add_message_to_display_with_type(self, message_data):
        """Add message with type info to chat display"""
        if not hasattr(self, 'messages_layout'):
            return
        
        # Debug the message data
        self.debug_message_data(message_data, "DISPLAY")
        
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
        """Create enhanced message bubble widget that handles text, images, and files with click support"""
        container = QFrame()
        container.setStyleSheet("background-color: transparent; border: none;")
    
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
    
        # Get message info
        message_text = message_data.get('message', '')
        is_sent = message_data.get('is_sent', False)
        timestamp = message_data.get('timestamp', '')
        message_type = message_data.get('message_type', 'text')
    
        print(f"🎨 [UI] Creating widget for {message_type} message:")
        print(f"  text: {message_text}")
        print(f"  is_sent: {is_sent}")
        print(f"  file_path: {message_data.get('file_path', 'N/A')}")
    
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
            # Display image with click support
            image_label = QLabel()
            image_loaded = False
        
            # Try to load image from local path first
            image_path = message_data.get('file_path')
            print(f"🖼️ [UI] Attempting to load image from: {image_path}")
        
            if image_path and os.path.exists(image_path):
                try:
                    print(f"🖼️ [UI] File exists, size: {os.path.getsize(image_path)} bytes")
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        # Scale image to fit nicely in chat
                        scaled_pixmap = pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        image_label.setPixmap(scaled_pixmap)
                        image_loaded = True
                        print(f"✅ [UI] Successfully loaded image from: {image_path}")
                    else:
                        print(f"❌ [UI] Failed to load image (null pixmap): {image_path}")
                except Exception as e:
                    print(f"❌ [UI] Error loading image from {image_path}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                if image_path:
                    print(f"❌ [UI] Image file does not exist: {image_path}")
                else:
                    print(f"❌ [UI] No image path provided")
        
            # If image couldn't be loaded, show placeholder
            if not image_loaded:
                placeholder_pixmap = QPixmap(200, 150)
                placeholder_pixmap.fill(QColor(240, 240, 240))
            
                # Draw placeholder text
                painter = QPainter(placeholder_pixmap)
                painter.setPen(QColor(150, 150, 150))
                painter.drawText(placeholder_pixmap.rect(), Qt.AlignCenter, "📷\nImage\n(failed to load)")
                painter.end()
            
                image_label.setPixmap(placeholder_pixmap)
                print("⚠️ [UI] Using placeholder image")
        
            # FIX: Add click functionality for images
            image_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #B0C4C6;
                    border-radius: 8px;
                    background-color: white;
                }
                QLabel:hover {
                    border: 2px solid #7A9499;
                    cursor: pointer;
                }
            """)
            image_label.setScaledContents(False)
            image_label.setAlignment(Qt.AlignCenter)
            
            # Make image clickable
            image_label.mousePressEvent = lambda event: self.handle_image_click(message_data)
            image_label.setCursor(Qt.PointingHandCursor)
            
            bubble_layout.addWidget(image_label)
        
            # File name below image (if available and different from generic "Image")
            file_name = message_data.get('file_name', '')
            if file_name and file_name.lower() not in ['image', 'image.jpg', 'image.png']:
                name_label = QLabel(file_name)
                name_label.setStyleSheet("""
                    QLabel {
                        color: #2C2C2C;
                        font-size: 12px;
                        border: none;
                        background-color: transparent;
                    }
                """)
                name_label.setAlignment(Qt.AlignCenter)
                name_label.setWordWrap(True)
                bubble_layout.addWidget(name_label)
    
        elif message_type == 'file':
            # Display file icon and info with click support
            file_container = QFrame()
            file_container.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 100);
                    border: 1px solid #B0C4C6;
                    border-radius: 8px;
                    padding: 10px;
                }
                QFrame:hover {
                    border: 2px solid #7A9499;
                    cursor: pointer;
                }
            """)
            
            # Make file container clickable
            file_container.mousePressEvent = lambda event: self.handle_file_click(message_data)
            file_container.setCursor(Qt.PointingHandCursor)
            
            file_layout = QHBoxLayout(file_container)
            file_layout.setContentsMargins(10, 10, 10, 10)
        
            # File icon
            file_icon = QLabel("📄")
            file_icon.setStyleSheet("font-size: 24px;")
            file_layout.addWidget(file_icon)
        
            # File info
            info_layout = QVBoxLayout()
        
            file_name = message_data.get('file_name', message_text if message_text != 'File' else 'Unknown file')
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
            name_label.setWordWrap(True)
        
            file_size = message_data.get('file_size', 0)
            if file_size > 0:
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
            else:
                info_layout.addWidget(name_label)
        
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

    def handle_image_click(self, message_data):
        """Handle clicking on an image to view or download"""
        file_path = message_data.get('file_path')
        file_name = message_data.get('file_name', 'image.jpg')
        
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Image Not Found", "The image file could not be found.")
            return
        
        # Show options: View or Download
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Image Options")
        msg_box.setText(f"What would you like to do with '{file_name}'?")
        
        view_btn = msg_box.addButton("View", QMessageBox.ActionRole)
        download_btn = msg_box.addButton("Download", QMessageBox.ActionRole)
        cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        
        msg_box.exec_()
        
        if msg_box.clickedButton() == view_btn:
            # Open image with default system viewer
            try:
                import subprocess
                import platform
                
                if platform.system() == 'Windows':
                    os.startfile(file_path)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.call(['open', file_path])
                else:  # Linux
                    subprocess.call(['xdg-open', file_path])
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open image: {str(e)}")
                
        elif msg_box.clickedButton() == download_btn:
            self.download_file(file_path, file_name)

    def handle_file_click(self, message_data):
        """Handle clicking on a file to download"""
        file_name = message_data.get('file_name', 'file')
        
        # For files, we typically don't have the actual file data locally
        # We would need to request it from the server or download it
        QMessageBox.information(self, "File Download", 
                               f"File download functionality for '{file_name}' would be implemented here.\n"
                               f"This would typically request the file from the server.")

    def download_file(self, source_path, suggested_name):
        """Download/copy file to user-selected location"""
        try:
            # Let user choose where to save
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save File",
                suggested_name,
                "All Files (*.*)"
            )
            
            if save_path:
                # Copy file to chosen location
                shutil.copy2(source_path, save_path)
                QMessageBox.information(self, "Download Complete", 
                                      f"File saved to:\n{save_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"Failed to download file: {str(e)}")

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