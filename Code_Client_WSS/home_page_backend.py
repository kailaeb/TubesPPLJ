# # """
# # Enhanced Home Page with Full Chat History Support

# # IMPORTANT: For this to work properly, your WebSocket server must send COMPLETE conversation data.

# # Server Requirements:
# # 1. When sending "previous_conversations", include ALL messages from BOTH participants
# # 2. Each message should have:
# #    - sender_username: The actual sender of the message
# #    - recipient_id: The recipient of the message  
# #    - content: Message content
# #    - timestamp: When the message was sent
# #    - message_type: "text", "image", or "file"
# #    - For files: file_name, file_size, mime_type, file_data (base64)

# # 3. Server should respond to "request_conversation_history" requests with:
# #    {
# #      "type": "conversation_history_response", 
# #      "friend_username": "...",
# #      "messages": [/* all messages between current user and friend */]
# #    }

# # This client will automatically:
# # - Detect incomplete conversations (only sent OR only received messages)
# # - Request missing conversation history from the server
# # - Display both sent and received messages properly in chat bubbles
# # - Handle images and files with local caching for persistent display
# # """

# # from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
# #                              QLineEdit, QPushButton, QFrame, QScrollArea, QTextEdit,
# #                              QFileDialog, QDialog, QGridLayout, QMessageBox)
# # from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QThread
# # from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QIcon
# # from navigation_sidebar import NavigationSidebar
# # import json
# # import base64
# # import os
# # import asyncio
# # import websockets
# # import ssl

# # # Configure logging
# # logging.basicConfig(level=logging.INFO)
# # logger = logging.getLogger(__name__)


# # class DownloadManager(QObject):
# #     """Manages file download operations."""
# #     download_progress = pyqtSignal(str, int)  # file_path, percentage
# #     download_complete = pyqtSignal(str, str)  # file_path, local_save_path
# #     download_error = pyqtSignal(str, str)    # file_path, error_message

# #     def __init__(self, websocket_client):
# #         super().__init__()
# #         self.websocket_client = websocket_client
# #         self.active_downloads = {}

# #     def start_download(self, file_info, save_path):
# #         """Initiates a file download request."""
# #         file_path = file_info.get("file_path")
# #         if not file_path:
# #             self.download_error.emit("", "File path is missing.")
# #             return

# #         print(f"📥 Requesting download for: {file_path} -> {save_path}")
        
# #         # Create a downloader thread
# #         downloader = FileDownloader(self.websocket_client, file_info, save_path)
# #         downloader.download_complete.connect(self.download_complete)
# #         downloader.download_error.connect(self.download_error)
        
# #         self.active_downloads[file_path] = downloader
# #         downloader.start()

# # class FileDownloader(QThread):
# #     """Worker thread to handle a single file download."""
# #     download_complete = pyqtSignal(str, str)
# #     download_error = pyqtSignal(str, str)

# #     def __init__(self, websocket_client, file_info, save_path):
# #         super().__init__()
# #         self.websocket_client = websocket_client
# #         self.file_info = file_info
# #         self.save_path = save_path

# #     def run(self):
# #         """Send download request and wait for response."""
# #         file_path = self.file_info.get("file_path")
        
# #         # Register a callback to wait for the specific file
# #         future = self.websocket_client.request_file_data(file_path)
        
# #         try:
# #             # Wait for the file data to be received
# #             file_data_b64 = future.result(timeout=30) # 30-second timeout
            
# #             if file_data_b64:
# #                 print(f"📦 Received file data for {file_path}, decoding and saving...")
# #                 # Decode and save the file
# #                 file_bytes = base64.b64decode(file_data_b64)
# #                 with open(self.save_path, 'wb') as f:
# #                     f.write(file_bytes)
# #                 print(f"✅ Successfully saved to {self.save_path}")
# #                 self.download_complete.emit(file_path, self.save_path)
# #             else:
# #                 self.download_error.emit(file_path, "No data received from server.")

# #         except asyncio.TimeoutError:
# #             self.download_error.emit(file_path, "Download request timed out.")
# #         except Exception as e:
# #             self.download_error.emit(file_path, f"An error occurred: {str(e)}")
# #         finally:
# #             # Clean up the callback
# #             self.websocket_client.cleanup_file_request(file_path)

# # class FileSelectionDialog(QDialog):
# #     """Dialog for selecting file or image to send"""
    
# #     def __init__(self, parent=None):
# #         super().__init__(parent)
# #         self.selected_file_path = None
# #         self.file_type = None  # 'image' or 'file'
# #         self.setup_ui()
    
# #     def setup_ui(self):
# #         """Setup the file selection dialog UI"""
# #         self.setWindowTitle("Send File")
# #         self.setFixedSize(400, 200)
# #         self.setStyleSheet("""
# #             QDialog {
# #                 background-color: #E8E1E1;
# #             }
# #         """)
        
# #         layout = QVBoxLayout(self)
# #         layout.setSpacing(20)
# #         layout.setContentsMargins(30, 30, 30, 30)
        
# #         # Title
# #         title = QLabel("Choose what to send")
# #         title.setAlignment(Qt.AlignCenter)
# #         title.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 18px;
# #                 font-weight: bold;
# #             }
# #         """)
# #         layout.addWidget(title)
        
# #         # Buttons
# #         button_layout = QGridLayout()
# #         button_layout.setSpacing(15)
        
# #         # Image button
# #         image_btn = QPushButton("📷\nSelect Image")
# #         image_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: #9DB4B8;
# #                 color: #2C2C2C;
# #                 border: none;
# #                 border-radius: 10px;
# #                 padding: 20px;
# #                 font-size: 14px;
# #                 font-weight: bold;
# #                 min-height: 80px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #8BA5A9;
# #             }
# #         """)
# #         image_btn.clicked.connect(self.select_image)
        
# #         # File button
# #         file_btn = QPushButton("📄\nSelect File")
# #         file_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: #9DB4B8;
# #                 color: #2C2C2C;
# #                 border: none;
# #                 border-radius: 10px;
# #                 padding: 20px;
# #                 font-size: 14px;
# #                 font-weight: bold;
# #                 min-height: 80px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #8BA5A9;
# #             }
# #         """)
# #         file_btn.clicked.connect(self.select_file)
        
# #         button_layout.addWidget(image_btn, 0, 0)
# #         button_layout.addWidget(file_btn, 0, 1)
# #         layout.addLayout(button_layout)
        
# #         # Cancel button
# #         cancel_btn = QPushButton("Cancel")
# #         cancel_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: #7F8C8D;
# #                 color: white;
# #                 border: none;
# #                 border-radius: 8px;
# #                 padding: 10px;
# #                 font-size: 14px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #6C7B7C;
# #             }
# #         """)
# #         cancel_btn.clicked.connect(self.reject)
# #         layout.addWidget(cancel_btn)
    
# #     def select_image(self):
# #         """Open image file dialog"""
# #         file_path, _ = QFileDialog.getOpenFileName(
# #             self,
# #             "Select Image",
# #             "",
# #             "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
# #         )
        
# #         if file_path:
# #             self.selected_file_path = file_path
# #             self.file_type = 'image'
# #             self.accept()
    
# #     def select_file(self):
# #         """Open general file dialog"""
# #         file_path, _ = QFileDialog.getOpenFileName(
# #             self,
# #             "Select File",
# #             "",
# #             "All Files (*.*)"
# #         )
        
# #         if file_path:
# #             self.selected_file_path = file_path
# #             self.file_type = 'file'
# #             self.accept()

# # class WebSocketThread(QThread):
# #     """Simplified WebSocket thread for messaging"""
    
# #     # Core signals
# #     previous_conversations_received = pyqtSignal(dict) 
# #     conversation_history_received = pyqtSignal(str, list)  # friend_username, messages
# #     message_received = pyqtSignal(str, str, str, str, dict)  # from_username, message, timestamp, message_type, file_data
# #     connection_established = pyqtSignal()
# #     connection_lost = pyqtSignal()
# #     message_sent_confirmation = pyqtSignal(str, str, str, bool)
    
# #     def __init__(self, auth_token):
# #         super().__init__()
# #         self.auth_token = auth_token
# #         self.websocket = None
# #         self.running = False
# #         self.message_queue = []
# #         self.loop = None
# #         self.current_username = ""  # Track current username to avoid self-messages
    
# #     def set_current_username(self, username):
# #         """Set the current username for filtering self-messages"""
# #         self.current_username = username
# #         print(f"🔧 [WS] Current username set to: {username}")
    
# #     def run(self):
# #         """Main thread execution"""
# #         self.running = True
# #         self.loop = asyncio.new_event_loop()
# #         asyncio.set_event_loop(self.loop)
# #         self.loop.run_until_complete(self.websocket_main())
    
# #     async def websocket_main(self):
# #         """Main WebSocket connection handler with increased size limits"""
# #         while self.running:
# #             try:
# #                 logger.info("Connecting to WebSocket server...")
# #                 ssl_context = ssl._create_unverified_context()
                
# #                 # IMPORTANT: Increase message size limit to handle chat history with images
# #                 self.websocket = await websockets.connect(
# #                     "wss://localhost:8443", 
# #                     ssl=ssl_context,
# #                     max_size=10 * 1024 * 1024,  # 10MB limit instead of default 1MB
# #                     ping_interval=30,
# #                     ping_timeout=10,
# #                     compression=None  # Disable compression to save processing
# #                 )
                
# #                 # Send authentication
# #                 auth_message = {"token": self.auth_token, "session_id": "home_chat"}
# #                 await self.websocket.send(json.dumps(auth_message))
                
# #                 logger.info("Successfully connected and authenticated")
# #                 self.connection_established.emit()
                
# #                 # Send any queued messages
# #                 await self.send_queued_messages()
                
# #                 # Listen for messages
# #                 await self.listen_for_messages()
                
# #             except websockets.exceptions.ConnectionClosedError as e:
# #                 if "message too big" in str(e):
# #                     logger.error(f"❌ [WS] Message size limit exceeded: {e}")
# #                     logger.error("💡 [WS] Server sent message larger than 10MB limit")
# #                     logger.error("🔧 [WS] This might indicate server needs to implement pagination")
# #                 else:
# #                     logger.error(f"❌ [WS] WebSocket connection closed: {e}")
# #                 self.connection_lost.emit()
# #                 if self.running:
# #                     await asyncio.sleep(5)
# #             except Exception as e:
# #                 logger.error(f"WebSocket connection error: {e}")
# #                 self.connection_lost.emit()
# #                 if self.running:
# #                     await asyncio.sleep(5)
    
# #     async def send_queued_messages(self):
# #         """Send any queued messages"""
# #         while self.message_queue and self.websocket:
# #             try:
# #                 message_data = self.message_queue.pop(0)
# #                 await self.websocket.send(json.dumps(message_data))
# #                 logger.info(f"📤 Sent queued message: {message_data}")
# #             except Exception as e:
# #                 logger.error(f"❌ Failed to send queued message: {e}")
# #                 self.message_queue.insert(0, message_data)
# #                 break
    
# #     async def listen_for_messages(self):
# #         """Listen for incoming messages with improved error handling"""
# #         try:
# #             async for message in self.websocket:
# #                 try:
# #                     print(f"DEBUG: Raw message fetched from server: {message[:200]}..." if len(message) > 200 else message)
# #                     data = json.loads(message)
# #                     message_type = data.get("type")
                    
# #                     logger.info(f"📨 [WS] Received message type: {message_type}")
                    
# #                     if message_type == "previous_conversations":
# #                         logger.info("📚 [WS] Processing previous_conversations message...")
# #                         await self.handle_previous_conversations(data)
# #                     elif message_type == "new_message":
# #                         logger.info("📨 [WS] Processing new_message...")
# #                         await self.handle_new_message(data)
# #                     elif message_type == "message_sent":
# #                         logger.info("✅ [WS] Processing message_sent confirmation...")
# #                         await self.handle_message_sent(data)
# #                     elif message_type == "conversation_history_response":
# #                         logger.info("📚 [WS] Processing conversation_history_response...")
# #                         await self.handle_conversation_history_response(data)
# #                     elif message_type == "auth_success":
# #                         logger.info("🔑 [WS] Authentication successful")
# #                     else:
# #                         logger.info(f"❓ [WS] Unhandled message type: {message_type}")
                
# #                 except json.JSONDecodeError as e:
# #                     logger.error(f"❌ [WS] Failed to decode JSON message: {e}")
# #                     continue
# #                 except Exception as e:
# #                     logger.error(f"❌ [WS] Error processing individual message: {e}")
# #                     import traceback
# #                     traceback.print_exc()
# #                     continue
                    
# #         except websockets.exceptions.ConnectionClosedError as e:
# #             if "message too big" in str(e):
# #                 logger.error(f"❌ [WS] Connection closed - message too big: {e}")
# #                 logger.error("💡 [WS] The server sent a message that exceeded size limits")
# #                 logger.error("🔧 [WS] Try clearing chat history or reducing file sizes")
# #             else:
# #                 logger.error(f"❌ [WS] Connection closed: {e}")
# #         except Exception as e:
# #             logger.error(f"❌ [WS] Error in listen_for_messages: {e}")
# #             import traceback
# #             traceback.print_exc()
    
# #     async def handle_previous_conversations(self, data):
# #         """Handle previous conversations from server with enhanced debugging"""
# #         try:
# #             logger.info("📚 [WS] Starting to process previous conversations...")
# #             conversations_data = data.get("conversations", {})
            
# #             logger.info(f"📚 [WS] Conversations data type: {type(conversations_data)}")
# #             logger.info(f"📚 [WS] Raw conversations data: {conversations_data}")
            
# #             friend_conversations = {}
# #             # Use the current username from WebSocket thread if available, otherwise fallback
# #             current_username = self.current_username or "indira123"
# #             logger.info(f"📚 [WS] Current username for processing: {current_username}")
            
# #             # Handle dict format: {room_id: [messages]}
# #             if isinstance(conversations_data, dict):
# #                 logger.info(f"📚 [WS] Processing dict format with {len(conversations_data)} rooms")
                
# #                 for room_id, messages in conversations_data.items():
# #                     logger.info(f"📚 [WS] *** Processing room {room_id} with {len(messages) if messages else 0} messages ***")
                    
# #                     if not messages:
# #                         logger.info(f"📚 [WS] Skipping empty room {room_id}")
# #                         continue
                    
# #                     # Debug: Print all messages in this room
# #                     logger.info(f"📚 [WS] Messages in room {room_id}:")
# #                     for i, msg in enumerate(messages):
# #                         sender = msg.get("sender_username", "")
# #                         content = msg.get("content", "")[:50]
# #                         msg_type = msg.get("message_type", "text")
# #                         logger.info(f"📚 [WS]   {i+1}. From: {sender}, Content: {content}, Type: {msg_type}")
                    
# #                     # Find friend username - ENHANCED LOGIC
# #                     friend_username = None
# #                     participants = set()
                    
# #                     # Collect all participants in this conversation
# #                     for msg in messages:
# #                         sender = msg.get("sender_username", "")
# #                         recipient_id = msg.get("recipient_id", "")
                        
# #                         if sender:
# #                             participants.add(sender)
# #                         if recipient_id and isinstance(recipient_id, str):
# #                             participants.add(recipient_id)
                    
# #                     logger.info(f"📚 [WS] Room {room_id} participants: {participants}")
# #                     logger.info(f"📚 [WS] Current username: {current_username}")
                    
# #                     # Remove current user from participants to find the friend
# #                     participants.discard(current_username)
                    
# #                     if len(participants) == 1:
# #                         friend_username = list(participants)[0]
# #                         logger.info(f"📚 [WS] ✅ Found friend: {friend_username} in room {room_id}")
# #                     elif len(participants) > 1:
# #                         logger.warning(f"📚 [WS] ⚠️ Multiple participants in room {room_id}: {participants}")
# #                         # Take the first non-current-user participant
# #                         friend_username = list(participants)[0]
# #                         logger.info(f"📚 [WS] Using first participant as friend: {friend_username}")
# #                     else:
# #                         logger.warning(f"📚 [WS] ❌ No friend found in room {room_id}")
# #                         logger.warning(f"📚 [WS] This might be a single-user room or all messages are from {current_username}")
                        
# #                         # FIX: Try to infer friend from message context
# #                         # Look for any recipient_id that's not the current user
# #                         for msg in messages:
# #                             recipient = msg.get("recipient_id", "")
# #                             sender = msg.get("sender_username", "")
                            
# #                             if recipient and recipient != current_username:
# #                                 friend_username = recipient
# #                                 logger.info(f"📚 [WS] ✅ Inferred friend from recipient_id: {friend_username}")
# #                                 break
# #                             elif sender != current_username and sender:
# #                                 friend_username = sender
# #                                 logger.info(f"📚 [WS] ✅ Inferred friend from sender: {friend_username}")
# #                                 break
                        
# #                         if not friend_username:
# #                             logger.warning(f"📚 [WS] ❌ Could not determine friend for room {room_id}, skipping")
# #                             continue
                    
# #                     # Verify friend_username is not the current user
# #                     if friend_username == current_username:
# #                         logger.warning(f"📚 [WS] Skipping room {room_id} - friend is current user (self-conversation)")
# #                         continue
                    
# #                     if friend_username:
# #                         if friend_username not in friend_conversations:
# #                             friend_conversations[friend_username] = []
                        
# #                         logger.info(f"📚 [WS] *** Processing {len(messages)} messages for conversation with {friend_username} ***")
                        
# #                         # FIX: Process ALL messages regardless of sender
# #                         processed_count = 0
# #                         sent_count = 0
# #                         received_count = 0
                        
# #                         # Sort messages by timestamp if available
# #                         try:
# #                             messages_sorted = sorted(messages, key=lambda x: x.get("timestamp", ""))
# #                         except:
# #                             messages_sorted = messages
                        
# #                         for msg in messages_sorted:
# #                             processed_msg = self.process_message(msg, current_username, friend_username)
# #                             if processed_msg:
# #                                 friend_conversations[friend_username].append(processed_msg)
# #                                 processed_count += 1
                                
# #                                 if processed_msg['is_sent']:
# #                                     sent_count += 1
# #                                     logger.info(f"📤 [WS] Sent message: {processed_msg['message'][:30]}... at {processed_msg['timestamp']}")
# #                                 else:
# #                                     received_count += 1
# #                                     logger.info(f"📥 [WS] Received message: {processed_msg['message'][:30]}... at {processed_msg['timestamp']}")
# #                             else:
# #                                 logger.warning(f"📚 [WS] Failed to process message: {msg}")
                        
# #                         logger.info(f"📚 [WS] *** SUMMARY for {friend_username}: {processed_count} total, {sent_count} sent, {received_count} received ***")
# #                     else:
# #                         logger.warning(f"📚 [WS] No friend username found for room {room_id}")
            
# #             # Handle list format
# #             elif isinstance(conversations_data, list):
# #                 logger.info(f"📚 [WS] Processing list format with {len(conversations_data)} conversations")
                
# #                 for conversation in conversations_data:
# #                     if isinstance(conversation, dict):
# #                         # Server sends metadata format: {room_id, other_user, last_message_time}
# #                         room_id = conversation.get("room_id")
# #                         other_user_id = conversation.get("other_user")  # This should be the friend's username
# #                         last_message_time = conversation.get("last_message_time")
                        
# #                         logger.info(f"📚 [WS] Processing conversation metadata:")
# #                         logger.info(f"📚 [WS]   room_id: {room_id}")
# #                         logger.info(f"📚 [WS]   other_user_id: {other_user_id}")
                        
# #                         # Use the actual other_user from server response
# #                         if room_id and other_user_id:
# #                             friend_username = other_user_id  # Use the actual friend username from server
                            
# #                             # Make sure it's not the current user
# #                             if friend_username == current_username:
# #                                 logger.warning(f"📚 [WS] Skipping room {room_id} - other_user is current user")
# #                                 continue
                            
# #                             logger.info(f"📚 [WS] Processing conversation with friend: {friend_username}")
                            
# #                             if friend_username not in friend_conversations:
# #                                 friend_conversations[friend_username] = []
                            
# #                             # Add placeholder message indicating conversation exists
# #                             placeholder_message = {
# #                                 "sender": friend_username,
# #                                 "message": f"Previous conversation available (click to load)",
# #                                 "timestamp": self.format_timestamp(last_message_time, is_timestamp=False),
# #                                 "is_sent": False,
# #                                 "message_type": "text",
# #                                 "room_id": room_id  # Store room_id for future message loading
# #                             }
                            
# #                             friend_conversations[friend_username].append(placeholder_message)
# #                             logger.info(f"📚 [WS] Added placeholder for {friend_username}")
# #                         else:
# #                             logger.warning(f"📚 [WS] Missing room_id or other_user in conversation: {conversation}")
                        
# #                         # Handle legacy format (full conversation data) if server provides it
# #                         friend_username_full = conversation.get("friend_username") or conversation.get("username")
# #                         messages = conversation.get("messages", [])
                        
# #                         if friend_username_full and messages:
# #                             logger.info(f"📚 [WS] Processing full conversation data for {friend_username_full}")
# #                             if friend_username_full not in friend_conversations:
# #                                 friend_conversations[friend_username_full] = []
                            
# #                             # FIX: Enhanced message processing for legacy format
# #                             processed_count = 0
# #                             sent_count = 0
# #                             received_count = 0
                            
# #                             for msg in messages:
# #                                 processed_msg = self.process_message(msg, current_username, friend_username_full)
# #                                 if processed_msg:
# #                                     friend_conversations[friend_username_full].append(processed_msg)
# #                                     processed_count += 1
                                    
# #                                     if processed_msg['is_sent']:
# #                                         sent_count += 1
# #                                     else:
# #                                         received_count += 1
                            
# #                             logger.info(f"📚 [WS] Legacy format - {friend_username_full}: {processed_count} total, {sent_count} sent, {received_count} received")
# #             else:
# #                 logger.error(f"📚 [WS] Unexpected conversations data type: {type(conversations_data)}")
# #                 return
            
# #             logger.info(f"📚 [WS] *** FINAL RESULT: Processed conversations for {len(friend_conversations)} friends ***")
# #             for friend, msgs in friend_conversations.items():
# #                 sent_msgs = sum(1 for msg in msgs if msg.get('is_sent', False))
# #                 received_msgs = len(msgs) - sent_msgs
# #                 logger.info(f"📚 [WS]   {friend}: {len(msgs)} total ({sent_msgs} sent, {received_msgs} received)")
            
# #             # Emit the signal
# #             logger.info("📤 [WS] *** EMITTING previous_conversations_received SIGNAL ***")
# #             self.previous_conversations_received.emit(friend_conversations)
# #             logger.info("✅ [WS] *** SIGNAL EMITTED SUCCESSFULLY ***")
            
# #         except Exception as e:
# #             logger.error(f"❌ [WS] Error processing conversations: {e}")
# #             import traceback
# #             traceback.print_exc()
    
# #     async def handle_conversation_history_response(self, data):
# #         """Handle response to conversation history request"""
# #         try:
# #             friend_username = data.get("friend_username")
# #             messages = data.get("messages", [])
            
# #             logger.info(f"📚 [WS] Received conversation history response for {friend_username}: {len(messages)} messages")
            
# #             if not friend_username or not messages:
# #                 logger.warning(f"📚 [WS] Invalid conversation history response: friend={friend_username}, messages={len(messages) if messages else 0}")
# #                 return
            
# #             # Process messages using the same logic as previous conversations
# #             processed_messages = []
# #             current_username = self.current_username or "indira123"
            
# #             sent_count = 0
# #             received_count = 0
            
# #             for msg in messages:
# #                 processed_msg = self.process_message(msg, current_username, friend_username)
# #                 if processed_msg:
# #                     processed_messages.append(processed_msg)
# #                     if processed_msg['is_sent']:
# #                         sent_count += 1
# #                     else:
# #                         received_count += 1
            
# #             logger.info(f"📚 [WS] Processed conversation history for {friend_username}: {len(processed_messages)} total ({sent_count} sent, {received_count} received)")
            
# #             # Emit signal to update UI
# #             self.conversation_history_received.emit(friend_username, processed_messages)
            
# #         except Exception as e:
# #             logger.error(f"❌ [WS] Error processing conversation history response: {e}")
# #             import traceback
# #             traceback.print_exc()
    
# #     """
# # Enhanced Home Page with Full Chat History Support

# # IMPORTANT: For this to work properly, your WebSocket server must send COMPLETE conversation data.

# # Server Requirements:
# # 1. When sending "previous_conversations", include ALL messages from BOTH participants
# # 2. Each message should have:
# #    - sender_username: The actual sender of the message
# #    - recipient_id: The recipient of the message  
# #    - content: Message content
# #    - timestamp: When the message was sent
# #    - message_type: "text", "image", or "file"
# #    - For files: file_name, file_size, mime_type, file_data (base64)

# # 3. Server should respond to "request_conversation_history" requests with:
# #    {
# #      "type": "conversation_history_response", 
# #      "friend_username": "...",
# #      "messages": [/* all messages between current user and friend */]
# #    }

# # This client will automatically:
# # - Detect incomplete conversations (only sent OR only received messages)
# # - Request missing conversation history from the server
# # - Display both sent and received messages properly in chat bubbles
# # - Handle images and files with local caching for persistent display
# # """

# # from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
# #                              QLineEdit, QPushButton, QFrame, QScrollArea, QTextEdit,
# #                              QFileDialog, QDialog, QGridLayout, QMessageBox)
# # from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QThread
# # from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QIcon
# # from navigation_sidebar import NavigationSidebar
# # import datetime
# # import json
# # import asyncio
# # import websockets
# # import logging
# # import ssl
# # import base64
# # import os
# # import mimetypes
# # import tempfile
# # import shutil

# # # Configure logging
# # logging.basicConfig(level=logging.INFO)
# # logger = logging.getLogger(__name__)

# # class FileSelectionDialog(QDialog):
# #     """Dialog for selecting file or image to send"""
    
# #     def __init__(self, parent=None):
# #         super().__init__(parent)
# #         self.selected_file_path = None
# #         self.file_type = None  # 'image' or 'file'
# #         self.setup_ui()
    
# #     def setup_ui(self):
# #         """Setup the file selection dialog UI"""
# #         self.setWindowTitle("Send File")
# #         self.setFixedSize(400, 200)
# #         self.setStyleSheet("""
# #             QDialog {
# #                 background-color: #E8E1E1;
# #             }
# #         """)
        
# #         layout = QVBoxLayout(self)
# #         layout.setSpacing(20)
# #         layout.setContentsMargins(30, 30, 30, 30)
        
# #         # Title
# #         title = QLabel("Choose what to send")
# #         title.setAlignment(Qt.AlignCenter)
# #         title.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 18px;
# #                 font-weight: bold;
# #             }
# #         """)
# #         layout.addWidget(title)
        
# #         # Buttons
# #         button_layout = QGridLayout()
# #         button_layout.setSpacing(15)
        
# #         # Image button
# #         image_btn = QPushButton("📷\nSelect Image")
# #         image_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: #9DB4B8;
# #                 color: #2C2C2C;
# #                 border: none;
# #                 border-radius: 10px;
# #                 padding: 20px;
# #                 font-size: 14px;
# #                 font-weight: bold;
# #                 min-height: 80px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #8BA5A9;
# #             }
# #         """)
# #         image_btn.clicked.connect(self.select_image)
        
# #         # File button
# #         file_btn = QPushButton("📄\nSelect File")
# #         file_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: #9DB4B8;
# #                 color: #2C2C2C;
# #                 border: none;
# #                 border-radius: 10px;
# #                 padding: 20px;
# #                 font-size: 14px;
# #                 font-weight: bold;
# #                 min-height: 80px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #8BA5A9;
# #             }
# #         """)
# #         file_btn.clicked.connect(self.select_file)
        
# #         button_layout.addWidget(image_btn, 0, 0)
# #         button_layout.addWidget(file_btn, 0, 1)
# #         layout.addLayout(button_layout)
        
# #         # Cancel button
# #         cancel_btn = QPushButton("Cancel")
# #         cancel_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: #7F8C8D;
# #                 color: white;
# #                 border: none;
# #                 border-radius: 8px;
# #                 padding: 10px;
# #                 font-size: 14px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #6C7B7C;
# #             }
# #         """)
# #         cancel_btn.clicked.connect(self.reject)
# #         layout.addWidget(cancel_btn)
    
# #     def select_image(self):
# #         """Open image file dialog"""
# #         file_path, _ = QFileDialog.getOpenFileName(
# #             self,
# #             "Select Image",
# #             "",
# #             "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
# #         )
        
# #         if file_path:
# #             self.selected_file_path = file_path
# #             self.file_type = 'image'
# #             self.accept()
    
# #     def select_file(self):
# #         """Open general file dialog"""
# #         file_path, _ = QFileDialog.getOpenFileName(
# #             self,
# #             "Select File",
# #             "",
# #             "All Files (*.*)"
# #         )
        
# #         if file_path:
# #             self.selected_file_path = file_path
# #             self.file_type = 'file'
# #             self.accept()

# # class WebSocketThread(QThread):
# #     """Simplified WebSocket thread for messaging"""
    
# #     # Core signals
# #     previous_conversations_received = pyqtSignal(dict) 
# #     conversation_history_received = pyqtSignal(str, list)  # friend_username, messages
# #     message_received = pyqtSignal(str, str, str, str, dict)  # from_username, message, timestamp, message_type, file_data
# #     connection_established = pyqtSignal()
# #     connection_lost = pyqtSignal()
# #     message_sent_confirmation = pyqtSignal(str, str, str, bool)
    
# #     def __init__(self, auth_token):
# #         super().__init__()
# #         self.auth_token = auth_token
# #         self.websocket = None
# #         self.running = False
# #         self.message_queue = []
# #         self.loop = None
# #         self.current_username = ""  # Track current username to avoid self-messages
    
# #     def set_current_username(self, username):
# #         """Set the current username for filtering self-messages"""
# #         self.current_username = username
# #         print(f"🔧 [WS] Current username set to: {username}")
    
# #     def run(self):
# #         """Main thread execution"""
# #         self.running = True
# #         self.loop = asyncio.new_event_loop()
# #         asyncio.set_event_loop(self.loop)
# #         self.loop.run_until_complete(self.websocket_main())
    
# #     async def websocket_main(self):
# #         """Main WebSocket connection handler with increased size limits"""
# #         while self.running:
# #             try:
# #                 logger.info("Connecting to WebSocket server...")
# #                 ssl_context = ssl._create_unverified_context()
                
# #                 # IMPORTANT: Increase message size limit to handle chat history with images
# #                 self.websocket = await websockets.connect(
# #                     "wss://localhost:8443", 
# #                     ssl=ssl_context,
# #                     max_size=10 * 1024 * 1024,  # 10MB limit instead of default 1MB
# #                     ping_interval=30,
# #                     ping_timeout=10,
# #                     compression=None  # Disable compression to save processing
# #                 )
                
# #                 # Send authentication
# #                 auth_message = {"token": self.auth_token, "session_id": "home_chat"}
# #                 await self.websocket.send(json.dumps(auth_message))
                
# #                 logger.info("Successfully connected and authenticated")
# #                 self.connection_established.emit()
                
# #                 # Send any queued messages
# #                 await self.send_queued_messages()
                
# #                 # Listen for messages
# #                 await self.listen_for_messages()
                
# #             except websockets.exceptions.ConnectionClosedError as e:
# #                 if "message too big" in str(e):
# #                     logger.error(f"❌ [WS] Message size limit exceeded: {e}")
# #                     logger.error("💡 [WS] Server sent message larger than 10MB limit")
# #                     logger.error("🔧 [WS] This might indicate server needs to implement pagination")
# #                 else:
# #                     logger.error(f"❌ [WS] WebSocket connection closed: {e}")
# #                 self.connection_lost.emit()
# #                 if self.running:
# #                     await asyncio.sleep(5)
# #             except Exception as e:
# #                 logger.error(f"WebSocket connection error: {e}")
# #                 self.connection_lost.emit()
# #                 if self.running:
# #                     await asyncio.sleep(5)
    
# #     async def send_queued_messages(self):
# #         """Send any queued messages"""
# #         while self.message_queue and self.websocket:
# #             try:
# #                 message_data = self.message_queue.pop(0)
# #                 await self.websocket.send(json.dumps(message_data))
# #                 logger.info(f"📤 Sent queued message: {message_data}")
# #             except Exception as e:
# #                 logger.error(f"❌ Failed to send queued message: {e}")
# #                 self.message_queue.insert(0, message_data)
# #                 break
    
# #     async def listen_for_messages(self):
# #         """Listen for incoming messages with improved error handling"""
# #         try:
# #             async for message in self.websocket:
# #                 try:
# #                     print(f"DEBUG: Raw message fetched from server: {message[:200]}..." if len(message) > 200 else message)
# #                     data = json.loads(message)
# #                     message_type = data.get("type")
                    
# #                     logger.info(f"📨 [WS] Received message type: {message_type}")
                    
# #                     if message_type == "previous_conversations":
# #                         logger.info("📚 [WS] Processing previous_conversations message...")
# #                         await self.handle_previous_conversations(data)
# #                     elif message_type == "new_message":
# #                         logger.info("📨 [WS] Processing new_message...")
# #                         await self.handle_new_message(data)
# #                     elif message_type == "message_sent":
# #                         logger.info("✅ [WS] Processing message_sent confirmation...")
# #                         await self.handle_message_sent(data)
# #                     elif message_type == "conversation_history_response":
# #                         logger.info("📚 [WS] Processing conversation_history_response...")
# #                         await self.handle_conversation_history_response(data)
# #                     elif message_type == "auth_success":
# #                         logger.info("🔑 [WS] Authentication successful")
# #                     else:
# #                         logger.info(f"❓ [WS] Unhandled message type: {message_type}")
                
# #                 except json.JSONDecodeError as e:
# #                     logger.error(f"❌ [WS] Failed to decode JSON message: {e}")
# #                     continue
# #                 except Exception as e:
# #                     logger.error(f"❌ [WS] Error processing individual message: {e}")
# #                     import traceback
# #                     traceback.print_exc()
# #                     continue
                    
# #         except websockets.exceptions.ConnectionClosedError as e:
# #             if "message too big" in str(e):
# #                 logger.error(f"❌ [WS] Connection closed - message too big: {e}")
# #                 logger.error("💡 [WS] The server sent a message that exceeded size limits")
# #                 logger.error("🔧 [WS] Try clearing chat history or reducing file sizes")
# #             else:
# #                 logger.error(f"❌ [WS] Connection closed: {e}")
# #         except Exception as e:
# #             logger.error(f"❌ [WS] Error in listen_for_messages: {e}")
# #             import traceback
# #             traceback.print_exc()
    
# #     async def handle_previous_conversations(self, data):
# #         """Handle previous conversations from server with enhanced debugging"""
# #         try:
# #             logger.info("📚 [WS] Starting to process previous conversations...")
# #             conversations_data = data.get("conversations", {})
            
# #             logger.info(f"📚 [WS] Conversations data type: {type(conversations_data)}")
# #             logger.info(f"📚 [WS] Raw conversations data: {conversations_data}")
            
# #             friend_conversations = {}
# #             # Use the current username from WebSocket thread if available, otherwise fallback
# #             current_username = self.current_username or "indira123"
# #             logger.info(f"📚 [WS] Current username for processing: {current_username}")
            
# #             # Handle dict format: {room_id: [messages]}
# #             if isinstance(conversations_data, dict):
# #                 logger.info(f"📚 [WS] Processing dict format with {len(conversations_data)} rooms")
                
# #                 for room_id, messages in conversations_data.items():
# #                     logger.info(f"📚 [WS] *** Processing room {room_id} with {len(messages) if messages else 0} messages ***")
                    
# #                     if not messages:
# #                         logger.info(f"📚 [WS] Skipping empty room {room_id}")
# #                         continue
                    
# #                     # Debug: Print all messages in this room
# #                     logger.info(f"📚 [WS] Messages in room {room_id}:")
# #                     for i, msg in enumerate(messages):
# #                         sender = msg.get("sender_username", "")
# #                         content = msg.get("content", "")[:50]
# #                         msg_type = msg.get("message_type", "text")
# #                         logger.info(f"📚 [WS]   {i+1}. From: {sender}, Content: {content}, Type: {msg_type}")
                    
# #                     # Find friend username - ENHANCED LOGIC
# #                     friend_username = None
# #                     participants = set()
                    
# #                     # Collect all participants in this conversation
# #                     for msg in messages:
# #                         sender = msg.get("sender_username", "")
# #                         recipient_id = msg.get("recipient_id", "")
                        
# #                         if sender:
# #                             participants.add(sender)
# #                         if recipient_id and isinstance(recipient_id, str):
# #                             participants.add(recipient_id)
                    
# #                     logger.info(f"📚 [WS] Room {room_id} participants: {participants}")
# #                     logger.info(f"📚 [WS] Current username: {current_username}")
                    
# #                     # Remove current user from participants to find the friend
# #                     participants.discard(current_username)
                    
# #                     if len(participants) == 1:
# #                         friend_username = list(participants)[0]
# #                         logger.info(f"📚 [WS] ✅ Found friend: {friend_username} in room {room_id}")
# #                     elif len(participants) > 1:
# #                         logger.warning(f"📚 [WS] ⚠️ Multiple participants in room {room_id}: {participants}")
# #                         # Take the first non-current-user participant
# #                         friend_username = list(participants)[0]
# #                         logger.info(f"📚 [WS] Using first participant as friend: {friend_username}")
# #                     else:
# #                         logger.warning(f"📚 [WS] ❌ No friend found in room {room_id}")
# #                         logger.warning(f"📚 [WS] This might be a single-user room or all messages are from {current_username}")
                        
# #                         # FIX: Try to infer friend from message context
# #                         # Look for any recipient_id that's not the current user
# #                         for msg in messages:
# #                             recipient = msg.get("recipient_id", "")
# #                             sender = msg.get("sender_username", "")
                            
# #                             if recipient and recipient != current_username:
# #                                 friend_username = recipient
# #                                 logger.info(f"📚 [WS] ✅ Inferred friend from recipient_id: {friend_username}")
# #                                 break
# #                             elif sender != current_username and sender:
# #                                 friend_username = sender
# #                                 logger.info(f"📚 [WS] ✅ Inferred friend from sender: {friend_username}")
# #                                 break
                        
# #                         if not friend_username:
# #                             logger.warning(f"📚 [WS] ❌ Could not determine friend for room {room_id}, skipping")
# #                             continue
                    
# #                     # Verify friend_username is not the current user
# #                     if friend_username == current_username:
# #                         logger.warning(f"📚 [WS] Skipping room {room_id} - friend is current user (self-conversation)")
# #                         continue
                    
# #                     if friend_username:
# #                         if friend_username not in friend_conversations:
# #                             friend_conversations[friend_username] = []
                        
# #                         logger.info(f"📚 [WS] *** Processing {len(messages)} messages for conversation with {friend_username} ***")
                        
# #                         # FIX: Process ALL messages regardless of sender
# #                         processed_count = 0
# #                         sent_count = 0
# #                         received_count = 0
                        
# #                         # Sort messages by timestamp if available
# #                         try:
# #                             messages_sorted = sorted(messages, key=lambda x: x.get("timestamp", ""))
# #                         except:
# #                             messages_sorted = messages
                        
# #                         for msg in messages_sorted:
# #                             processed_msg = self.process_message(msg, current_username, friend_username)
# #                             if processed_msg:
# #                                 friend_conversations[friend_username].append(processed_msg)
# #                                 processed_count += 1
                                
# #                                 if processed_msg['is_sent']:
# #                                     sent_count += 1
# #                                     logger.info(f"📤 [WS] Sent message: {processed_msg['message'][:30]}... at {processed_msg['timestamp']}")
# #                                 else:
# #                                     received_count += 1
# #                                     logger.info(f"📥 [WS] Received message: {processed_msg['message'][:30]}... at {processed_msg['timestamp']}")
# #                             else:
# #                                 logger.warning(f"📚 [WS] Failed to process message: {msg}")
                        
# #                         logger.info(f"📚 [WS] *** SUMMARY for {friend_username}: {processed_count} total, {sent_count} sent, {received_count} received ***")
# #                     else:
# #                         logger.warning(f"📚 [WS] No friend username found for room {room_id}")
            
# #             # Handle list format
# #             elif isinstance(conversations_data, list):
# #                 logger.info(f"📚 [WS] Processing list format with {len(conversations_data)} conversations")
                
# #                 for conversation in conversations_data:
# #                     if isinstance(conversation, dict):
# #                         # Server sends metadata format: {room_id, other_user, last_message_time}
# #                         room_id = conversation.get("room_id")
# #                         other_user_id = conversation.get("other_user")  # This should be the friend's username
# #                         last_message_time = conversation.get("last_message_time")
                        
# #                         logger.info(f"📚 [WS] Processing conversation metadata:")
# #                         logger.info(f"📚 [WS]   room_id: {room_id}")
# #                         logger.info(f"📚 [WS]   other_user_id: {other_user_id}")
                        
# #                         # Use the actual other_user from server response
# #                         if room_id and other_user_id:
# #                             friend_username = other_user_id  # Use the actual friend username from server
                            
# #                             # Make sure it's not the current user
# #                             if friend_username == current_username:
# #                                 logger.warning(f"📚 [WS] Skipping room {room_id} - other_user is current user")
# #                                 continue
                            
# #                             logger.info(f"📚 [WS] Processing conversation with friend: {friend_username}")
                            
# #                             if friend_username not in friend_conversations:
# #                                 friend_conversations[friend_username] = []
                            
# #                             # Add placeholder message indicating conversation exists
# #                             placeholder_message = {
# #                                 "sender": friend_username,
# #                                 "message": f"Previous conversation available (click to load)",
# #                                 "timestamp": self.format_timestamp(last_message_time, is_timestamp=False),
# #                                 "is_sent": False,
# #                                 "message_type": "text",
# #                                 "room_id": room_id  # Store room_id for future message loading
# #                             }
                            
# #                             friend_conversations[friend_username].append(placeholder_message)
# #                             logger.info(f"📚 [WS] Added placeholder for {friend_username}")
# #                         else:
# #                             logger.warning(f"📚 [WS] Missing room_id or other_user in conversation: {conversation}")
                        
# #                         # Handle legacy format (full conversation data) if server provides it
# #                         friend_username_full = conversation.get("friend_username") or conversation.get("username")
# #                         messages = conversation.get("messages", [])
                        
# #                         if friend_username_full and messages:
# #                             logger.info(f"📚 [WS] Processing full conversation data for {friend_username_full}")
# #                             if friend_username_full not in friend_conversations:
# #                                 friend_conversations[friend_username_full] = []
                            
# #                             # FIX: Enhanced message processing for legacy format
# #                             processed_count = 0
# #                             sent_count = 0
# #                             received_count = 0
                            
# #                             for msg in messages:
# #                                 processed_msg = self.process_message(msg, current_username, friend_username_full)
# #                                 if processed_msg:
# #                                     friend_conversations[friend_username_full].append(processed_msg)
# #                                     processed_count += 1
                                    
# #                                     if processed_msg['is_sent']:
# #                                         sent_count += 1
# #                                     else:
# #                                         received_count += 1
                            
# #                             logger.info(f"📚 [WS] Legacy format - {friend_username_full}: {processed_count} total, {sent_count} sent, {received_count} received")
# #             else:
# #                 logger.error(f"📚 [WS] Unexpected conversations data type: {type(conversations_data)}")
# #                 return
            
# #             logger.info(f"📚 [WS] *** FINAL RESULT: Processed conversations for {len(friend_conversations)} friends ***")
# #             for friend, msgs in friend_conversations.items():
# #                 sent_msgs = sum(1 for msg in msgs if msg.get('is_sent', False))
# #                 received_msgs = len(msgs) - sent_msgs
# #                 logger.info(f"📚 [WS]   {friend}: {len(msgs)} total ({sent_msgs} sent, {received_msgs} received)")
            
# #             # Emit the signal
# #             logger.info("📤 [WS] *** EMITTING previous_conversations_received SIGNAL ***")
# #             self.previous_conversations_received.emit(friend_conversations)
# #             logger.info("✅ [WS] *** SIGNAL EMITTED SUCCESSFULLY ***")
            
# #         except Exception as e:
# #             logger.error(f"❌ [WS] Error processing conversations: {e}")
# #             import traceback
# #             traceback.print_exc()
    
# #     async def handle_conversation_history_response(self, data):
# #         """Handle response to conversation history request"""
# #         try:
# #             friend_username = data.get("friend_username")
# #             messages = data.get("messages", [])
            
# #             logger.info(f"📚 [WS] Received conversation history response for {friend_username}: {len(messages)} messages")
            
# #             if not friend_username or not messages:
# #                 logger.warning(f"📚 [WS] Invalid conversation history response: friend={friend_username}, messages={len(messages) if messages else 0}")
# #                 return
            
# #             # Process messages using the same logic as previous conversations
# #             processed_messages = []
# #             current_username = self.current_username or "indira123"
            
# #             sent_count = 0
# #             received_count = 0
            
# #             for msg in messages:
# #                 processed_msg = self.process_message(msg, current_username, friend_username)
# #                 if processed_msg:
# #                     processed_messages.append(processed_msg)
# #                     if processed_msg['is_sent']:
# #                         sent_count += 1
# #                     else:
# #                         received_count += 1
            
# #             logger.info(f"📚 [WS] Processed conversation history for {friend_username}: {len(processed_messages)} total ({sent_count} sent, {received_count} received)")
            
# #             # Emit signal to update UI
# #             self.conversation_history_received.emit(friend_username, processed_messages)
            
# #         except Exception as e:
# #             logger.error(f"❌ [WS] Error processing conversation history response: {e}")
# #             import traceback
# #             traceback.print_exc()
    
# #     async def handle_new_message(self, data):
# #         """Handle new incoming message with file support"""
# #         try:
# #             message_obj = data.get("message", {})
# #             from_username = message_obj.get("sender_username") or data.get("sender", {}).get("username")
# #             message_text = message_obj.get("content") or data.get("message", "")
# #             timestamp = message_obj.get("timestamp") or data.get("timestamp")
            
# #             # Check for file/image data
# #             message_type = message_obj.get("message_type", "text")
# #             file_data = {}
            
# #             print(f"🔍 [WS] Processing message: type={message_type}, from={from_username}")
# #             print(f"🔍 [WS] Message object keys: {list(message_obj.keys())}")
            
# #             if message_type in ['image', 'file']:
# #                 file_data = {
# #                     'file_name': message_obj.get('file_name'),
# #                     'file_data': message_obj.get('file_data'),  # Base64 encoded data
# #                     'file_size': message_obj.get('file_size'),
# #                     'mime_type': message_obj.get('mime_type')
# #                 }
                
# #                 print(f"🔍 [WS] File data extracted:")
# #                 print(f"  file_name: {file_data.get('file_name')}")
# #                 print(f"  file_size: {file_data.get('file_size')}")
# #                 print(f"  mime_type: {file_data.get('mime_type')}")
# #                 print(f"  has_file_data: {bool(file_data.get('file_data'))}")
                
# #                 # Verify file_data is not None or empty
# #                 if not file_data.get('file_data'):
# #                     print(f"⚠️ [WS] Warning: No file_data found for {message_type} message")
# #                 else:
# #                     print(f"✅ [WS] File data present, length: {len(file_data.get('file_data', ''))}")
                
# #                 # For display purposes, use file name as message text for files
# #                 if message_type == 'file':
# #                     message_text = file_data.get('file_name', 'File')
# #                 elif message_type == 'image':
# #                     message_text = file_data.get('file_name', 'Image')
            
# #             display_time = self.format_timestamp(timestamp)
            
# #             print(f"🔍 [WS] Final emit data:")
# #             print(f"  from_username: {from_username}")
# #             print(f"  message_text: {message_text}")
# #             print(f"  message_type: {message_type}")
# #             print(f"  display_time: {display_time}")
# #             print(f"  file_data_present: {bool(file_data)}")
            
# #             # Emit with enhanced parameters
# #             self.message_received.emit(from_username, message_text, display_time, message_type, file_data)
            
# #         except Exception as e:
# #             logger.error(f"❌ [WS] Error in handle_new_message: {e}")
# #             import traceback
# #             traceback.print_exc()
    
# #     async def handle_message_sent(self, data):
# #         """Handle message sent confirmation"""
# #         original_msg = data.get("original", {})
# #         recipient_id = original_msg.get("recipient_id")
# #         message_text = original_msg.get("content")
# #         timestamp = data.get("server_timestamp")
# #         delivered = data.get("status") == "delivered"
        
# #         display_time = self.format_timestamp(timestamp, is_timestamp=True)
# #         self.message_sent_confirmation.emit(str(recipient_id), message_text, display_time, delivered)
    
# #     def process_message(self, msg, current_username, friend_username=None):
# #         """Convert server message to display format with enhanced processing for both sent and received messages"""
# #         try:
# #             logger.info(f"📚 [WS] Processing message: {msg}")
            
# #             timestamp = msg.get("timestamp", "")
# #             display_time = self.format_timestamp(timestamp)
# #             sender = msg.get("sender_username", "")
# #             recipient = msg.get("recipient_id", "")
# #             content = msg.get("content", "")
# #             message_type = msg.get("message_type", "text")
            
# #             # FIX: Enhanced logic to determine if message is sent or received
# #             is_sent = False
            
# #             # Method 1: Check if sender is current user
# #             if sender == current_username:
# #                 is_sent = True
# #                 effective_friend = recipient or friend_username
# #                 logger.info(f"📤 [WS] SENT message from {sender} to {effective_friend}")
            
# #             # Method 2: Check if sender is the friend (received message)
# #             elif friend_username and sender == friend_username:
# #                 is_sent = False
# #                 effective_friend = sender
# #                 logger.info(f"📥 [WS] RECEIVED message from {sender} to {current_username}")
            
# #             # Method 3: Check recipient to infer direction
# #             elif recipient == current_username:
# #                 is_sent = False  # Message sent TO current user (received)
# #                 effective_friend = sender
# #                 logger.info(f"📥 [WS] RECEIVED message (via recipient check) from {sender}")
            
# #             # Method 4: Fallback - if sender is not current user, assume received
# #             elif sender and sender != current_username:
# #                 is_sent = False
# #                 effective_friend = sender
# #                 logger.info(f"📥 [WS] RECEIVED message (fallback) from {sender}")
            
# #             # Method 5: Last resort - if we have friend_username context
# #             elif friend_username:
# #                 # If no clear sender info, but we know the friend, assume it's from friend
# #                 is_sent = False
# #                 effective_friend = friend_username
# #                 logger.warning(f"⚠️ [WS] ASSUMED received message from {friend_username} (unclear sender)")
            
# #             else:
# #                 logger.warning(f"⚠️ [WS] Cannot determine message direction for: {msg}")
# #                 logger.warning(f"⚠️ [WS] sender={sender}, recipient={recipient}, current_user={current_username}, friend={friend_username}")
# #                 # Default to received to be safe
# #                 is_sent = False
# #                 effective_friend = sender or friend_username or "unknown"
            
# #             logger.info(f"📚 [WS] Final determination: is_sent={is_sent}, sender={sender}, content={content[:30]}..., type={message_type}")
            
# #             # Create message data
# #             result = {
# #                 "sender": sender,
# #                 "message": content,
# #                 "timestamp": display_time,
# #                 "is_sent": is_sent,
# #                 "message_type": message_type
# #             }
            
# #             # Handle file/image data from server
# #             if message_type in ['image', 'file']:
# #                 result.update({
# #                     'file_name': msg.get('file_name'),
# #                     'file_size': msg.get('file_size'),
# #                     'mime_type': msg.get('mime_type')
# #                 })
                
# #                 # FIX: For images, decode and save the file data locally
# #                 file_data_b64 = msg.get('file_data')
# #                 if file_data_b64 and message_type == 'image':
# #                     try:
# #                         # Create persistent chat images directory
# #                         chat_images_dir = os.path.join(os.path.expanduser('~'), '.messenger_chat_images')
# #                         os.makedirs(chat_images_dir, exist_ok=True)
                        
# #                         # Create unique filename based on sender and direction
# #                         file_name = msg.get('file_name', 'image.jpg')
# #                         clean_timestamp = display_time.replace(':', '').replace(' ', '_')
# #                         direction = "sent" if is_sent else "received"
# #                         from_user = current_username if is_sent else sender
# #                         unique_filename = f"{direction}_{from_user}_{clean_timestamp}_{file_name}"
# #                         local_file_path = os.path.join(chat_images_dir, unique_filename)
                        
# #                         # Decode and save if not already exists
# #                         if not os.path.exists(local_file_path):
# #                             image_data = base64.b64decode(file_data_b64)
# #                             with open(local_file_path, 'wb') as f:
# #                                 f.write(image_data)
# #                             logger.info(f"📷 [WS] Saved chat history image: {local_file_path}")
# #                         else:
# #                             logger.info(f"📷 [WS] Image already exists: {local_file_path}")
                        
# #                         # Set file path for display
# #                         result['file_path'] = local_file_path
# #                         result['message'] = file_name  # Use filename as display text
                        
# #                     except Exception as e:
# #                         logger.error(f"❌ [WS] Error saving chat history image: {e}")
# #                         result['message'] = msg.get('file_name', 'Image (failed to load)')
                
# #                 elif message_type == 'file':
# #                     # For files, just use filename as display text
# #                     result['message'] = msg.get('file_name', 'File')
            
# #             logger.info(f"📚 [WS] Final result: {result}")
# #             return result
            
# #         except Exception as e:
# #             logger.error(f"❌ [WS] Error processing message: {e}")
# #             logger.error(f"❌ [WS] Problem message was: {msg}")
# #             import traceback
# #             traceback.print_exc()
# #             return None
    
# #     def format_timestamp(self, timestamp, is_timestamp=False):
# #         """Format timestamp for display"""
# #         try:
# #             if timestamp:
# #                 if is_timestamp and isinstance(timestamp, (int, float)):
# #                     dt = datetime.datetime.fromtimestamp(timestamp)
# #                 elif isinstance(timestamp, str):
# #                     dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
# #                 else:
# #                     dt = datetime.datetime.fromtimestamp(timestamp)
# #                 return dt.strftime("%H:%M")
# #             return datetime.datetime.now().strftime("%H:%M")
# #         except:
# #             return datetime.datetime.now().strftime("%H:%M")
    
# #     def send_message(self, recipient_id, message_text):
# #         """Send message to friend"""
# #         if not recipient_id.strip() or not message_text.strip():
# #             return False
        
# #         message_data = {"recipient_id": recipient_id, "message": message_text}
        
# #         if self.websocket and self.loop:
# #             try:
# #                 future = asyncio.run_coroutine_threadsafe(
# #                     self.websocket.send(json.dumps(message_data)), self.loop
# #                 )
# #                 future.result(timeout=1.0)
# #                 logger.info("✅ Message sent successfully")
# #                 return True
# #             except Exception as e:
# #                 logger.error(f"❌ Failed to send message: {e}")
# #                 self.message_queue.append(message_data)
# #                 return False
# #         else:
# #             self.message_queue.append(message_data)
# #             return False
    
# #     def send_file_message(self, message_data):
# #         """Send file message to friend with size checking"""
# #         if not message_data.get("recipient_id") or not message_data.get("file_data"):
# #             return False
        
# #         # Check message size before sending
# #         message_json = json.dumps(message_data)
# #         message_size = len(message_json.encode('utf-8'))
# #         max_size = 8 * 1024 * 1024  # 8MB limit for safety (server has 10MB limit)
        
# #         print(f"📤 [WS] File message size: {message_size/1024/1024:.2f}MB")
        
# #         if message_size > max_size:
# #             logger.error(f"❌ File message too large: {message_size/1024/1024:.1f}MB > {max_size/1024/1024:.1f}MB")
# #             return False
        
# #         if self.websocket and self.loop:
# #             try:
# #                 future = asyncio.run_coroutine_threadsafe(
# #                     self.websocket.send(message_json), self.loop
# #                 )
# #                 future.result(timeout=15.0)  # Longer timeout for large files
# #                 logger.info("✅ File message sent successfully")
# #                 return True
# #             except asyncio.TimeoutError:
# #                 logger.error("❌ Timeout sending file message")
# #                 self.message_queue.append(message_data)
# #                 return False
# #             except websockets.exceptions.ConnectionClosedError as e:
# #                 if "message too big" in str(e):
# #                     logger.error(f"❌ File message rejected - too large: {e}")
# #                 else:
# #                     logger.error(f"❌ Connection closed while sending file: {e}")
# #                 return False
# #             except Exception as e:
# #                 logger.error(f"❌ Failed to send file message: {e}")
# #                 self.message_queue.append(message_data)
# #                 return False
# #         else:
# #             self.message_queue.append(message_data)
# #             return False
    
# #     def request_conversation_history(self, friend_username, room_id=None):
# #         """Request full conversation history for a specific friend"""
# #         if not friend_username:
# #             return False
        
# #         request_data = {
# #             "type": "request_conversation_history",
# #             "friend_username": friend_username
# #         }
        
# #         if room_id:
# #             request_data["room_id"] = room_id
        
# #         if self.websocket and self.loop:
# #             try:
# #                 future = asyncio.run_coroutine_threadsafe(
# #                     self.websocket.send(json.dumps(request_data)), self.loop
# #                 )
# #                 future.result(timeout=5.0)
# #                 logger.info(f"📤 [WS] Requested conversation history for {friend_username}")
# #                 return True
# #             except Exception as e:
# #                 logger.error(f"❌ [WS] Failed to request conversation history: {e}")
# #                 return False
# #         else:
# #             logger.warning(f"⚠️ [WS] Cannot request history - no websocket connection")
# #             return False
        

# #     def stop(self):
# #         """Stop WebSocket thread"""
# #         self.running = False
# #         if self.websocket and self.loop:
# #             try:
# #                 future = asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
# #                 future.result(timeout=1.0)
# #             except:
# #                 pass


# # class HomePage(QWidget):
# #     """Clean home page with chat interface"""
    
# #     logout_requested = pyqtSignal()
# #     friend_list_requested = pyqtSignal()
    
# #     def __init__(self):
# #         super().__init__()
# #         self.current_chat_user = None
# #         self.auth_token = None
# #         self.current_user = None
# #         self.chat_history = {}  # Store all chat history
# #         self.websocket_client = None
        
# #         # Create navigation sidebar
# #         self.sidebar = NavigationSidebar(active_page="home")
# #         self.sidebar.friend_list_clicked.connect(self.on_friend_list_clicked)

# #         # --- NEW: Initialize Download Manager ---
# #         self.download_manager = DownloadManager(self.websocket_client)
# #         self.download_manager.download_complete.connect(self.on_download_complete)
# #         self.download_manager.download_error.connect(self.on_download_error)

# #         self.init_ui()
# #         self.connect_signals()
        
# #         self.setup_ui()
    
# #     def set_auth_token(self, token):
# #         """Set authentication token and start WebSocket"""
# #         self.auth_token = token
# #         self.start_websocket_connection()
    

# #     def connect_signals(self):
# #         # ... (keep your existing signal connections)
# #         self.websocket_client.file_message_received.connect(self.display_file_message)
    
# #     def set_current_user(self, user_info):
# #         """Set current user info"""
# #         self.current_user = user_info
        
# #         # FIX: Set current username in WebSocket client if it exists
# #         if self.websocket_client and user_info:
# #             username = user_info.get('username', '')
# #             self.websocket_client.set_current_username(username)
# #             print(f"🔧 [HOME] Set WebSocket username to: {username}")
    
# #     def show_page(self):
# #         """Called when navigating to home page - show appropriate interface"""
# #         print(f"📱 [HOME] show_page called")
# #         print(f"📱 [HOME] Current chat user: {self.current_chat_user}")
# #         print(f"📱 [HOME] Chat history keys: {list(self.chat_history.keys())}")
# #         print(f"📱 [HOME] Chat history length: {len(self.chat_history)}")
        
# #         # If we have chat history but no current chat, auto-select one
# #         if self.chat_history and not self.current_chat_user:
# #             print("📱 [HOME] Have chat history but no current chat, auto-selecting...")
            
# #             # Priority: iniahmad if exists, otherwise most recent
# #             if "iniahmad" in self.chat_history:
# #                 print("📱 [HOME] Showing iniahmad chat on home page navigation")
# #                 self.start_chat_with_friend("iniahmad")
# #             else:
# #                 most_recent = self.find_most_recent_chat(self.chat_history)
# #                 if most_recent:
# #                     print(f"📱 [HOME] Showing most recent chat with {most_recent}")
# #                     self.start_chat_with_friend(most_recent)
        
# #         # If we have a current chat, make sure it's displayed
# #         elif self.current_chat_user:
# #             print(f"📱 [HOME] Showing current chat with {self.current_chat_user}")
# #             self.display_chat_messages(self.current_chat_user)
# #             self.show_chat_interface()
        
# #         # Otherwise show welcome screen (no chats available)
# #         else:
# #             print("📱 [HOME] No chats available, showing welcome screen")
# #             print(f"📱 [HOME] Debug: chat_history empty? {not bool(self.chat_history)}")
# #             print(f"📱 [HOME] Debug: current_chat_user empty? {not bool(self.current_chat_user)}")
# #             self.show_welcome_screen()
    
# #     def start_websocket_connection(self):
# #         """Start WebSocket connection for messaging"""
# #         print("🔗 [HOME] Starting WebSocket connection...")
        
# #         # Stop existing connection
# #         if self.websocket_client:
# #             print("🔗 [HOME] Stopping existing WebSocket...")
# #             self.websocket_client.stop()
# #             self.websocket_client.wait()
        
# #         # Start new connection
# #         self.websocket_client = WebSocketThread(self.auth_token)
        
# #         # FIX: Set current username immediately after creating client
# #         if self.current_user:
# #             username = self.current_user.get('username', '')
# #             self.websocket_client.set_current_username(username)
# #             print(f"🔧 [HOME] Set WebSocket username to: {username}")
        
# #         # Connect signals with debug
# #         print("🔗 [HOME] Connecting WebSocket signals...")
# #         self.websocket_client.previous_conversations_received.connect(self.handle_chat_history)
# #         self.websocket_client.conversation_history_received.connect(self.handle_conversation_history_update)
# #         self.websocket_client.message_received.connect(self.handle_incoming_message)
# #         self.websocket_client.connection_established.connect(self.on_websocket_connected)
# #         self.websocket_client.connection_lost.connect(self.on_websocket_disconnected)
# #         self.websocket_client.message_sent_confirmation.connect(self.on_message_sent_confirmation)
        
# #         print("✅ [HOME] WebSocket signals connected, starting thread...")
# #         self.websocket_client.start()
    
# #     @pyqtSlot()
# #     def on_websocket_connected(self):
# #         """Handle WebSocket connection"""
# #         print("✅ Connected to backend server")
# #         # Don't auto-show chats here - wait for chat history to load
    
# #     @pyqtSlot()
# #     def on_websocket_disconnected(self):
# #         """Handle WebSocket disconnection"""
# #         print("❌ Disconnected from backend server")
    
# #     @pyqtSlot(str, str, str, bool)
# #     def on_message_sent_confirmation(self, recipient_id, message, timestamp, delivered):
# #         """Handle message delivery confirmation"""
# #         status = "delivered" if delivered else "pending"
# #         print(f"✅ Message to {recipient_id}: {status}")
    
# #     @pyqtSlot(dict)
# #     def handle_chat_history(self, friend_conversations):
# #         """Handle chat history from server with enhanced debugging"""
# #         print(f"📚 [HOME] *** RECEIVED CHAT HISTORY SIGNAL ***")
# #         print(f"📚 [HOME] Received chat history for {len(friend_conversations)} friends")
        
# #         # Enhanced debugging for each friend's conversation
# #         for friend, messages in friend_conversations.items():
# #             sent_count = sum(1 for msg in messages if msg.get('is_sent', False))
# #             received_count = len(messages) - sent_count
# #             print(f"📚 [HOME] {friend}: {len(messages)} total ({sent_count} sent, {received_count} received)")
            
# #             # Debug first few messages
# #             for i, msg in enumerate(messages[:3]):  # Show first 3 messages
# #                 msg_type = msg.get('message_type', 'text')
# #                 is_sent = msg.get('is_sent', False)
# #                 sender = msg.get('sender', 'unknown')
# #                 content = msg.get('message', '')[:30]
# #                 direction = "SENT" if is_sent else "RECEIVED"
# #                 print(f"  {i+1}. {direction} {msg_type} from {sender}: {content}...")
        
# #         # Store chat history
# #         self.chat_history.update(friend_conversations)
# #         print(f"📚 [HOME] Updated self.chat_history, now has {len(self.chat_history)} friends")
        
# #         # Update chat list with friends who have conversations
# #         for friend_username in friend_conversations.keys():
# #             print(f"📚 [HOME] Adding {friend_username} to chat list...")
# #             self.add_friend_to_chat_list(friend_username)
        
# #         # Auto-open a chat if no chat is currently selected
# #         if not self.current_chat_user and friend_conversations:
# #             print("📚 [HOME] No current chat selected, auto-opening...")
            
# #             # Priority: open iniahmad's chat if it exists
# #             if "iniahmad" in friend_conversations:
# #                 print("📱 [HOME] Auto-opening chat with iniahmad")
# #                 self.start_chat_with_friend("iniahmad")
# #             else:
# #                 # Otherwise, open the most recent chat (last message)
# #                 most_recent_friend = self.find_most_recent_chat(friend_conversations)
# #                 if most_recent_friend:
# #                     print(f"📱 [HOME] Auto-opening most recent chat with {most_recent_friend}")
# #                     self.start_chat_with_friend(most_recent_friend)
        
# #         # If currently viewing a chat, refresh it
# #         elif self.current_chat_user and self.current_chat_user in friend_conversations:
# #             print(f"📱 [HOME] Refreshing current chat with {self.current_chat_user}")
# #             # Check if we have both sent and received messages
# #             msgs = friend_conversations[self.current_chat_user]
# #             sent_count = sum(1 for msg in msgs if msg.get('is_sent', False))
# #             received_count = len(msgs) - sent_count
# #             print(f"📱 [HOME] Current chat refresh: {len(msgs)} total, {sent_count} sent, {received_count} received")
# #             self.display_chat_messages(self.current_chat_user)
        
# #         print(f"📚 [HOME] *** CHAT HISTORY PROCESSING COMPLETE ***")
    
# #     @pyqtSlot(str, list)
# #     def handle_conversation_history_update(self, friend_username, messages):
# #         """Handle updated conversation history for a specific friend"""
# #         print(f"📚 [HOME] *** RECEIVED CONVERSATION HISTORY UPDATE for {friend_username} ***")
        
# #         sent_count = sum(1 for msg in messages if msg.get('is_sent', False))
# #         received_count = len(messages) - sent_count
# #         print(f"📚 [HOME] Updated history: {len(messages)} total ({sent_count} sent, {received_count} received)")
        
# #         # Update chat history for this friend
# #         self.chat_history[friend_username] = messages
        
# #         # If this is the currently active chat, refresh the display
# #         if self.current_chat_user == friend_username:
# #             print(f"📱 [HOME] Refreshing active chat display for {friend_username}")
# #             self.display_chat_messages(friend_username)
        
# #         # Update chat list preview
# #         if messages:
# #             last_msg = messages[-1]
# #             msg_type = last_msg.get('message_type', 'text')
            
# #             if msg_type == 'image':
# #                 preview_text = "📷 Image"
# #             elif msg_type == 'file':
# #                 preview_text = f"📎 {last_msg.get('file_name', 'File')}"
# #             else:
# #                 preview_text = last_msg.get('message', '')
            
# #             if last_msg.get('is_sent', False):
# #                 preview_text = f"You: {preview_text}"
            
# #             timestamp = last_msg.get('timestamp', '')
# #             self.update_chat_list_preview(friend_username, preview_text, timestamp)
        
# #         print(f"📚 [HOME] *** CONVERSATION HISTORY UPDATE COMPLETE for {friend_username} ***")
    
# #     @pyqtSlot(str, str, str, str, dict)
# #     def handle_incoming_message(self, from_username, message_text, timestamp, message_type='text', file_data=None):
# #         """Handle incoming message with file/image support"""
# #         print(f"📥 Message from {from_username}: {message_text} (type: {message_type})")

# #         # Get current user's username for comparison
# #         current_username = self.current_user.get('username', '') if self.current_user else 'indira123'

# #         # IMPORTANT FIX: Ignore messages from ourselves (echoes/confirmations)
# #         if from_username == current_username:
# #             print(f"📝 [HOME] Ignoring message from self: {from_username}")
# #             return

# #         # Store message in chat history
# #         if from_username not in self.chat_history:
# #             self.chat_history[from_username] = []

# #         # Create base message data
# #         message_data = {
# #             'message': message_text,
# #             'message_type': message_type,
# #             'is_sent': False,  # Always False for incoming messages
# #             'timestamp': timestamp,
# #             'sender': from_username
# #         }

# #         # Handle file/image data
# #         if file_data and message_type in ['image', 'file']:
# #             print(f"🔍 [HANDLER] Processing {message_type} from {from_username}")
# #             print(f"🔍 [HANDLER] File data: {list(file_data.keys())}")
            
# #             # Add file metadata
# #             message_data.update({
# #                 'file_name': file_data.get('file_name', 'Unknown file'),
# #                 'file_size': file_data.get('file_size', 0),
# #                 'mime_type': file_data.get('mime_type', 'application/octet-stream')
# #             })
            
# #             # For images, save to temp folder for display
# #             if message_type == 'image' and file_data.get('file_data'):
# #                 try:
# #                     print(f"🔍 [HANDLER] Decoding image data...")
# #                     # Decode base64 image data
# #                     image_data = base64.b64decode(file_data['file_data'])
                    
# #                     # Create persistent chat images directory
# #                     chat_images_dir = os.path.join(os.path.expanduser('~'), '.messenger_chat_images')
# #                     os.makedirs(chat_images_dir, exist_ok=True)
                    
# #                     # Create temp file with proper extension
# #                     file_name = file_data.get('file_name', 'image.jpg')
# #                     # Clean timestamp for filename
# #                     clean_timestamp = timestamp.replace(':', '').replace(' ', '_')
# #                     temp_file_path = os.path.join(chat_images_dir, f"received_{from_username}_{clean_timestamp}_{file_name}")
                    
# #                     print(f"🔍 [HANDLER] Saving image to: {temp_file_path}")
# #                     with open(temp_file_path, 'wb') as f:
# #                         f.write(image_data)
                    
# #                     # Verify file was created and has content
# #                     if os.path.exists(temp_file_path):
# #                         file_size = os.path.getsize(temp_file_path)
# #                         print(f"✅ [HANDLER] Image saved successfully: {file_size} bytes")
                        
# #                         # Store the temp file path for display
# #                         message_data['file_path'] = temp_file_path
# #                         # Update message text to be more user-friendly
# #                         message_data['message'] = file_data.get('file_name', 'Image')
# #                     else:
# #                         print(f"❌ [HANDLER] Failed to save image file")
# #                         message_data['message'] = file_data.get('file_name', 'Image (failed to save)')
                    
# #                 except Exception as e:
# #                     print(f"❌ [HANDLER] Error saving received image: {e}")
# #                     import traceback
# #                     traceback.print_exc()
# #                     # Fallback to showing filename
# #                     message_data['message'] = file_data.get('file_name', 'Image (failed to load)')
            
# #             elif message_type == 'file':
# #                 # For files, just use filename as display text
# #                 message_data['message'] = file_data.get('file_name', 'File')
# #                 print(f"🔍 [HANDLER] File message processed: {message_data['message']}")

# #         # Add message to chat history (only once!)
# #         self.chat_history[from_username].append(message_data)
# #         print(f"💾 [HANDLER] Message from {from_username} stored in chat history.")

# #         # Add friend to chat list
# #         self.add_friend_to_chat_list(from_username)

# #         # If the user is currently viewing this chat, add the new bubble to the display
# #         if self.current_chat_user == from_username:
# #             print(f"✅ [HANDLER] Chat with {from_username} is active. Adding bubble to display.")
# #             self.add_message_to_display_with_type(message_data)
# #         else:
# #             print(f"ℹ️ [HANDLER] Chat with {from_username} is not active. UI will not be updated instantly.")

# #         # Update chat list preview
# #         if message_type == 'image':
# #             preview_text = "📷 Image"
# #         elif message_type == 'file':
# #             preview_text = f"📎 {file_data.get('file_name', 'File') if file_data else 'File'}"
# #         else:
# #             preview_text = message_text

# #         self.update_chat_list_preview(from_username, preview_text, timestamp)
    
# #     def send_message(self):
# #         """Send message to current friend"""
# #         if not self.current_chat_user or not self.websocket_client:
# #             return
    
# #         message_text = self.message_input.text().strip()
# #         if not message_text:
# #             return
    
# #         timestamp = datetime.datetime.now().strftime("%H:%M")
    
# #         # Send via WebSocket
# #         success = self.websocket_client.send_message(self.current_chat_user, message_text)
    
# #         # Store locally and display
# #         if self.current_chat_user not in self.chat_history:
# #             self.chat_history[self.current_chat_user] = []
    
# #         message_data = {
# #             'message': message_text,
# #             'message_type': 'text',
# #             'is_sent': True,
# #             'timestamp': timestamp,
# #             'sender': self.current_user.get('username', '') if self.current_user else ''
# #         }
# #         self.chat_history[self.current_chat_user].append(message_data)
    
# #         # Ensure the recipient is in the chat list
# #         print(f"📝 [HOME] Ensuring recipient {self.current_chat_user} is in chat list...")
# #         self.add_friend_to_chat_list(self.current_chat_user)
    
# #         # Add to display
# #         self.add_message_to_display_with_type(message_data)
    
# #         # Update chat list preview
# #         self.update_chat_list_preview(self.current_chat_user, f"You: {message_text}", timestamp)
    
# #         # Clear input
# #         self.message_input.clear()
    
# #         print(f"📤 Sent message to {self.current_chat_user}: {message_text}")
    
# #     def open_file_dialog(self):
# #         """Open file selection dialog"""
# #         if not self.current_chat_user:
# #             QMessageBox.warning(self, "No Chat Selected", "Please select a friend to chat with first.")
# #             return
        
# #         dialog = FileSelectionDialog(self)
# #         if dialog.exec_() == QDialog.Accepted:
# #             if dialog.selected_file_path and dialog.file_type:
# #                 self.send_file(dialog.selected_file_path, dialog.file_type)

# #     def send_file(self, file_path, file_type):
# #         """Send file or image to current friend with size limits and compression"""
# #         if not self.current_chat_user or not self.websocket_client:
# #             return
        
# #         try:
# #             # Get file info
# #             file_name = os.path.basename(file_path)
# #             file_size = os.path.getsize(file_path)
            
# #             print(f"📎 [SEND] Preparing to send {file_type}: {file_name} ({file_size} bytes)")
# #             print(f"📎 [SEND] Original file path: {file_path}")
            
# #             # Check file size limits (stricter for WebSocket)
# #             if file_type == 'image':
# #                 max_size = 2 * 1024 * 1024  # 2MB for images
# #             else:
# #                 max_size = 1 * 1024 * 1024  # 1MB for other files
                
# #             if file_size > max_size:
# #                 QMessageBox.warning(self, "File Too Large", 
# #                                   f"File size ({file_size/1024/1024:.1f}MB) exceeds the {max_size/1024/1024:.0f}MB limit for {file_type}s.\n"
# #                                   f"Please choose a smaller file or compress it first.")
# #                 return
            
# #             # Read and process file
# #             if file_type == 'image':
# #                 # Compress image if needed
# #                 file_data, compressed_size = self.compress_image_if_needed(file_path, max_size)
# #                 if compressed_size != file_size:
# #                     print(f"📷 [SEND] Image compressed: {file_size} → {compressed_size} bytes")
# #                     file_size = compressed_size
# #             else:
# #                 # Read file normally
# #                 with open(file_path, 'rb') as f:
# #                     file_data = f.read()
            
# #             # Encode to base64
# #             file_base64 = base64.b64encode(file_data).decode('utf-8')
            
# #             # Check final encoded size (base64 adds ~33% overhead)
# #             encoded_size = len(file_base64)
# #             max_encoded_size = 3 * 1024 * 1024  # 3MB encoded limit
            
# #             if encoded_size > max_encoded_size:
# #                 QMessageBox.warning(self, "Encoded File Too Large", 
# #                                   f"After encoding, file size ({encoded_size/1024/1024:.1f}MB) exceeds the 3MB transmission limit.\n"
# #                                   f"Please choose a smaller file.")
# #                 return
            
# #             print(f"✅ [SEND] File ready for transmission: {encoded_size} bytes encoded")
            
# #             # Get MIME type
# #             mime_type, _ = mimetypes.guess_type(file_path)
# #             if not mime_type:
# #                 mime_type = 'application/octet-stream'
            
# #             timestamp = datetime.datetime.now().strftime("%H:%M")
            
# #             # Create message data for WebSocket
# #             message_data = {
# #                 "recipient_id": self.current_chat_user,
# #                 "message_type": file_type,
# #                 "file_name": file_name,
# #                 "file_data": file_base64,
# #                 "file_size": file_size,
# #                 "mime_type": mime_type
# #             }
            
# #             # Send via WebSocket
# #             success = self.websocket_client.send_file_message(message_data)
            
# #             # Store locally and display
# #             if self.current_chat_user not in self.chat_history:
# #                 self.chat_history[self.current_chat_user] = []
            
# #             # FIX: For images, copy to a permanent location for display
# #             display_path = file_path  # Default to original path
            
# #             if file_type == 'image':
# #                 try:
# #                     # Create a permanent copy in chat images folder for display
# #                     chat_images_dir = os.path.join(os.path.expanduser('~'), '.messenger_chat_images')
# #                     os.makedirs(chat_images_dir, exist_ok=True)
                    
# #                     # Use timestamp to make unique filename
# #                     clean_timestamp = timestamp.replace(':', '').replace(' ', '_')
# #                     current_username = self.current_user.get('username', 'user') if self.current_user else 'user'
# #                     temp_file_path = os.path.join(chat_images_dir, f"sent_{current_username}_{clean_timestamp}_{file_name}")
                    
# #                     # Copy file to persistent location
# #                     shutil.copy2(file_path, temp_file_path)
# #                     display_path = temp_file_path
                    
# #                     print(f"📷 [SEND] Copied image for display to: {display_path}")
                    
# #                     # Verify the copy was successful
# #                     if os.path.exists(display_path):
# #                         print(f"✅ [SEND] Display image exists: {os.path.getsize(display_path)} bytes")
# #                     else:
# #                         print(f"❌ [SEND] Display image copy failed, using original path")
# #                         display_path = file_path
                        
# #                 except Exception as e:
# #                     print(f"⚠️ [SEND] Could not copy image for display: {e}")
# #                     display_path = file_path
            
# #             local_message_data = {
# #                 'message': file_name,
# #                 'message_type': file_type,
# #                 'file_path': display_path,  # Use the display path
# #                 'file_name': file_name,
# #                 'file_size': file_size,
# #                 'mime_type': mime_type,
# #                 'is_sent': True,
# #                 'timestamp': timestamp,
# #                 'sender': self.current_user.get('username', '') if self.current_user else ''
# #             }
            
# #             print(f"📎 [SEND] Storing message data: {local_message_data}")
            
# #             self.chat_history[self.current_chat_user].append(local_message_data)
            
# #             # Ensure recipient is in chat list
# #             self.add_friend_to_chat_list(self.current_chat_user)
            
# #             # Add to display
# #             self.add_message_to_display_with_type(local_message_data)
            
# #             # Update chat list preview
# #             preview_text = f"📎 {file_name}" if file_type == 'file' else f"📷 Image"
# #             self.update_chat_list_preview(self.current_chat_user, f"You: {preview_text}", timestamp)
            
# #             print(f"📤 Sent {file_type} to {self.current_chat_user}: {file_name} ({file_size} bytes)")
            
# #         except Exception as e:
# #             print(f"❌ Error sending file: {e}")
# #             import traceback
# #             traceback.print_exc()
# #             QMessageBox.critical(self, "Send Error", f"Failed to send file: {str(e)}")

# #     def compress_image_if_needed(self, image_path, max_size):
# #         """Compress image if it exceeds size limit"""
# #         try:
# #             from PIL import Image
# #             import io
            
# #             # Open image
# #             with Image.open(image_path) as img:
# #                 # Convert to RGB if necessary
# #                 if img.mode in ('RGBA', 'P'):
# #                     img = img.convert('RGB')
                
# #                 # Get original size
# #                 original_size = os.path.getsize(image_path)
                
# #                 if original_size <= max_size:
# #                     # No compression needed
# #                     with open(image_path, 'rb') as f:
# #                         return f.read(), original_size
                
# #                 # Try different compression levels
# #                 for quality in [85, 70, 55, 40, 25]:
# #                     output = io.BytesIO()
# #                     img.save(output, format='JPEG', quality=quality, optimize=True)
# #                     compressed_data = output.getvalue()
                    
# #                     if len(compressed_data) <= max_size:
# #                         print(f"📷 [COMPRESS] Compressed to quality {quality}%")
# #                         return compressed_data, len(compressed_data)
                
# #                 # If still too large, resize the image
# #                 width, height = img.size
# #                 for scale in [0.8, 0.6, 0.4, 0.2]:
# #                     new_width = int(width * scale)
# #                     new_height = int(height * scale)
# #                     resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
# #                     output = io.BytesIO()
# #                     resized_img.save(output, format='JPEG', quality=70, optimize=True)
# #                     compressed_data = output.getvalue()
                    
# #                     if len(compressed_data) <= max_size:
# #                         print(f"📷 [COMPRESS] Resized to {scale*100}% and compressed")
# #                         return compressed_data, len(compressed_data)
                
# #                 # If all else fails, return original and let error handling deal with it
# #                 with open(image_path, 'rb') as f:
# #                     return f.read(), original_size
                    
# #         except ImportError:
# #             print("⚠️ [COMPRESS] PIL not available, cannot compress images")
# #             # Fall back to original file
# #             with open(image_path, 'rb') as f:
# #                 return f.read(), os.path.getsize(image_path)
# #         except Exception as e:
# #             print(f"❌ [COMPRESS] Error compressing image: {e}")
# #             # Fall back to original file
# #             with open(image_path, 'rb') as f:
# #                 return f.read(), os.path.getsize(image_path)

# #     def debug_message_data(self, message_data, context=""):
# #         """Debug helper to print message data structure"""
# #         print(f"🔍 DEBUG {context}:")
# #         print(f"  message: {message_data.get('message', 'N/A')}")
# #         print(f"  message_type: {message_data.get('message_type', 'N/A')}")
# #         print(f"  file_name: {message_data.get('file_name', 'N/A')}")
# #         print(f"  file_path: {message_data.get('file_path', 'N/A')}")
# #         print(f"  file_size: {message_data.get('file_size', 'N/A')}")
# #         print(f"  is_sent: {message_data.get('is_sent', 'N/A')}")
# #         print(f"  sender: {message_data.get('sender', 'N/A')}")
# #         if message_data.get('file_path'):
# #             file_exists = os.path.exists(message_data['file_path'])
# #             file_size = os.path.getsize(message_data['file_path']) if file_exists else 0
# #             print(f"  file_exists: {file_exists}")
# #             print(f"  actual_file_size: {file_size}")

# #     def add_message_to_display_with_type(self, message_data):
# #         """Add message with type info to chat display"""
# #         if not hasattr(self, 'messages_layout'):
# #             return
        
# #         # Debug the message data
# #         self.debug_message_data(message_data, "DISPLAY")
        
# #         # Remove stretch temporarily
# #         self.remove_layout_stretch(self.messages_layout)
        
# #         # Create message widget based on type
# #         message_widget = self.create_message_widget_enhanced(message_data)
# #         self.messages_layout.addWidget(message_widget)
        
# #         # Add stretch back
# #         self.messages_layout.addStretch()
        
# #         # Scroll to bottom
# #         QTimer.singleShot(50, self.scroll_to_bottom)

# #     def create_message_widget_enhanced(self, message_data):
# #         """Create enhanced message bubble widget that handles text, images, and files with click support"""
# #         container = QFrame()
# #         container.setStyleSheet("background-color: transparent; border: none;")
    
# #         layout = QHBoxLayout(container)
# #         layout.setContentsMargins(0, 0, 0, 0)
    
# #         # Get message info
# #         message_text = message_data.get('message', '')
# #         is_sent = message_data.get('is_sent', False)
# #         timestamp = message_data.get('timestamp', '')
# #         message_type = message_data.get('message_type', 'text')
    
# #         print(f"🎨 [UI] Creating widget for {message_type} message:")
# #         print(f"  text: {message_text}")
# #         print(f"  is_sent: {is_sent}")
# #         print(f"  file_path: {message_data.get('file_path', 'N/A')}")
    
# #         # Message bubble
# #         bubble = QFrame()
# #         bubble.setMaximumWidth(400)
    
# #         if is_sent:
# #             bubble.setStyleSheet("""
# #                 QFrame {
# #                     background-color: #A8B8BC;
# #                     border-radius: 15px;
# #                     padding: 10px 15px;
# #                 }
# #             """)
# #             layout.addStretch()
# #             layout.addWidget(bubble)
# #         else:
# #             bubble.setStyleSheet("""
# #                 QFrame {
# #                     background-color: #D5CECE;
# #                     border-radius: 15px;
# #                     padding: 10px 15px;
# #                 }
# #             """)
# #             layout.addWidget(bubble)
# #             layout.addStretch()
    
# #         bubble_layout = QVBoxLayout(bubble)
# #         bubble_layout.setContentsMargins(5, 5, 5, 5)
# #         bubble_layout.setSpacing(5)
    
# #         # Content based on message type
# #         if message_type == 'image':
# #             # Display image with click support
# #             image_label = QLabel()
# #             image_loaded = False
        
# #             # Try to load image from local path first
# #             image_path = message_data.get('file_path')
# #             print(f"🖼️ [UI] Attempting to load image from: {image_path}")
        
# #             if image_path and os.path.exists(image_path):
# #                 try:
# #                     print(f"🖼️ [UI] File exists, size: {os.path.getsize(image_path)} bytes")
# #                     pixmap = QPixmap(image_path)
# #                     if not pixmap.isNull():
# #                         # Scale image to fit nicely in chat
# #                         scaled_pixmap = pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
# #                         image_label.setPixmap(scaled_pixmap)
# #                         image_loaded = True
# #                         print(f"✅ [UI] Successfully loaded image from: {image_path}")
# #                     else:
# #                         print(f"❌ [UI] Failed to load image (null pixmap): {image_path}")
# #                 except Exception as e:
# #                     print(f"❌ [UI] Error loading image from {image_path}: {e}")
# #                     import traceback
# #                     traceback.print_exc()
# #             else:
# #                 if image_path:
# #                     print(f"❌ [UI] Image file does not exist: {image_path}")
# #                 else:
# #                     print(f"❌ [UI] No image path provided")
        
# #             # If image couldn't be loaded, show placeholder
# #             if not image_loaded:
# #                 placeholder_pixmap = QPixmap(200, 150)
# #                 placeholder_pixmap.fill(QColor(240, 240, 240))
            
# #                 # Draw placeholder text
# #                 painter = QPainter(placeholder_pixmap)
# #                 painter.setPen(QColor(150, 150, 150))
# #                 painter.drawText(placeholder_pixmap.rect(), Qt.AlignCenter, "📷\nImage\n(failed to load)")
# #                 painter.end()
            
# #                 image_label.setPixmap(placeholder_pixmap)
# #                 print("⚠️ [UI] Using placeholder image")
        
# #             # FIX: Add click functionality for images
# #             image_label.setStyleSheet("""
# #                 QLabel {
# #                     border: 1px solid #B0C4C6;
# #                     border-radius: 8px;
# #                     background-color: white;
# #                 }
# #                 QLabel:hover {
# #                     border: 2px solid #7A9499;
# #                     cursor: pointer;
# #                 }
# #             """)
# #             image_label.setScaledContents(False)
# #             image_label.setAlignment(Qt.AlignCenter)
            
# #             # Make image clickable
# #             image_label.mousePressEvent = lambda event: self.handle_image_click(message_data)
# #             image_label.setCursor(Qt.PointingHandCursor)
            
# #             bubble_layout.addWidget(image_label)
        
# #             # File name below image (if available and different from generic "Image")
# #             file_name = message_data.get('file_name', '')
# #             if file_name and file_name.lower() not in ['image', 'image.jpg', 'image.png']:
# #                 name_label = QLabel(file_name)
# #                 name_label.setStyleSheet("""
# #                     QLabel {
# #                         color: #2C2C2C;
# #                         font-size: 12px;
# #                         border: none;
# #                         background-color: transparent;
# #                     }
# #                 """)
# #                 name_label.setAlignment(Qt.AlignCenter)
# #                 name_label.setWordWrap(True)
# #                 bubble_layout.addWidget(name_label)
    
# #         elif message_type == 'file':
# #             # Display file icon and info with click support
# #             file_container = QFrame()
# #             file_container.setStyleSheet("""
# #                 QFrame {
# #                     background-color: rgba(255, 255, 255, 100);
# #                     border: 1px solid #B0C4C6;
# #                     border-radius: 8px;
# #                     padding: 10px;
# #                 }
# #                 QFrame:hover {
# #                     border: 2px solid #7A9499;
# #                     cursor: pointer;
# #                 }
# #             """)
            
# #             # Make file container clickable
# #             file_container.mousePressEvent = lambda event: self.handle_file_click(message_data)
# #             file_container.setCursor(Qt.PointingHandCursor)
            
# #             file_layout = QHBoxLayout(file_container)
# #             file_layout.setContentsMargins(10, 10, 10, 10)
        
# #             # File icon
# #             file_icon = QLabel("📄")
# #             file_icon.setStyleSheet("font-size: 24px;")
# #             file_layout.addWidget(file_icon)
        
# #             # File info
# #             info_layout = QVBoxLayout()
        
# #             file_name = message_data.get('file_name', message_text if message_text != 'File' else 'Unknown file')
# #             name_label = QLabel(file_name)
# #             name_label.setStyleSheet("""
# #                 QLabel {
# #                     color: #2C2C2C;
# #                     font-size: 14px;
# #                     font-weight: bold;
# #                     border: none;
# #                     background-color: transparent;
# #                 }
# #             """)
# #             name_label.setWordWrap(True)
        
# #             file_size = message_data.get('file_size', 0)
# #             if file_size > 0:
# #                 size_text = self.format_file_size(file_size)
# #                 size_label = QLabel(size_text)
# #                 size_label.setStyleSheet("""
# #                     QLabel {
# #                         color: #7F8C8D;
# #                         font-size: 12px;
# #                         border: none;
# #                         background-color: transparent;
# #                     }
# #                 """)
# #                 info_layout.addWidget(name_label)
# #                 info_layout.addWidget(size_label)
# #             else:
# #                 info_layout.addWidget(name_label)
        
# #             file_layout.addLayout(info_layout)
# #             bubble_layout.addWidget(file_container)
    
# #         else:
# #             # Regular text message
# #             message_label = QLabel(message_text)
# #             message_label.setWordWrap(True)
# #             message_label.setStyleSheet("""
# #                 QLabel {
# #                     color: #2C2C2C;
# #                     font-size: 14px;
# #                     border: none;
# #                 }
# #             """)
# #             bubble_layout.addWidget(message_label)
    
# #         # Timestamp
# #         time_label = QLabel(timestamp)
# #         time_label.setStyleSheet("""
# #             QLabel {
# #                 color: #7F8C8D;
# #                 font-size: 10px;
# #                 border: none;
# #             }
# #         """)
# #         time_label.setAlignment(Qt.AlignRight if is_sent else Qt.AlignLeft)
# #         bubble_layout.addWidget(time_label)
    
# #         return container

# #     def handle_image_click(self, message_data):
# #         """Handle clicking on an image to view or download"""
# #         file_path = message_data.get('file_path')
# #         file_name = message_data.get('file_name', 'image.jpg')
        
# #         if not file_path or not os.path.exists(file_path):
# #             QMessageBox.warning(self, "Image Not Found", "The image file could not be found.")
# #             return
        
# #         # Show options: View or Download
# #         msg_box = QMessageBox(self)
# #         msg_box.setWindowTitle("Image Options")
# #         msg_box.setText(f"What would you like to do with '{file_name}'?")
        
# #         view_btn = msg_box.addButton("View", QMessageBox.ActionRole)
# #         download_btn = msg_box.addButton("Download", QMessageBox.ActionRole)
# #         cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        
# #         msg_box.exec_()
        
# #         if msg_box.clickedButton() == view_btn:
# #             # Open image with default system viewer
# #             try:
# #                 import subprocess
# #                 import platform
                
# #                 if platform.system() == 'Windows':
# #                     os.startfile(file_path)
# #                 elif platform.system() == 'Darwin':  # macOS
# #                     subprocess.call(['open', file_path])
# #                 else:  # Linux
# #                     subprocess.call(['xdg-open', file_path])
                    
# #             except Exception as e:
# #                 QMessageBox.critical(self, "Error", f"Could not open image: {str(e)}")
                
# #         elif msg_box.clickedButton() == download_btn:
# #             self.download_file(file_path, file_name)

# #     def handle_file_click(self, message_data):
# #         """Handle clicking on a file to download"""
# #         file_name = message_data.get('file_name', 'file')
        
# #         # For files, we typically don't have the actual file data locally
# #         # We would need to request it from the server or download it
# #         QMessageBox.information(self, "File Download", 
# #                                f"File download functionality for '{file_name}' would be implemented here.\n"
# #                                f"This would typically request the file from the server.")

# #     def download_file(self, source_path, suggested_name):
# #         """Download/copy file to user-selected location"""
# #         try:
# #             # Let user choose where to save
# #             save_path, _ = QFileDialog.getSaveFileName(
# #                 self,
# #                 "Save File",
# #                 suggested_name,
# #                 "All Files (*.*)"
# #             )
            
# #             if save_path:
# #                 # Copy file to chosen location
# #                 shutil.copy2(source_path, save_path)
# #                 QMessageBox.information(self, "Download Complete", 
# #                                       f"File saved to:\n{save_path}")
                
# #         except Exception as e:
# #             QMessageBox.critical(self, "Download Error", f"Failed to download file: {str(e)}")

# #     def format_file_size(self, size_bytes):
# #         """Format file size in human readable format"""
# #         if size_bytes == 0:
# #             return "0 B"
        
# #         size_names = ["B", "KB", "MB", "GB"]
# #         i = 0
# #         size = float(size_bytes)
        
# #         while size >= 1024 and i < len(size_names) - 1:
# #             size /= 1024
# #             i += 1
        
# #         return f"{size:.1f} {size_names[i]}"
    
# #     def find_most_recent_chat(self, friend_conversations):
# #         """Find the friend with the most recent message"""
# #         try:
# #             most_recent_friend = None
# #             latest_timestamp = None
            
# #             for friend_username, messages in friend_conversations.items():
# #                 if not messages:
# #                     continue
                
# #                 # Get the last message timestamp
# #                 last_message = messages[-1]
# #                 timestamp_str = last_message.get('timestamp', '')
                
# #                 try:
# #                     # Convert timestamp to comparable format
# #                     if timestamp_str:
# #                         # Assuming timestamp is in "HH:MM" format, use today's date
# #                         today = datetime.datetime.now().date()
# #                         time_obj = datetime.datetime.strptime(timestamp_str, "%H:%M").time()
# #                         full_timestamp = datetime.datetime.combine(today, time_obj)
                        
# #                         if latest_timestamp is None or full_timestamp > latest_timestamp:
# #                             latest_timestamp = full_timestamp
# #                             most_recent_friend = friend_username
# #                 except:
# #                     # If timestamp parsing fails, just use the first friend as fallback
# #                     if most_recent_friend is None:
# #                         most_recent_friend = friend_username
            
# #             return most_recent_friend
# #         except Exception as e:
# #             print(f"❌ Error finding most recent chat: {e}")
# #             # Return first friend as fallback
# #             return list(friend_conversations.keys())[0] if friend_conversations else None
    
# #     def add_friend_to_chat_list(self, friend_username):
# #         """Add friend to chat list if not already there"""
# #         print(f"📝 [HOME] add_friend_to_chat_list called for: {friend_username}")
        
# #         # Check if already exists
# #         for i in range(self.chat_layout.count()):
# #             item = self.chat_layout.itemAt(i)
# #             if item and item.widget() and hasattr(item.widget(), 'objectName'):
# #                 if item.widget().objectName() == f"chat_{friend_username}":
# #                     print(f"📝 [HOME] {friend_username} already in chat list")
# #                     return  # Already exists
        
# #         print(f"📝 [HOME] Adding {friend_username} to chat list...")
        
# #         # Remove any stretch items
# #         self.clear_layout_stretches(self.chat_layout)
        
# #         # Create chat item
# #         chat_item = self.create_chat_item(friend_username)
# #         chat_item.setObjectName(f"chat_{friend_username}")
        
# #         # Add click handler
# #         def on_chat_clicked():
# #             print(f"📝 [HOME] Chat item clicked: {friend_username}")
# #             self.start_chat_with_friend(friend_username)
        
# #         chat_item.mousePressEvent = lambda event: on_chat_clicked()
        
# #         # Add to layout
# #         self.chat_layout.insertWidget(0, chat_item)
# #         self.chat_layout.addStretch()
        
# #         print(f"✅ [HOME] Added {friend_username} to chat list")
    
# #     def start_chat_with_friend(self, friend_username):
# #         """Start or continue chat with friend"""
# #         print(f"💬 [HOME] Starting chat with {friend_username}")
        
# #         self.current_chat_user = friend_username
        
# #         # Show chat interface
# #         self.show_chat_interface()
        
# #         # Update chat header
# #         if hasattr(self, 'friend_name_label'):
# #             self.friend_name_label.setText(friend_username)
        
# #         # Check if we have actual conversation data or just metadata
# #         if friend_username in self.chat_history:
# #             messages = self.chat_history[friend_username]
# #             has_placeholder = any(msg.get('message', '').startswith('Previous conversation') for msg in messages)
            
# #             # FIX: Check if we have a balanced conversation (both sent and received messages)
# #             sent_count = sum(1 for msg in messages if msg.get('is_sent', False))
# #             received_count = len(messages) - sent_count
            
# #             print(f"💬 [HOME] Chat analysis for {friend_username}:")
# #             print(f"  Total messages: {len(messages)}")
# #             print(f"  Sent messages: {sent_count}")
# #             print(f"  Received messages: {received_count}")
# #             print(f"  Has placeholder: {has_placeholder}")
            
# #             # If we only have sent messages or only received messages, request full history
# #             if (sent_count > 0 and received_count == 0) or (sent_count == 0 and received_count > 0):
# #                 print(f"⚠️ [HOME] Unbalanced conversation detected! Requesting full history...")
# #                 self.request_full_conversation_history(friend_username)
            
# #             if has_placeholder:
# #                 print(f"💬 [HOME] Only have conversation metadata for {friend_username}, requesting full history...")
# #                 # Extract room_id from placeholder if available
# #                 room_id = None
# #                 for msg in messages:
# #                     if 'room_id' in msg:
# #                         room_id = msg['room_id']
# #                         break
                
# #                 self.request_full_conversation_history(friend_username, room_id)
                
# #                 # Show placeholder and allow new messages
# #                 self.display_chat_messages(friend_username)
                
# #                 # Add a system message explaining the situation
# #                 if hasattr(self, 'messages_layout'):
# #                     self.remove_layout_stretch(self.messages_layout)
# #                     system_msg = self.create_system_message("Loading conversation history...")
# #                     self.messages_layout.addWidget(system_msg)
# #                     self.messages_layout.addStretch()
# #             else:
# #                 # Display chat history
# #                 print(f"💬 [HOME] Displaying {len(messages)} messages for {friend_username}")
# #                 self.display_chat_messages(friend_username)
# #         else:
# #             # No history, start fresh but also request any available history
# #             print(f"💬 [HOME] No local history for {friend_username}, requesting from server...")
# #             self.request_full_conversation_history(friend_username)
# #             self.display_chat_messages(friend_username)
        
# #         # Enable message input
# #         self.message_input.setPlaceholderText(f"Message {friend_username}...")
# #         self.message_input.setEnabled(True)
# #         self.message_input.setFocus()
        
# #         print(f"✅ [HOME] Chat interface ready for {friend_username}")
    
# #     def request_full_conversation_history(self, friend_username, room_id=None):
# #         """Request full conversation history from server"""
# #         if self.websocket_client:
# #             print(f"📤 [HOME] Requesting full conversation history for {friend_username}")
# #             success = self.websocket_client.request_conversation_history(friend_username, room_id)
# #             if success:
# #                 print(f"✅ [HOME] History request sent for {friend_username}")
# #             else:
# #                 print(f"❌ [HOME] Failed to request history for {friend_username}")
# #         else:
# #             print(f"❌ [HOME] No websocket client available to request history")
    
# #     def create_system_message(self, text):
# #         """Create a system message widget"""
# #         container = QFrame()
# #         container.setStyleSheet("background-color: transparent; border: none;")
        
# #         layout = QHBoxLayout(container)
# #         layout.setContentsMargins(0, 5, 0, 5)
        
# #         # System message (centered, italic)
# #         message_label = QLabel(text)
# #         message_label.setWordWrap(True)
# #         message_label.setAlignment(Qt.AlignCenter)
# #         message_label.setStyleSheet("""
# #             QLabel {
# #                 color: #7F8C8D;
# #                 font-size: 12px;
# #                 font-style: italic;
# #                 border: none;
# #                 padding: 10px;
# #             }
# #         """)
        
# #         layout.addWidget(message_label)
# #         return container
    
# #     def display_chat_messages(self, friend_username):
# #         """Display chat messages for friend with enhanced debugging"""
# #         if not hasattr(self, 'messages_layout'):
# #             return
        
# #         # Clear existing messages
# #         self.clear_layout(self.messages_layout)
        
# #         # Add messages if history exists
# #         if friend_username in self.chat_history:
# #             messages = self.chat_history[friend_username]
# #             sent_count = sum(1 for msg in messages if msg.get('is_sent', False))
# #             received_count = len(messages) - sent_count
            
# #             print(f"📺 [DISPLAY] Showing {len(messages)} messages for {friend_username}")
# #             print(f"📺 [DISPLAY]   {sent_count} sent messages, {received_count} received messages")
            
# #             for i, msg in enumerate(messages):
# #                 msg_type = msg.get('message_type', 'text')
# #                 is_sent = msg.get('is_sent', False)
# #                 sender = msg.get('sender', 'unknown')
# #                 content = msg.get('message', '')[:30]
# #                 direction = "SENT" if is_sent else "RECV"
                
# #                 print(f"📺 [DISPLAY]   {i+1}. {direction} {msg_type} from {sender}: {content}...")
                
# #                 # Check if it's an enhanced message with type info
# #                 if 'message_type' in msg:
# #                     self.add_message_to_display_with_type(msg)
# #                 else:
# #                     # Legacy text message
# #                     message_text = msg.get('message', '')
# #                     timestamp = msg.get('timestamp', '')
# #                     self.add_message_to_display(message_text, is_sent, timestamp)
# #         else:
# #             print(f"📺 [DISPLAY] No chat history found for {friend_username}")
        
# #         # Add stretch to keep messages at top
# #         self.messages_layout.addStretch()
        
# #         # Scroll to bottom
# #         QTimer.singleShot(100, self.scroll_to_bottom)
    
# #     def add_message_to_display(self, message_text, is_sent, timestamp):
# #         """Add message to chat display"""
# #         if not hasattr(self, 'messages_layout'):
# #             return
        
# #         # Remove stretch temporarily
# #         self.remove_layout_stretch(self.messages_layout)
        
# #         # Create message widget
# #         message_widget = self.create_message_widget(message_text, is_sent, timestamp)
# #         self.messages_layout.addWidget(message_widget)
        
# #         # Add stretch back
# #         self.messages_layout.addStretch()
        
# #         # Scroll to bottom
# #         QTimer.singleShot(50, self.scroll_to_bottom)
    
# #     def update_chat_list_preview(self, friend_username, message_preview, timestamp):
# #         """Update chat list item with latest message"""
# #         for i in range(self.chat_layout.count()):
# #             item = self.chat_layout.itemAt(i)
# #             if item and item.widget() and hasattr(item.widget(), 'objectName'):
# #                 if item.widget().objectName() == f"chat_{friend_username}":
# #                     # Update the preview (implementation depends on your chat item structure)
# #                     # This is a simplified version - adapt to your chat item layout
# #                     widget = item.widget()
# #                     try:
# #                         layout = widget.layout()
# #                         if layout and layout.count() >= 2:
# #                             # Find and update message label
# #                             for j in range(layout.count()):
# #                                 child_item = layout.itemAt(j)
# #                                 if child_item and isinstance(child_item.widget(), QLabel):
# #                                     label = child_item.widget()
# #                                     if ":" in label.text() or "message" in label.text().lower():
# #                                         preview = message_preview[:50] + "..." if len(message_preview) > 50 else message_preview
# #                                         label.setText(preview)
# #                                         break
# #                     except Exception as e:
# #                         print(f"❌ Error updating chat preview: {e}")
# #                     break
    
# #     # UI Setup Methods
# #     def setup_ui(self):
# #         """Setup main UI layout"""
# #         main_layout = QHBoxLayout(self)
# #         main_layout.setContentsMargins(0, 0, 0, 0)
# #         main_layout.setSpacing(0)
        
# #         # Add sidebar
# #         main_layout.addWidget(self.sidebar)
        
# #         # Add chat list
# #         self.setup_chat_list_sidebar(main_layout)
        
# #         # Add main content
# #         self.setup_main_content_area(main_layout)
    
# #     def setup_chat_list_sidebar(self, parent_layout):
# #         """Setup chat list sidebar"""
# #         chat_sidebar = QFrame()
# #         chat_sidebar.setFixedWidth(350)
# #         chat_sidebar.setStyleSheet("""
# #             QFrame {
# #                 background-color: #E8E1E1;
# #             }
# #         """)
        
# #         layout = QVBoxLayout(chat_sidebar)
# #         layout.setContentsMargins(0, 0, 0, 0)
# #         layout.setSpacing(0)
        
# #         # Header
# #         header = self.create_chat_header()
# #         layout.addWidget(header)
        
# #         # Search
# #         search = self.create_search_area()
# #         layout.addWidget(search)
        
# #         # Chat list
# #         self.setup_chat_scroll_area(layout)
        
# #         parent_layout.addWidget(chat_sidebar)
    
# #     def create_chat_header(self):
# #         """Create chat list header"""
# #         header = QFrame()
# #         header.setFixedHeight(66)
# #         header.setStyleSheet("""
# #             QFrame {
# #                 background-color: #9DB4B8;
# #             }
# #         """)
        
# #         layout = QVBoxLayout(header)
# #         layout.setContentsMargins(20, 0, 20, 0)
# #         layout.setAlignment(Qt.AlignCenter)
        
# #         title = QLabel("Start a new chat")
# #         title.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 16px;
# #                 font-weight: bold;
# #             }
# #         """)
# #         title.setAlignment(Qt.AlignCenter)
        
# #         layout.addWidget(title)
# #         return header
    
# #     def create_search_area(self):
# #         """Create search area"""
# #         search_container = QFrame()
# #         search_container.setFixedHeight(66)
# #         search_container.setStyleSheet("""
# #             QFrame {
# #                 background-color: #E8E1E1;
# #             }
# #         """)
        
# #         layout = QHBoxLayout(search_container)
# #         layout.setContentsMargins(15, 13, 15, 13)
        
# #         # Search input
# #         search_frame = QFrame()
# #         search_frame.setStyleSheet("""
# #             QFrame {
# #                 background-color: white;
# #                 border: 1px solid #B0C4C6;
# #                 border-radius: 8px;
# #             }
# #         """)
        
# #         search_layout = QHBoxLayout(search_frame)
# #         search_layout.setContentsMargins(10, 0, 10, 0)
# #         search_layout.setSpacing(8)
        
# #         search_icon = QLabel("🔍")
# #         search_icon.setStyleSheet("color: #7F8C8D; font-size: 14px;")
        
# #         self.chat_search_input = QLineEdit()
# #         self.chat_search_input.setPlaceholderText("Search for messages ...")
# #         self.chat_search_input.setStyleSheet("""
# #             QLineEdit {
# #                 border: none;
# #                 font-size: 14px;
# #                 color: #2C2C2C;
# #             }
# #         """)
        
# #         search_layout.addWidget(search_icon)
# #         search_layout.addWidget(self.chat_search_input)
        
# #         layout.addWidget(search_frame)
# #         return search_container
    
# #     def setup_chat_scroll_area(self, parent_layout):
# #         """Setup scrollable chat list"""
# #         self.chat_scroll_area = QScrollArea()
# #         self.chat_scroll_area.setWidgetResizable(True)
# #         self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
# #         self.chat_scroll_area.setStyleSheet("""
# #             QScrollArea {
# #                 background-color: #E8E1E1;
# #                 border: none;
# #             }
# #         """)
        
# #         self.chat_container = QWidget()
# #         self.chat_container.setStyleSheet("background-color: #E8E1E1;")
        
# #         self.chat_layout = QVBoxLayout(self.chat_container)
# #         self.chat_layout.setContentsMargins(0, 0, 0, 0)
# #         self.chat_layout.setSpacing(0)
# #         self.chat_layout.setAlignment(Qt.AlignTop)
# #         self.chat_layout.addStretch()
        
# #         self.chat_scroll_area.setWidget(self.chat_container)
# #         parent_layout.addWidget(self.chat_scroll_area)
    
# #     def setup_main_content_area(self, parent_layout):
# #         """Setup main content area"""
# #         self.main_content = QFrame()
# #         self.main_content.setStyleSheet("background-color: #9DB4B8;")
        
# #         self.content_layout = QVBoxLayout(self.main_content)
# #         self.content_layout.setContentsMargins(0, 0, 0, 0)
# #         self.content_layout.setSpacing(0)
        
# #         # Welcome area (shown initially)
# #         self.setup_welcome_area()
        
# #         # Message input (hidden initially)
# #         self.setup_message_input_area()
        
# #         parent_layout.addWidget(self.main_content)
    
# #     def setup_welcome_area(self):
# #         """Setup welcome message area"""
# #         self.welcome_area = QFrame()
# #         self.welcome_area.setStyleSheet("background-color: #9DB4B8;")
        
# #         layout = QVBoxLayout(self.welcome_area)
# #         layout.setAlignment(Qt.AlignCenter)
# #         layout.setSpacing(30)
# #         layout.setContentsMargins(50, 50, 50, 50)
        
# #         # Title
# #         title = QLabel("Welcome to Messenger!")
# #         title.setAlignment(Qt.AlignCenter)
# #         title.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 36px;
# #                 font-weight: bold;
# #             }
# #         """)
        
# #         # Subtitle
# #         subtitle = QLabel("Start by adding friends to begin chatting")
# #         subtitle.setAlignment(Qt.AlignCenter)
# #         subtitle.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 20px;
# #             }
# #         """)
        
# #         # Button
# #         friend_list_btn = QPushButton("Go to Friend List")
# #         friend_list_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: #7A9499;
# #                 color: white;
# #                 border: none;
# #                 border-radius: 15px;
# #                 padding: 20px 40px;
# #                 font-size: 18px;
# #                 font-weight: bold;
# #                 min-width: 200px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #6A8489;
# #             }
# #         """)
# #         friend_list_btn.clicked.connect(self.on_friend_list_clicked)
        
# #         layout.addWidget(title)
# #         layout.addWidget(subtitle)
# #         layout.addWidget(friend_list_btn, 0, Qt.AlignCenter)
        
# #         self.content_layout.addWidget(self.welcome_area)
    
# #     def setup_message_input_area(self):
# #         """Setup message input area with file attachment support"""
# #         self.input_container = QFrame()
# #         self.input_container.setFixedHeight(80)
# #         self.input_container.setStyleSheet("""
# #             QFrame {
# #                 background-color: #E8E1E1;
# #                 border-top: 2px solid #B0C4C6;
# #             }
# #         """)
        
# #         layout = QHBoxLayout(self.input_container)
# #         layout.setContentsMargins(20, 15, 20, 15)
# #         layout.setSpacing(15)
        
# #         # Attachment button - ENHANCED
# #         self.attach_btn = QPushButton("📎")
# #         self.attach_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: white;
# #                 border: 1px solid #B0C4C6;
# #                 border-radius: 8px;
# #                 font-size: 18px;
# #                 padding: 8px;
# #                 max-width: 40px;
# #                 max-height: 40px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #F0F0F0;
# #             }
# #         """)
# #         self.attach_btn.clicked.connect(self.open_file_dialog)  # Connect to file dialog
        
# #         # Message input
# #         self.message_input = QLineEdit()
# #         self.message_input.setPlaceholderText("Select a friend to start chatting...")
# #         self.message_input.setStyleSheet("""
# #             QLineEdit {
# #                 background-color: white;
# #                 border: 1px solid #B0C4C6;
# #                 border-radius: 8px;
# #                 padding: 12px 15px;
# #                 font-size: 16px;
# #                 color: #2C2C2C;
# #             }
# #             QLineEdit:focus {
# #                 border: 2px solid #7A9499;
# #             }
# #         """)
# #         self.message_input.setFixedHeight(50)
# #         self.message_input.setEnabled(False)
# #         self.message_input.returnPressed.connect(self.send_message)
        
# #         # Send button
# #         send_btn = QPushButton("Send")
# #         send_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: #9DB4B8;
# #                 color: white;
# #                 border: none;
# #                 border-radius: 8px;
# #                 padding: 12px 25px;
# #                 font-size: 16px;
# #                 font-weight: bold;
# #                 min-width: 80px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #8BA5A9;
# #             }
# #         """)
# #         send_btn.setFixedHeight(50)
# #         send_btn.clicked.connect(self.send_message)
        
# #         layout.addWidget(self.attach_btn)
# #         layout.addWidget(self.message_input)
# #         layout.addWidget(send_btn)
        
# #         self.input_container.hide()
# #         self.content_layout.addWidget(self.input_container)
    
# #     def show_chat_interface(self):
# #         """Show chat interface instead of welcome"""
# #         # Create or show chat area
# #         if not hasattr(self, 'chat_area'):
# #             self.create_chat_area()
        
# #         # Hide welcome, show chat and input
# #         self.welcome_area.hide()
# #         self.chat_area.show()
# #         self.input_container.show()
    
# #     def show_welcome_screen(self):
# #         """Show welcome screen (hide chat interface)"""
# #         if hasattr(self, 'chat_area'):
# #             self.chat_area.hide()
# #         self.input_container.hide()
# #         self.welcome_area.show()
# #         self.current_chat_user = None
    
# #     def create_chat_area(self):
# #         """Create chat messages area"""
# #         self.chat_area = QFrame()
# #         self.chat_area.setStyleSheet("background-color: #B8C4C8;")
        
# #         layout = QVBoxLayout(self.chat_area)
# #         layout.setContentsMargins(0, 0, 0, 0)
# #         layout.setSpacing(0)
        
# #         # Chat header
# #         chat_header = QFrame()
# #         chat_header.setFixedHeight(60)
# #         chat_header.setStyleSheet("""
# #             QFrame {
# #                 background-color: #B8C4C8;
# #                 border-bottom: 1px solid #A0A8AC;
# #             }
# #         """)
        
# #         header_layout = QHBoxLayout(chat_header)
# #         header_layout.setContentsMargins(30, 15, 30, 15)
        
# #         self.friend_name_label = QLabel("Friend")
# #         self.friend_name_label.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 18px;
# #                 font-weight: bold;
# #             }
# #         """)
        
# #         header_layout.addWidget(self.friend_name_label)
        
# #         # Messages scroll area
# #         self.messages_scroll = QScrollArea()
# #         self.messages_scroll.setWidgetResizable(True)
# #         self.messages_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
# #         self.messages_scroll.setStyleSheet("""
# #             QScrollArea {
# #                 background-color: #B8C4C8;
# #                 border: none;
# #             }
# #         """)
        
# #         self.messages_container = QWidget()
# #         self.messages_container.setStyleSheet("background-color: #B8C4C8;")
        
# #         self.messages_layout = QVBoxLayout(self.messages_container)
# #         self.messages_layout.setContentsMargins(20, 20, 20, 20)
# #         self.messages_layout.setSpacing(10)
# #         self.messages_layout.setAlignment(Qt.AlignTop)
# #         self.messages_layout.addStretch()
        
# #         self.messages_scroll.setWidget(self.messages_container)
        
# #         layout.addWidget(chat_header)
# #         layout.addWidget(self.messages_scroll)
        
# #         # Insert before input container
# #         self.content_layout.insertWidget(0, self.chat_area)
# #         self.chat_area.hide()  # Hidden initially
    
# #     def create_chat_item(self, friend_username):
# #         """Create chat list item"""
# #         chat_item = QFrame()
# #         chat_item.setFixedHeight(80)
# #         chat_item.setStyleSheet("""
# #             QFrame {
# #                 background-color: #E8E1E1;
# #                 border-bottom: 1px solid #D0C9C9;
# #             }
# #             QFrame:hover {
# #                 background-color: #D5CECE;
# #             }
# #         """)
# #         chat_item.setCursor(Qt.PointingHandCursor)
        
# #         layout = QVBoxLayout(chat_item)
# #         layout.setContentsMargins(15, 10, 15, 10)
# #         layout.setSpacing(5)
        
# #         # Top row: name and time
# #         top_row = QHBoxLayout()
        
# #         name_label = QLabel(friend_username)
# #         name_label.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 16px;
# #                 font-weight: bold;
# #             }
# #         """)
        
# #         time_label = QLabel("Now")
# #         time_label.setStyleSheet("""
# #             QLabel {
# #                 color: #7F8C8D;
# #                 font-size: 12px;
# #             }
# #         """)
# #         time_label.setAlignment(Qt.AlignRight)
        
# #         top_row.addWidget(name_label)
# #         top_row.addStretch()
# #         top_row.addWidget(time_label)
        
# #         # Bottom row: last message
# #         message_preview = "No messages yet"
# #         if friend_username in self.chat_history and self.chat_history[friend_username]:
# #             last_msg = self.chat_history[friend_username][-1]
# #             msg_type = last_msg.get('message_type', 'text')
            
# #             if msg_type == 'image':
# #                 preview_text = "📷 Image"
# #             elif msg_type == 'file':
# #                 preview_text = f"📎 {last_msg.get('file_name', 'File')}"
# #             else:
# #                 preview_text = last_msg.get('message', '')
            
# #             if last_msg.get('is_sent', False):
# #                 message_preview = f"You: {preview_text[:30]}..."
# #             else:
# #                 message_preview = preview_text[:40] + "..." if len(preview_text) > 40 else preview_text
        
# #         message_label = QLabel(message_preview)
# #         message_label.setStyleSheet("""
# #             QLabel {
# #                 color: #7F8C8D;
# #                 font-size: 14px;
# #             }
# #         """)
        
# #         layout.addLayout(top_row)
# #         layout.addWidget(message_label)
        
# #         return chat_item
    
# #     def create_message_widget(self, message_text, is_sent, timestamp):
# #         """Create message bubble widget"""
# #         container = QFrame()
# #         container.setStyleSheet("background-color: transparent; border: none;")
        
# #         layout = QHBoxLayout(container)
# #         layout.setContentsMargins(0, 0, 0, 0)
        
# #         # Message bubble
# #         bubble = QFrame()
# #         bubble.setMaximumWidth(400)
        
# #         if is_sent:
# #             bubble.setStyleSheet("""
# #                 QFrame {
# #                     background-color: #A8B8BC;
# #                     border-radius: 15px;
# #                     padding: 10px 15px;
# #                 }
# #             """)
# #             layout.addStretch()
# #             layout.addWidget(bubble)
# #         else:
# #             bubble.setStyleSheet("""
# #                 QFrame {
# #                     background-color: #D5CECE;
# #                     border-radius: 15px;
# #                     padding: 10px 15px;
# #                 }
# #             """)
# #             layout.addWidget(bubble)
# #             layout.addStretch()
        
# #         bubble_layout = QVBoxLayout(bubble)
# #         bubble_layout.setContentsMargins(5, 5, 5, 5)
# #         bubble_layout.setSpacing(2)
        
# #         # Message text
# #         message_label = QLabel(message_text)
# #         message_label.setWordWrap(True)
# #         message_label.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 14px;
# #                 border: none;
# #             }
# #         """)
        
# #         # Timestamp
# #         time_label = QLabel(timestamp)
# #         time_label.setStyleSheet("""
# #             QLabel {
# #                 color: #7F8C8D;
# #                 font-size: 10px;
# #                 border: none;
# #             }
# #         """)
# #         time_label.setAlignment(Qt.AlignRight if is_sent else Qt.AlignLeft)
        
# #         bubble_layout.addWidget(message_label)
# #         bubble_layout.addWidget(time_label)
        
# #         return container
    
# #     # Utility Methods
# #     def clear_layout(self, layout):
# #         """Clear all widgets from layout"""
# #         while layout.count():
# #             child = layout.takeAt(0)
# #             if child.widget():
# #                 child.widget().deleteLater()
    
# #     def clear_layout_stretches(self, layout):
# #         """Remove stretch items from layout"""
# #         for i in range(layout.count() - 1, -1, -1):
# #             item = layout.itemAt(i)
# #             if item and item.spacerItem():
# #                 layout.removeItem(item)
    
# #     def remove_layout_stretch(self, layout):
# #         """Remove the last stretch item"""
# #         for i in range(layout.count() - 1, -1, -1):
# #             item = layout.itemAt(i)
# #             if item and item.spacerItem():
# #                 layout.removeItem(item)
# #                 break
    
# #     def scroll_to_bottom(self):
# #         """Scroll messages to bottom"""
# #         if hasattr(self, 'messages_scroll'):
# #             scrollbar = self.messages_scroll.verticalScrollBar()
# #             scrollbar.setValue(scrollbar.maximum())
    
# #     @pyqtSlot()
# #     def on_friend_list_clicked(self):
# #         """Handle friend list navigation"""
# #         print("👥 Friend list navigation requested")
# #         self.friend_list_requested.emit()
    
# #     def add_chat_to_list(self, friend_username):
# #         """Public method to add chat (called from main app)"""
# #         self.add_friend_to_chat_list(friend_username)
        
# #         # If this is the first chat and no chat is currently selected, auto-open it
# #         if not self.current_chat_user:
# #             print(f"📱 Auto-opening first chat with {friend_username}")
# #             self.start_chat_with_friend(friend_username)
    
# #     def closeEvent(self, event):
# #         """Clean up on close"""
# #         if self.websocket_client:
# #             self.websocket_client.stop()
# #             self.websocket_client.wait()
# #         event.accept()
    
# #     async def handle_message_sent(self, data):
# #         """Handle message sent confirmation"""
# #         original_msg = data.get("original", {})
# #         recipient_id = original_msg.get("recipient_id")
# #         message_text = original_msg.get("content")
# #         timestamp = data.get("server_timestamp")
# #         delivered = data.get("status") == "delivered"
        
# #         display_time = self.format_timestamp(timestamp, is_timestamp=True)
# #         self.message_sent_confirmation.emit(str(recipient_id), message_text, display_time, delivered)
    
# #     def process_message(self, msg, current_username, friend_username=None):
# #         """Convert server message to display format with enhanced processing for both sent and received messages"""
# #         try:
# #             logger.info(f"📚 [WS] Processing message: {msg}")
            
# #             timestamp = msg.get("timestamp", "")
# #             display_time = self.format_timestamp(timestamp)
# #             sender = msg.get("sender_username", "")
# #             recipient = msg.get("recipient_id", "")
# #             content = msg.get("content", "")
# #             message_type = msg.get("message_type", "text")
            
# #             # FIX: Enhanced logic to determine if message is sent or received
# #             is_sent = False
            
# #             # Method 1: Check if sender is current user
# #             if sender == current_username:
# #                 is_sent = True
# #                 effective_friend = recipient or friend_username
# #                 logger.info(f"📤 [WS] SENT message from {sender} to {effective_friend}")
            
# #             # Method 2: Check if sender is the friend (received message)
# #             elif friend_username and sender == friend_username:
# #                 is_sent = False
# #                 effective_friend = sender
# #                 logger.info(f"📥 [WS] RECEIVED message from {sender} to {current_username}")
            
# #             # Method 3: Check recipient to infer direction
# #             elif recipient == current_username:
# #                 is_sent = False  # Message sent TO current user (received)
# #                 effective_friend = sender
# #                 logger.info(f"📥 [WS] RECEIVED message (via recipient check) from {sender}")
            
# #             # Method 4: Fallback - if sender is not current user, assume received
# #             elif sender and sender != current_username:
# #                 is_sent = False
# #                 effective_friend = sender
# #                 logger.info(f"📥 [WS] RECEIVED message (fallback) from {sender}")
            
# #             # Method 5: Last resort - if we have friend_username context
# #             elif friend_username:
# #                 # If no clear sender info, but we know the friend, assume it's from friend
# #                 is_sent = False
# #                 effective_friend = friend_username
# #                 logger.warning(f"⚠️ [WS] ASSUMED received message from {friend_username} (unclear sender)")
            
# #             else:
# #                 logger.warning(f"⚠️ [WS] Cannot determine message direction for: {msg}")
# #                 logger.warning(f"⚠️ [WS] sender={sender}, recipient={recipient}, current_user={current_username}, friend={friend_username}")
# #                 # Default to received to be safe
# #                 is_sent = False
# #                 effective_friend = sender or friend_username or "unknown"
            
# #             logger.info(f"📚 [WS] Final determination: is_sent={is_sent}, sender={sender}, content={content[:30]}..., type={message_type}")
            
# #             # Create message data
# #             result = {
# #                 "sender": sender,
# #                 "message": content,
# #                 "timestamp": display_time,
# #                 "is_sent": is_sent,
# #                 "message_type": message_type
# #             }
            
# #             # Handle file/image data from server
# #             if message_type in ['image', 'file']:
# #                 result.update({
# #                     'file_name': msg.get('file_name'),
# #                     'file_size': msg.get('file_size'),
# #                     'mime_type': msg.get('mime_type')
# #                 })
                
# #                 # FIX: For images, decode and save the file data locally
# #                 file_data_b64 = msg.get('file_data')
# #                 if file_data_b64 and message_type == 'image':
# #                     try:
# #                         # Create persistent chat images directory
# #                         chat_images_dir = os.path.join(os.path.expanduser('~'), '.messenger_chat_images')
# #                         os.makedirs(chat_images_dir, exist_ok=True)
                        
# #                         # Create unique filename based on sender and direction
# #                         file_name = msg.get('file_name', 'image.jpg')
# #                         clean_timestamp = display_time.replace(':', '').replace(' ', '_')
# #                         direction = "sent" if is_sent else "received"
# #                         from_user = current_username if is_sent else sender
# #                         unique_filename = f"{direction}_{from_user}_{clean_timestamp}_{file_name}"
# #                         local_file_path = os.path.join(chat_images_dir, unique_filename)
                        
# #                         # Decode and save if not already exists
# #                         if not os.path.exists(local_file_path):
# #                             image_data = base64.b64decode(file_data_b64)
# #                             with open(local_file_path, 'wb') as f:
# #                                 f.write(image_data)
# #                             logger.info(f"📷 [WS] Saved chat history image: {local_file_path}")
# #                         else:
# #                             logger.info(f"📷 [WS] Image already exists: {local_file_path}")
                        
# #                         # Set file path for display
# #                         result['file_path'] = local_file_path
# #                         result['message'] = file_name  # Use filename as display text
                        
# #                     except Exception as e:
# #                         logger.error(f"❌ [WS] Error saving chat history image: {e}")
# #                         result['message'] = msg.get('file_name', 'Image (failed to load)')
                
# #                 elif message_type == 'file':
# #                     # For files, just use filename as display text
# #                     result['message'] = msg.get('file_name', 'File')
            
# #             logger.info(f"📚 [WS] Final result: {result}")
# #             return result
            
# #         except Exception as e:
# #             logger.error(f"❌ [WS] Error processing message: {e}")
# #             logger.error(f"❌ [WS] Problem message was: {msg}")
# #             import traceback
# #             traceback.print_exc()
# #             return None
    
# #     def format_timestamp(self, timestamp, is_timestamp=False):
# #         """Format timestamp for display"""
# #         try:
# #             if timestamp:
# #                 if is_timestamp and isinstance(timestamp, (int, float)):
# #                     dt = datetime.datetime.fromtimestamp(timestamp)
# #                 elif isinstance(timestamp, str):
# #                     dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
# #                 else:
# #                     dt = datetime.datetime.fromtimestamp(timestamp)
# #                 return dt.strftime("%H:%M")
# #             return datetime.datetime.now().strftime("%H:%M")
# #         except:
# #             return datetime.datetime.now().strftime("%H:%M")
    
# #     def send_message(self, recipient_id, message_text):
# #         """Send message to friend"""
# #         if not recipient_id.strip() or not message_text.strip():
# #             return False
        
# #         message_data = {"recipient_id": recipient_id, "message": message_text}
        
# #         if self.websocket and self.loop:
# #             try:
# #                 future = asyncio.run_coroutine_threadsafe(
# #                     self.websocket.send(json.dumps(message_data)), self.loop
# #                 )
# #                 future.result(timeout=1.0)
# #                 logger.info("✅ Message sent successfully")
# #                 return True
# #             except Exception as e:
# #                 logger.error(f"❌ Failed to send message: {e}")
# #                 self.message_queue.append(message_data)
# #                 return False
# #         else:
# #             self.message_queue.append(message_data)
# #             return False
    
# #     def send_file_message(self, message_data):
# #         """Send file message to friend with size checking"""
# #         if not message_data.get("recipient_id") or not message_data.get("file_data"):
# #             return False
        
# #         # Check message size before sending
# #         message_json = json.dumps(message_data)
# #         message_size = len(message_json.encode('utf-8'))
# #         max_size = 8 * 1024 * 1024  # 8MB limit for safety (server has 10MB limit)
        
# #         print(f"📤 [WS] File message size: {message_size/1024/1024:.2f}MB")
        
# #         if message_size > max_size:
# #             logger.error(f"❌ File message too large: {message_size/1024/1024:.1f}MB > {max_size/1024/1024:.1f}MB")
# #             return False
        
# #         if self.websocket and self.loop:
# #             try:
# #                 future = asyncio.run_coroutine_threadsafe(
# #                     self.websocket.send(message_json), self.loop
# #                 )
# #                 future.result(timeout=15.0)  # Longer timeout for large files
# #                 logger.info("✅ File message sent successfully")
# #                 return True
# #             except asyncio.TimeoutError:
# #                 logger.error("❌ Timeout sending file message")
# #                 self.message_queue.append(message_data)
# #                 return False
# #             except websockets.exceptions.ConnectionClosedError as e:
# #                 if "message too big" in str(e):
# #                     logger.error(f"❌ File message rejected - too large: {e}")
# #                 else:
# #                     logger.error(f"❌ Connection closed while sending file: {e}")
# #                 return False
# #             except Exception as e:
# #                 logger.error(f"❌ Failed to send file message: {e}")
# #                 self.message_queue.append(message_data)
# #                 return False
# #         else:
# #             self.message_queue.append(message_data)
# #             return False
    
# #     def request_conversation_history(self, friend_username, room_id=None):
# #         """Request full conversation history for a specific friend"""
# #         if not friend_username:
# #             return False
        
# #         request_data = {
# #             "type": "request_conversation_history",
# #             "friend_username": friend_username
# #         }
        
# #         if room_id:
# #             request_data["room_id"] = room_id
        
# #         if self.websocket and self.loop:
# #             try:
# #                 future = asyncio.run_coroutine_threadsafe(
# #                     self.websocket.send(json.dumps(request_data)), self.loop
# #                 )
# #                 future.result(timeout=5.0)
# #                 logger.info(f"📤 [WS] Requested conversation history for {friend_username}")
# #                 return True
# #             except Exception as e:
# #                 logger.error(f"❌ [WS] Failed to request conversation history: {e}")
# #                 return False
# #         else:
# #             logger.warning(f"⚠️ [WS] Cannot request history - no websocket connection")
# #             return False
        

# #     def stop(self):
# #         """Stop WebSocket thread"""
# #         self.running = False
# #         if self.websocket and self.loop:
# #             try:
# #                 future = asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
# #                 future.result(timeout=1.0)
# #             except:
# #                 pass


# # class HomePage(QWidget):
# #     """Clean home page with chat interface"""
    
# #     logout_requested = pyqtSignal()
# #     friend_list_requested = pyqtSignal()
    
# #     def __init__(self):
# #         super().__init__()
# #         self.current_chat_user = None
# #         self.auth_token = None
# #         self.current_user = None
# #         self.chat_history = {}  # Store all chat history
# #         self.websocket_client = None
        
# #         # Create navigation sidebar
# #         self.sidebar = NavigationSidebar(active_page="home")
# #         self.sidebar.friend_list_clicked.connect(self.on_friend_list_clicked)
        
# #         self.setup_ui()
    
# #     def set_auth_token(self, token):
# #         """Set authentication token and start WebSocket"""
# #         self.auth_token = token
# #         self.start_websocket_connection()
    
# #     def set_current_user(self, user_info):
# #         """Set current user info"""
# #         self.current_user = user_info
        
# #         # FIX: Set current username in WebSocket client if it exists
# #         if self.websocket_client and user_info:
# #             username = user_info.get('username', '')
# #             self.websocket_client.set_current_username(username)
# #             print(f"🔧 [HOME] Set WebSocket username to: {username}")
    
# #     def show_page(self):
# #         """Called when navigating to home page - show appropriate interface"""
# #         print(f"📱 [HOME] show_page called")
# #         print(f"📱 [HOME] Current chat user: {self.current_chat_user}")
# #         print(f"📱 [HOME] Chat history keys: {list(self.chat_history.keys())}")
# #         print(f"📱 [HOME] Chat history length: {len(self.chat_history)}")
        
# #         # If we have chat history but no current chat, auto-select one
# #         if self.chat_history and not self.current_chat_user:
# #             print("📱 [HOME] Have chat history but no current chat, auto-selecting...")
            
# #             # Priority: iniahmad if exists, otherwise most recent
# #             if "iniahmad" in self.chat_history:
# #                 print("📱 [HOME] Showing iniahmad chat on home page navigation")
# #                 self.start_chat_with_friend("iniahmad")
# #             else:
# #                 most_recent = self.find_most_recent_chat(self.chat_history)
# #                 if most_recent:
# #                     print(f"📱 [HOME] Showing most recent chat with {most_recent}")
# #                     self.start_chat_with_friend(most_recent)
        
# #         # If we have a current chat, make sure it's displayed
# #         elif self.current_chat_user:
# #             print(f"📱 [HOME] Showing current chat with {self.current_chat_user}")
# #             self.display_chat_messages(self.current_chat_user)
# #             self.show_chat_interface()
        
# #         # Otherwise show welcome screen (no chats available)
# #         else:
# #             print("📱 [HOME] No chats available, showing welcome screen")
# #             print(f"📱 [HOME] Debug: chat_history empty? {not bool(self.chat_history)}")
# #             print(f"📱 [HOME] Debug: current_chat_user empty? {not bool(self.current_chat_user)}")
# #             self.show_welcome_screen()
    
# #     def start_websocket_connection(self):
# #         """Start WebSocket connection for messaging"""
# #         print("🔗 [HOME] Starting WebSocket connection...")
        
# #         # Stop existing connection
# #         if self.websocket_client:
# #             print("🔗 [HOME] Stopping existing WebSocket...")
# #             self.websocket_client.stop()
# #             self.websocket_client.wait()
        
# #         # Start new connection
# #         self.websocket_client = WebSocketThread(self.auth_token)
        
# #         # FIX: Set current username immediately after creating client
# #         if self.current_user:
# #             username = self.current_user.get('username', '')
# #             self.websocket_client.set_current_username(username)
# #             print(f"🔧 [HOME] Set WebSocket username to: {username}")
        
# #         # Connect signals with debug
# #         print("🔗 [HOME] Connecting WebSocket signals...")
# #         self.websocket_client.previous_conversations_received.connect(self.handle_chat_history)
# #         self.websocket_client.conversation_history_received.connect(self.handle_conversation_history_update)
# #         self.websocket_client.message_received.connect(self.handle_incoming_message)
# #         self.websocket_client.connection_established.connect(self.on_websocket_connected)
# #         self.websocket_client.connection_lost.connect(self.on_websocket_disconnected)
# #         self.websocket_client.message_sent_confirmation.connect(self.on_message_sent_confirmation)
        
# #         print("✅ [HOME] WebSocket signals connected, starting thread...")
# #         self.websocket_client.start()
    
# #     @pyqtSlot()
# #     def on_websocket_connected(self):
# #         """Handle WebSocket connection"""
# #         print("✅ Connected to backend server")
# #         # Don't auto-show chats here - wait for chat history to load
    
# #     @pyqtSlot()
# #     def on_websocket_disconnected(self):
# #         """Handle WebSocket disconnection"""
# #         print("❌ Disconnected from backend server")
    
# #     @pyqtSlot(str, str, str, bool)
# #     def on_message_sent_confirmation(self, recipient_id, message, timestamp, delivered):
# #         """Handle message delivery confirmation"""
# #         status = "delivered" if delivered else "pending"
# #         print(f"✅ Message to {recipient_id}: {status}")
    
# #     @pyqtSlot(dict)
# #     def handle_chat_history(self, friend_conversations):
# #         """Handle chat history from server with enhanced debugging"""
# #         print(f"📚 [HOME] *** RECEIVED CHAT HISTORY SIGNAL ***")
# #         print(f"📚 [HOME] Received chat history for {len(friend_conversations)} friends")
        
# #         # Enhanced debugging for each friend's conversation
# #         for friend, messages in friend_conversations.items():
# #             sent_count = sum(1 for msg in messages if msg.get('is_sent', False))
# #             received_count = len(messages) - sent_count
# #             print(f"📚 [HOME] {friend}: {len(messages)} total ({sent_count} sent, {received_count} received)")
            
# #             # Debug first few messages
# #             for i, msg in enumerate(messages[:3]):  # Show first 3 messages
# #                 msg_type = msg.get('message_type', 'text')
# #                 is_sent = msg.get('is_sent', False)
# #                 sender = msg.get('sender', 'unknown')
# #                 content = msg.get('message', '')[:30]
# #                 direction = "SENT" if is_sent else "RECEIVED"
# #                 print(f"  {i+1}. {direction} {msg_type} from {sender}: {content}...")
        
# #         # Store chat history
# #         self.chat_history.update(friend_conversations)
# #         print(f"📚 [HOME] Updated self.chat_history, now has {len(self.chat_history)} friends")
        
# #         # Update chat list with friends who have conversations
# #         for friend_username in friend_conversations.keys():
# #             print(f"📚 [HOME] Adding {friend_username} to chat list...")
# #             self.add_friend_to_chat_list(friend_username)
        
# #         # Auto-open a chat if no chat is currently selected
# #         if not self.current_chat_user and friend_conversations:
# #             print("📚 [HOME] No current chat selected, auto-opening...")
            
# #             # Priority: open iniahmad's chat if it exists
# #             if "iniahmad" in friend_conversations:
# #                 print("📱 [HOME] Auto-opening chat with iniahmad")
# #                 self.start_chat_with_friend("iniahmad")
# #             else:
# #                 # Otherwise, open the most recent chat (last message)
# #                 most_recent_friend = self.find_most_recent_chat(friend_conversations)
# #                 if most_recent_friend:
# #                     print(f"📱 [HOME] Auto-opening most recent chat with {most_recent_friend}")
# #                     self.start_chat_with_friend(most_recent_friend)
        
# #         # If currently viewing a chat, refresh it
# #         elif self.current_chat_user and self.current_chat_user in friend_conversations:
# #             print(f"📱 [HOME] Refreshing current chat with {self.current_chat_user}")
# #             # Check if we have both sent and received messages
# #             msgs = friend_conversations[self.current_chat_user]
# #             sent_count = sum(1 for msg in msgs if msg.get('is_sent', False))
# #             received_count = len(msgs) - sent_count
# #             print(f"📱 [HOME] Current chat refresh: {len(msgs)} total, {sent_count} sent, {received_count} received")
# #             self.display_chat_messages(self.current_chat_user)
        
# #         print(f"📚 [HOME] *** CHAT HISTORY PROCESSING COMPLETE ***")
    
# #     @pyqtSlot(str, list)
# #     def handle_conversation_history_update(self, friend_username, messages):
# #         """Handle updated conversation history for a specific friend"""
# #         print(f"📚 [HOME] *** RECEIVED CONVERSATION HISTORY UPDATE for {friend_username} ***")
        
# #         sent_count = sum(1 for msg in messages if msg.get('is_sent', False))
# #         received_count = len(messages) - sent_count
# #         print(f"📚 [HOME] Updated history: {len(messages)} total ({sent_count} sent, {received_count} received)")
        
# #         # Update chat history for this friend
# #         self.chat_history[friend_username] = messages
        
# #         # If this is the currently active chat, refresh the display
# #         if self.current_chat_user == friend_username:
# #             print(f"📱 [HOME] Refreshing active chat display for {friend_username}")
# #             self.display_chat_messages(friend_username)
        
# #         # Update chat list preview
# #         if messages:
# #             last_msg = messages[-1]
# #             msg_type = last_msg.get('message_type', 'text')
            
# #             if msg_type == 'image':
# #                 preview_text = "📷 Image"
# #             elif msg_type == 'file':
# #                 preview_text = f"📎 {last_msg.get('file_name', 'File')}"
# #             else:
# #                 preview_text = last_msg.get('message', '')
            
# #             if last_msg.get('is_sent', False):
# #                 preview_text = f"You: {preview_text}"
            
# #             timestamp = last_msg.get('timestamp', '')
# #             self.update_chat_list_preview(friend_username, preview_text, timestamp)
        
# #         print(f"📚 [HOME] *** CONVERSATION HISTORY UPDATE COMPLETE for {friend_username} ***")
    
# #     @pyqtSlot(str, str, str, str, dict)
# #     def handle_incoming_message(self, from_username, message_text, timestamp, message_type='text', file_data=None):
# #         """Handle incoming message with file/image support"""
# #         print(f"📥 Message from {from_username}: {message_text} (type: {message_type})")

# #         # Get current user's username for comparison
# #         current_username = self.current_user.get('username', '') if self.current_user else 'indira123'

# #         # IMPORTANT FIX: Ignore messages from ourselves (echoes/confirmations)
# #         if from_username == current_username:
# #             print(f"📝 [HOME] Ignoring message from self: {from_username}")
# #             return

# #         # Store message in chat history
# #         if from_username not in self.chat_history:
# #             self.chat_history[from_username] = []

# #         # Create base message data
# #         message_data = {
# #             'message': message_text,
# #             'message_type': message_type,
# #             'is_sent': False,  # Always False for incoming messages
# #             'timestamp': timestamp,
# #             'sender': from_username
# #         }

# #         # Handle file/image data
# #         if file_data and message_type in ['image', 'file']:
# #             print(f"🔍 [HANDLER] Processing {message_type} from {from_username}")
# #             print(f"🔍 [HANDLER] File data: {list(file_data.keys())}")
            
# #             # Add file metadata
# #             message_data.update({
# #                 'file_name': file_data.get('file_name', 'Unknown file'),
# #                 'file_size': file_data.get('file_size', 0),
# #                 'mime_type': file_data.get('mime_type', 'application/octet-stream')
# #             })
            
# #             # For images, save to temp folder for display
# #             if message_type == 'image' and file_data.get('file_data'):
# #                 try:
# #                     print(f"🔍 [HANDLER] Decoding image data...")
# #                     # Decode base64 image data
# #                     image_data = base64.b64decode(file_data['file_data'])
                    
# #                     # Create persistent chat images directory
# #                     chat_images_dir = os.path.join(os.path.expanduser('~'), '.messenger_chat_images')
# #                     os.makedirs(chat_images_dir, exist_ok=True)
                    
# #                     # Create temp file with proper extension
# #                     file_name = file_data.get('file_name', 'image.jpg')
# #                     # Clean timestamp for filename
# #                     clean_timestamp = timestamp.replace(':', '').replace(' ', '_')
# #                     temp_file_path = os.path.join(chat_images_dir, f"received_{from_username}_{clean_timestamp}_{file_name}")
                    
# #                     print(f"🔍 [HANDLER] Saving image to: {temp_file_path}")
# #                     with open(temp_file_path, 'wb') as f:
# #                         f.write(image_data)
                    
# #                     # Verify file was created and has content
# #                     if os.path.exists(temp_file_path):
# #                         file_size = os.path.getsize(temp_file_path)
# #                         print(f"✅ [HANDLER] Image saved successfully: {file_size} bytes")
                        
# #                         # Store the temp file path for display
# #                         message_data['file_path'] = temp_file_path
# #                         # Update message text to be more user-friendly
# #                         message_data['message'] = file_data.get('file_name', 'Image')
# #                     else:
# #                         print(f"❌ [HANDLER] Failed to save image file")
# #                         message_data['message'] = file_data.get('file_name', 'Image (failed to save)')
                    
# #                 except Exception as e:
# #                     print(f"❌ [HANDLER] Error saving received image: {e}")
# #                     import traceback
# #                     traceback.print_exc()
# #                     # Fallback to showing filename
# #                     message_data['message'] = file_data.get('file_name', 'Image (failed to load)')
            
# #             elif message_type == 'file':
# #                 # For files, just use filename as display text
# #                 message_data['message'] = file_data.get('file_name', 'File')
# #                 print(f"🔍 [HANDLER] File message processed: {message_data['message']}")

# #         # Add message to chat history (only once!)
# #         self.chat_history[from_username].append(message_data)
# #         print(f"💾 [HANDLER] Message from {from_username} stored in chat history.")

# #         # Add friend to chat list
# #         self.add_friend_to_chat_list(from_username)

# #         # If the user is currently viewing this chat, add the new bubble to the display
# #         if self.current_chat_user == from_username:
# #             print(f"✅ [HANDLER] Chat with {from_username} is active. Adding bubble to display.")
# #             self.add_message_to_display_with_type(message_data)
# #         else:
# #             print(f"ℹ️ [HANDLER] Chat with {from_username} is not active. UI will not be updated instantly.")

# #         # Update chat list preview
# #         if message_type == 'image':
# #             preview_text = "📷 Image"
# #         elif message_type == 'file':
# #             preview_text = f"📎 {file_data.get('file_name', 'File') if file_data else 'File'}"
# #         else:
# #             preview_text = message_text

# #         self.update_chat_list_preview(from_username, preview_text, timestamp)
    
# #     def send_message(self):
# #         """Send message to current friend"""
# #         if not self.current_chat_user or not self.websocket_client:
# #             return
    
# #         message_text = self.message_input.text().strip()
# #         if not message_text:
# #             return
    
# #         timestamp = datetime.datetime.now().strftime("%H:%M")
    
# #         # Send via WebSocket
# #         success = self.websocket_client.send_message(self.current_chat_user, message_text)
    
# #         # Store locally and display
# #         if self.current_chat_user not in self.chat_history:
# #             self.chat_history[self.current_chat_user] = []
    
# #         message_data = {
# #             'message': message_text,
# #             'message_type': 'text',
# #             'is_sent': True,
# #             'timestamp': timestamp,
# #             'sender': self.current_user.get('username', '') if self.current_user else ''
# #         }
# #         self.chat_history[self.current_chat_user].append(message_data)
    
# #         # Ensure the recipient is in the chat list
# #         print(f"📝 [HOME] Ensuring recipient {self.current_chat_user} is in chat list...")
# #         self.add_friend_to_chat_list(self.current_chat_user)
    
# #         # Add to display
# #         self.add_message_to_display_with_type(message_data)
    
# #         # Update chat list preview
# #         self.update_chat_list_preview(self.current_chat_user, f"You: {message_text}", timestamp)
    
# #         # Clear input
# #         self.message_input.clear()
    
# #         print(f"📤 Sent message to {self.current_chat_user}: {message_text}")
    
# #     def open_file_dialog(self):
# #         """Open file selection dialog"""
# #         if not self.current_chat_user:
# #             QMessageBox.warning(self, "No Chat Selected", "Please select a friend to chat with first.")
# #             return
        
# #         dialog = FileSelectionDialog(self)
# #         if dialog.exec_() == QDialog.Accepted:
# #             if dialog.selected_file_path and dialog.file_type:
# #                 self.send_file(dialog.selected_file_path, dialog.file_type)

# #     def send_file(self, file_path, file_type):
# #         """Send file or image to current friend with size limits and compression"""
# #         if not self.current_chat_user or not self.websocket_client:
# #             return
        
# #         try:
# #             # Get file info
# #             file_name = os.path.basename(file_path)
# #             file_size = os.path.getsize(file_path)
            
# #             print(f"📎 [SEND] Preparing to send {file_type}: {file_name} ({file_size} bytes)")
# #             print(f"📎 [SEND] Original file path: {file_path}")
            
# #             # Check file size limits (stricter for WebSocket)
# #             if file_type == 'image':
# #                 max_size = 2 * 1024 * 1024  # 2MB for images
# #             else:
# #                 max_size = 1 * 1024 * 1024  # 1MB for other files
                
# #             if file_size > max_size:
# #                 QMessageBox.warning(self, "File Too Large", 
# #                                   f"File size ({file_size/1024/1024:.1f}MB) exceeds the {max_size/1024/1024:.0f}MB limit for {file_type}s.\n"
# #                                   f"Please choose a smaller file or compress it first.")
# #                 return
            
# #             # Read and process file
# #             if file_type == 'image':
# #                 # Compress image if needed
# #                 file_data, compressed_size = self.compress_image_if_needed(file_path, max_size)
# #                 if compressed_size != file_size:
# #                     print(f"📷 [SEND] Image compressed: {file_size} → {compressed_size} bytes")
# #                     file_size = compressed_size
# #             else:
# #                 # Read file normally
# #                 with open(file_path, 'rb') as f:
# #                     file_data = f.read()
            
# #             # Encode to base64
# #             file_base64 = base64.b64encode(file_data).decode('utf-8')
            
# #             # Check final encoded size (base64 adds ~33% overhead)
# #             encoded_size = len(file_base64)
# #             max_encoded_size = 3 * 1024 * 1024  # 3MB encoded limit
            
# #             if encoded_size > max_encoded_size:
# #                 QMessageBox.warning(self, "Encoded File Too Large", 
# #                                   f"After encoding, file size ({encoded_size/1024/1024:.1f}MB) exceeds the 3MB transmission limit.\n"
# #                                   f"Please choose a smaller file.")
# #                 return
            
# #             print(f"✅ [SEND] File ready for transmission: {encoded_size} bytes encoded")
            
# #             # Get MIME type
# #             mime_type, _ = mimetypes.guess_type(file_path)
# #             if not mime_type:
# #                 mime_type = 'application/octet-stream'
            
# #             timestamp = datetime.datetime.now().strftime("%H:%M")
            
# #             # Create message data for WebSocket
# #             message_data = {
# #                 "recipient_id": self.current_chat_user,
# #                 "message_type": file_type,
# #                 "file_name": file_name,
# #                 "file_data": file_base64,
# #                 "file_size": file_size,
# #                 "mime_type": mime_type
# #             }
            
# #             # Send via WebSocket
# #             success = self.websocket_client.send_file_message(message_data)
            
# #             # Store locally and display
# #             if self.current_chat_user not in self.chat_history:
# #                 self.chat_history[self.current_chat_user] = []
            
# #             # FIX: For images, copy to a permanent location for display
# #             display_path = file_path  # Default to original path
            
# #             if file_type == 'image':
# #                 try:
# #                     # Create a permanent copy in chat images folder for display
# #                     chat_images_dir = os.path.join(os.path.expanduser('~'), '.messenger_chat_images')
# #                     os.makedirs(chat_images_dir, exist_ok=True)
                    
# #                     # Use timestamp to make unique filename
# #                     clean_timestamp = timestamp.replace(':', '').replace(' ', '_')
# #                     current_username = self.current_user.get('username', 'user') if self.current_user else 'user'
# #                     temp_file_path = os.path.join(chat_images_dir, f"sent_{current_username}_{clean_timestamp}_{file_name}")
                    
# #                     # Copy file to persistent location
# #                     shutil.copy2(file_path, temp_file_path)
# #                     display_path = temp_file_path
                    
# #                     print(f"📷 [SEND] Copied image for display to: {display_path}")
                    
# #                     # Verify the copy was successful
# #                     if os.path.exists(display_path):
# #                         print(f"✅ [SEND] Display image exists: {os.path.getsize(display_path)} bytes")
# #                     else:
# #                         print(f"❌ [SEND] Display image copy failed, using original path")
# #                         display_path = file_path
                        
# #                 except Exception as e:
# #                     print(f"⚠️ [SEND] Could not copy image for display: {e}")
# #                     display_path = file_path
            
# #             local_message_data = {
# #                 'message': file_name,
# #                 'message_type': file_type,
# #                 'file_path': display_path,  # Use the display path
# #                 'file_name': file_name,
# #                 'file_size': file_size,
# #                 'mime_type': mime_type,
# #                 'is_sent': True,
# #                 'timestamp': timestamp,
# #                 'sender': self.current_user.get('username', '') if self.current_user else ''
# #             }
            
# #             print(f"📎 [SEND] Storing message data: {local_message_data}")
            
# #             self.chat_history[self.current_chat_user].append(local_message_data)
            
# #             # Ensure recipient is in chat list
# #             self.add_friend_to_chat_list(self.current_chat_user)
            
# #             # Add to display
# #             self.add_message_to_display_with_type(local_message_data)
            
# #             # Update chat list preview
# #             preview_text = f"📎 {file_name}" if file_type == 'file' else f"📷 Image"
# #             self.update_chat_list_preview(self.current_chat_user, f"You: {preview_text}", timestamp)
            
# #             print(f"📤 Sent {file_type} to {self.current_chat_user}: {file_name} ({file_size} bytes)")
            
# #         except Exception as e:
# #             print(f"❌ Error sending file: {e}")
# #             import traceback
# #             traceback.print_exc()
# #             QMessageBox.critical(self, "Send Error", f"Failed to send file: {str(e)}")

# #     def compress_image_if_needed(self, image_path, max_size):
# #         """Compress image if it exceeds size limit"""
# #         try:
# #             from PIL import Image
# #             import io
            
# #             # Open image
# #             with Image.open(image_path) as img:
# #                 # Convert to RGB if necessary
# #                 if img.mode in ('RGBA', 'P'):
# #                     img = img.convert('RGB')
                
# #                 # Get original size
# #                 original_size = os.path.getsize(image_path)
                
# #                 if original_size <= max_size:
# #                     # No compression needed
# #                     with open(image_path, 'rb') as f:
# #                         return f.read(), original_size
                
# #                 # Try different compression levels
# #                 for quality in [85, 70, 55, 40, 25]:
# #                     output = io.BytesIO()
# #                     img.save(output, format='JPEG', quality=quality, optimize=True)
# #                     compressed_data = output.getvalue()
                    
# #                     if len(compressed_data) <= max_size:
# #                         print(f"📷 [COMPRESS] Compressed to quality {quality}%")
# #                         return compressed_data, len(compressed_data)
                
# #                 # If still too large, resize the image
# #                 width, height = img.size
# #                 for scale in [0.8, 0.6, 0.4, 0.2]:
# #                     new_width = int(width * scale)
# #                     new_height = int(height * scale)
# #                     resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
# #                     output = io.BytesIO()
# #                     resized_img.save(output, format='JPEG', quality=70, optimize=True)
# #                     compressed_data = output.getvalue()
                    
# #                     if len(compressed_data) <= max_size:
# #                         print(f"📷 [COMPRESS] Resized to {scale*100}% and compressed")
# #                         return compressed_data, len(compressed_data)
                
# #                 # If all else fails, return original and let error handling deal with it
# #                 with open(image_path, 'rb') as f:
# #                     return f.read(), original_size
                    
# #         except ImportError:
# #             print("⚠️ [COMPRESS] PIL not available, cannot compress images")
# #             # Fall back to original file
# #             with open(image_path, 'rb') as f:
# #                 return f.read(), os.path.getsize(image_path)
# #         except Exception as e:
# #             print(f"❌ [COMPRESS] Error compressing image: {e}")
# #             # Fall back to original file
# #             with open(image_path, 'rb') as f:
# #                 return f.read(), os.path.getsize(image_path)

# #     def debug_message_data(self, message_data, context=""):
# #         """Debug helper to print message data structure"""
# #         print(f"🔍 DEBUG {context}:")
# #         print(f"  message: {message_data.get('message', 'N/A')}")
# #         print(f"  message_type: {message_data.get('message_type', 'N/A')}")
# #         print(f"  file_name: {message_data.get('file_name', 'N/A')}")
# #         print(f"  file_path: {message_data.get('file_path', 'N/A')}")
# #         print(f"  file_size: {message_data.get('file_size', 'N/A')}")
# #         print(f"  is_sent: {message_data.get('is_sent', 'N/A')}")
# #         print(f"  sender: {message_data.get('sender', 'N/A')}")
# #         if message_data.get('file_path'):
# #             file_exists = os.path.exists(message_data['file_path'])
# #             file_size = os.path.getsize(message_data['file_path']) if file_exists else 0
# #             print(f"  file_exists: {file_exists}")
# #             print(f"  actual_file_size: {file_size}")

# #     def add_message_to_display_with_type(self, message_data):
# #         """Add message with type info to chat display"""
# #         if not hasattr(self, 'messages_layout'):
# #             return
        
# #         # Debug the message data
# #         self.debug_message_data(message_data, "DISPLAY")
        
# #         # Remove stretch temporarily
# #         self.remove_layout_stretch(self.messages_layout)
        
# #         # Create message widget based on type
# #         message_widget = self.create_message_widget_enhanced(message_data)
# #         self.messages_layout.addWidget(message_widget)
        
# #         # Add stretch back
# #         self.messages_layout.addStretch()
        
# #         # Scroll to bottom
# #         QTimer.singleShot(50, self.scroll_to_bottom)

# #     def create_message_widget_enhanced(self, message_data):
# #         """Create enhanced message bubble widget that handles text, images, and files with click support"""
# #         container = QFrame()
# #         container.setStyleSheet("background-color: transparent; border: none;")
    
# #         layout = QHBoxLayout(container)
# #         layout.setContentsMargins(0, 0, 0, 0)
    
# #         # Get message info
# #         message_text = message_data.get('message', '')
# #         is_sent = message_data.get('is_sent', False)
# #         timestamp = message_data.get('timestamp', '')
# #         message_type = message_data.get('message_type', 'text')
    
# #         print(f"🎨 [UI] Creating widget for {message_type} message:")
# #         print(f"  text: {message_text}")
# #         print(f"  is_sent: {is_sent}")
# #         print(f"  file_path: {message_data.get('file_path', 'N/A')}")
    
# #         # Message bubble
# #         bubble = QFrame()
# #         bubble.setMaximumWidth(400)
    
# #         if is_sent:
# #             bubble.setStyleSheet("""
# #                 QFrame {
# #                     background-color: #A8B8BC;
# #                     border-radius: 15px;
# #                     padding: 10px 15px;
# #                 }
# #             """)
# #             layout.addStretch()
# #             layout.addWidget(bubble)
# #         else:
# #             bubble.setStyleSheet("""
# #                 QFrame {
# #                     background-color: #D5CECE;
# #                     border-radius: 15px;
# #                     padding: 10px 15px;
# #                 }
# #             """)
# #             layout.addWidget(bubble)
# #             layout.addStretch()
    
# #         bubble_layout = QVBoxLayout(bubble)
# #         bubble_layout.setContentsMargins(5, 5, 5, 5)
# #         bubble_layout.setSpacing(5)
    
# #         # Content based on message type
# #         if message_type == 'image':
# #             # Display image with click support
# #             image_label = QLabel()
# #             image_loaded = False
        
# #             # Try to load image from local path first
# #             image_path = message_data.get('file_path')
# #             print(f"🖼️ [UI] Attempting to load image from: {image_path}")
        
# #             if image_path and os.path.exists(image_path):
# #                 try:
# #                     print(f"🖼️ [UI] File exists, size: {os.path.getsize(image_path)} bytes")
# #                     pixmap = QPixmap(image_path)
# #                     if not pixmap.isNull():
# #                         # Scale image to fit nicely in chat
# #                         scaled_pixmap = pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
# #                         image_label.setPixmap(scaled_pixmap)
# #                         image_loaded = True
# #                         print(f"✅ [UI] Successfully loaded image from: {image_path}")
# #                     else:
# #                         print(f"❌ [UI] Failed to load image (null pixmap): {image_path}")
# #                 except Exception as e:
# #                     print(f"❌ [UI] Error loading image from {image_path}: {e}")
# #                     import traceback
# #                     traceback.print_exc()
# #             else:
# #                 if image_path:
# #                     print(f"❌ [UI] Image file does not exist: {image_path}")
# #                 else:
# #                     print(f"❌ [UI] No image path provided")
        
# #             # If image couldn't be loaded, show placeholder
# #             if not image_loaded:
# #                 placeholder_pixmap = QPixmap(200, 150)
# #                 placeholder_pixmap.fill(QColor(240, 240, 240))
            
# #                 # Draw placeholder text
# #                 painter = QPainter(placeholder_pixmap)
# #                 painter.setPen(QColor(150, 150, 150))
# #                 painter.drawText(placeholder_pixmap.rect(), Qt.AlignCenter, "📷\nImage\n(failed to load)")
# #                 painter.end()
            
# #                 image_label.setPixmap(placeholder_pixmap)
# #                 print("⚠️ [UI] Using placeholder image")
        
# #             # FIX: Add click functionality for images
# #             image_label.setStyleSheet("""
# #                 QLabel {
# #                     border: 1px solid #B0C4C6;
# #                     border-radius: 8px;
# #                     background-color: white;
# #                 }
# #                 QLabel:hover {
# #                     border: 2px solid #7A9499;
# #                     cursor: pointer;
# #                 }
# #             """)
# #             image_label.setScaledContents(False)
# #             image_label.setAlignment(Qt.AlignCenter)
            
# #             # Make image clickable
# #             image_label.mousePressEvent = lambda event: self.handle_image_click(message_data)
# #             image_label.setCursor(Qt.PointingHandCursor)
            
# #             bubble_layout.addWidget(image_label)
        
# #             # File name below image (if available and different from generic "Image")
# #             file_name = message_data.get('file_name', '')
# #             if file_name and file_name.lower() not in ['image', 'image.jpg', 'image.png']:
# #                 name_label = QLabel(file_name)
# #                 name_label.setStyleSheet("""
# #                     QLabel {
# #                         color: #2C2C2C;
# #                         font-size: 12px;
# #                         border: none;
# #                         background-color: transparent;
# #                     }
# #                 """)
# #                 name_label.setAlignment(Qt.AlignCenter)
# #                 name_label.setWordWrap(True)
# #                 bubble_layout.addWidget(name_label)
    
# #         elif message_type == 'file':
# #             # Display file icon and info with click support
# #             file_container = QFrame()
# #             file_container.setStyleSheet("""
# #                 QFrame {
# #                     background-color: rgba(255, 255, 255, 100);
# #                     border: 1px solid #B0C4C6;
# #                     border-radius: 8px;
# #                     padding: 10px;
# #                 }
# #                 QFrame:hover {
# #                     border: 2px solid #7A9499;
# #                     cursor: pointer;
# #                 }
# #             """)
            
# #             # Make file container clickable
# #             file_container.mousePressEvent = lambda event: self.handle_file_click(message_data)
# #             file_container.setCursor(Qt.PointingHandCursor)
            
# #             file_layout = QHBoxLayout(file_container)
# #             file_layout.setContentsMargins(10, 10, 10, 10)
        
# #             # File icon
# #             file_icon = QLabel("📄")
# #             file_icon.setStyleSheet("font-size: 24px;")
# #             file_layout.addWidget(file_icon)
        
# #             # File info
# #             info_layout = QVBoxLayout()
        
# #             file_name = message_data.get('file_name', message_text if message_text != 'File' else 'Unknown file')
# #             name_label = QLabel(file_name)
# #             name_label.setStyleSheet("""
# #                 QLabel {
# #                     color: #2C2C2C;
# #                     font-size: 14px;
# #                     font-weight: bold;
# #                     border: none;
# #                     background-color: transparent;
# #                 }
# #             """)
# #             name_label.setWordWrap(True)
        
# #             file_size = message_data.get('file_size', 0)
# #             if file_size > 0:
# #                 size_text = self.format_file_size(file_size)
# #                 size_label = QLabel(size_text)
# #                 size_label.setStyleSheet("""
# #                     QLabel {
# #                         color: #7F8C8D;
# #                         font-size: 12px;
# #                         border: none;
# #                         background-color: transparent;
# #                     }
# #                 """)
# #                 info_layout.addWidget(name_label)
# #                 info_layout.addWidget(size_label)
# #             else:
# #                 info_layout.addWidget(name_label)
        
# #             file_layout.addLayout(info_layout)
# #             bubble_layout.addWidget(file_container)
    
# #         else:
# #             # Regular text message
# #             message_label = QLabel(message_text)
# #             message_label.setWordWrap(True)
# #             message_label.setStyleSheet("""
# #                 QLabel {
# #                     color: #2C2C2C;
# #                     font-size: 14px;
# #                     border: none;
# #                 }
# #             """)
# #             bubble_layout.addWidget(message_label)
    
# #         # Timestamp
# #         time_label = QLabel(timestamp)
# #         time_label.setStyleSheet("""
# #             QLabel {
# #                 color: #7F8C8D;
# #                 font-size: 10px;
# #                 border: none;
# #             }
# #         """)
# #         time_label.setAlignment(Qt.AlignRight if is_sent else Qt.AlignLeft)
# #         bubble_layout.addWidget(time_label)
    
# #         return container

# #     def handle_image_click(self, message_data):
# #         """Handle clicking on an image to view or download"""
# #         file_path = message_data.get('file_path')
# #         file_name = message_data.get('file_name', 'image.jpg')
        
# #         if not file_path or not os.path.exists(file_path):
# #             QMessageBox.warning(self, "Image Not Found", "The image file could not be found.")
# #             return
        
# #         # Show options: View or Download
# #         msg_box = QMessageBox(self)
# #         msg_box.setWindowTitle("Image Options")
# #         msg_box.setText(f"What would you like to do with '{file_name}'?")
        
# #         view_btn = msg_box.addButton("View", QMessageBox.ActionRole)
# #         download_btn = msg_box.addButton("Download", QMessageBox.ActionRole)
# #         cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        
# #         msg_box.exec_()
        
# #         if msg_box.clickedButton() == view_btn:
# #             # Open image with default system viewer
# #             try:
# #                 import subprocess
# #                 import platform
                
# #                 if platform.system() == 'Windows':
# #                     os.startfile(file_path)
# #                 elif platform.system() == 'Darwin':  # macOS
# #                     subprocess.call(['open', file_path])
# #                 else:  # Linux
# #                     subprocess.call(['xdg-open', file_path])
                    
# #             except Exception as e:
# #                 QMessageBox.critical(self, "Error", f"Could not open image: {str(e)}")
                
# #         elif msg_box.clickedButton() == download_btn:
# #             self.download_file(file_path, file_name)

# #     def handle_file_click(self, message_data):
# #         """Handle clicking on a file to download"""
# #         file_name = message_data.get('file_name', 'file')
        
# #         # For files, we typically don't have the actual file data locally
# #         # We would need to request it from the server or download it
# #         QMessageBox.information(self, "File Download", 
# #                                f"File download functionality for '{file_name}' would be implemented here.\n"
# #                                f"This would typically request the file from the server.")

# #     def download_file(self, source_path, suggested_name):
# #         """Download/copy file to user-selected location"""
# #         try:
# #             # Let user choose where to save
# #             save_path, _ = QFileDialog.getSaveFileName(
# #                 self,
# #                 "Save File",
# #                 suggested_name,
# #                 "All Files (*.*)"
# #             )
            
# #             if save_path:
# #                 # Copy file to chosen location
# #                 shutil.copy2(source_path, save_path)
# #                 QMessageBox.information(self, "Download Complete", 
# #                                       f"File saved to:\n{save_path}")
                
# #         except Exception as e:
# #             QMessageBox.critical(self, "Download Error", f"Failed to download file: {str(e)}")

# #     def format_file_size(self, size_bytes):
# #         """Format file size in human readable format"""
# #         if size_bytes == 0:
# #             return "0 B"
        
# #         size_names = ["B", "KB", "MB", "GB"]
# #         i = 0
# #         size = float(size_bytes)
        
# #         while size >= 1024 and i < len(size_names) - 1:
# #             size /= 1024
# #             i += 1
        
# #         return f"{size:.1f} {size_names[i]}"
    
# #     def find_most_recent_chat(self, friend_conversations):
# #         """Find the friend with the most recent message"""
# #         try:
# #             most_recent_friend = None
# #             latest_timestamp = None
            
# #             for friend_username, messages in friend_conversations.items():
# #                 if not messages:
# #                     continue
                
# #                 # Get the last message timestamp
# #                 last_message = messages[-1]
# #                 timestamp_str = last_message.get('timestamp', '')
                
# #                 try:
# #                     # Convert timestamp to comparable format
# #                     if timestamp_str:
# #                         # Assuming timestamp is in "HH:MM" format, use today's date
# #                         today = datetime.datetime.now().date()
# #                         time_obj = datetime.datetime.strptime(timestamp_str, "%H:%M").time()
# #                         full_timestamp = datetime.datetime.combine(today, time_obj)
                        
# #                         if latest_timestamp is None or full_timestamp > latest_timestamp:
# #                             latest_timestamp = full_timestamp
# #                             most_recent_friend = friend_username
# #                 except:
# #                     # If timestamp parsing fails, just use the first friend as fallback
# #                     if most_recent_friend is None:
# #                         most_recent_friend = friend_username
            
# #             return most_recent_friend
# #         except Exception as e:
# #             print(f"❌ Error finding most recent chat: {e}")
# #             # Return first friend as fallback
# #             return list(friend_conversations.keys())[0] if friend_conversations else None
    
# #     def add_friend_to_chat_list(self, friend_username):
# #         """Add friend to chat list if not already there"""
# #         print(f"📝 [HOME] add_friend_to_chat_list called for: {friend_username}")
        
# #         # Check if already exists
# #         for i in range(self.chat_layout.count()):
# #             item = self.chat_layout.itemAt(i)
# #             if item and item.widget() and hasattr(item.widget(), 'objectName'):
# #                 if item.widget().objectName() == f"chat_{friend_username}":
# #                     print(f"📝 [HOME] {friend_username} already in chat list")
# #                     return  # Already exists
        
# #         print(f"📝 [HOME] Adding {friend_username} to chat list...")
        
# #         # Remove any stretch items
# #         self.clear_layout_stretches(self.chat_layout)
        
# #         # Create chat item
# #         chat_item = self.create_chat_item(friend_username)
# #         chat_item.setObjectName(f"chat_{friend_username}")
        
# #         # Add click handler
# #         def on_chat_clicked():
# #             print(f"📝 [HOME] Chat item clicked: {friend_username}")
# #             self.start_chat_with_friend(friend_username)
        
# #         chat_item.mousePressEvent = lambda event: on_chat_clicked()
        
# #         # Add to layout
# #         self.chat_layout.insertWidget(0, chat_item)
# #         self.chat_layout.addStretch()
        
# #         print(f"✅ [HOME] Added {friend_username} to chat list")
    
# #     def start_chat_with_friend(self, friend_username):
# #         """Start or continue chat with friend"""
# #         print(f"💬 [HOME] Starting chat with {friend_username}")
        
# #         self.current_chat_user = friend_username
        
# #         # Show chat interface
# #         self.show_chat_interface()
        
# #         # Update chat header
# #         if hasattr(self, 'friend_name_label'):
# #             self.friend_name_label.setText(friend_username)
        
# #         # Check if we have actual conversation data or just metadata
# #         if friend_username in self.chat_history:
# #             messages = self.chat_history[friend_username]
# #             has_placeholder = any(msg.get('message', '').startswith('Previous conversation') for msg in messages)
            
# #             # FIX: Check if we have a balanced conversation (both sent and received messages)
# #             sent_count = sum(1 for msg in messages if msg.get('is_sent', False))
# #             received_count = len(messages) - sent_count
            
# #             print(f"💬 [HOME] Chat analysis for {friend_username}:")
# #             print(f"  Total messages: {len(messages)}")
# #             print(f"  Sent messages: {sent_count}")
# #             print(f"  Received messages: {received_count}")
# #             print(f"  Has placeholder: {has_placeholder}")
            
# #             # If we only have sent messages or only received messages, request full history
# #             if (sent_count > 0 and received_count == 0) or (sent_count == 0 and received_count > 0):
# #                 print(f"⚠️ [HOME] Unbalanced conversation detected! Requesting full history...")
# #                 self.request_full_conversation_history(friend_username)
            
# #             if has_placeholder:
# #                 print(f"💬 [HOME] Only have conversation metadata for {friend_username}, requesting full history...")
# #                 # Extract room_id from placeholder if available
# #                 room_id = None
# #                 for msg in messages:
# #                     if 'room_id' in msg:
# #                         room_id = msg['room_id']
# #                         break
                
# #                 self.request_full_conversation_history(friend_username, room_id)
                
# #                 # Show placeholder and allow new messages
# #                 self.display_chat_messages(friend_username)
                
# #                 # Add a system message explaining the situation
# #                 if hasattr(self, 'messages_layout'):
# #                     self.remove_layout_stretch(self.messages_layout)
# #                     system_msg = self.create_system_message("Loading conversation history...")
# #                     self.messages_layout.addWidget(system_msg)
# #                     self.messages_layout.addStretch()
# #             else:
# #                 # Display chat history
# #                 print(f"💬 [HOME] Displaying {len(messages)} messages for {friend_username}")
# #                 self.display_chat_messages(friend_username)
# #         else:
# #             # No history, start fresh but also request any available history
# #             print(f"💬 [HOME] No local history for {friend_username}, requesting from server...")
# #             self.request_full_conversation_history(friend_username)
# #             self.display_chat_messages(friend_username)
        
# #         # Enable message input
# #         self.message_input.setPlaceholderText(f"Message {friend_username}...")
# #         self.message_input.setEnabled(True)
# #         self.message_input.setFocus()
        
# #         print(f"✅ [HOME] Chat interface ready for {friend_username}")
    
# #     def request_full_conversation_history(self, friend_username, room_id=None):
# #         """Request full conversation history from server"""
# #         if self.websocket_client:
# #             print(f"📤 [HOME] Requesting full conversation history for {friend_username}")
# #             success = self.websocket_client.request_conversation_history(friend_username, room_id)
# #             if success:
# #                 print(f"✅ [HOME] History request sent for {friend_username}")
# #             else:
# #                 print(f"❌ [HOME] Failed to request history for {friend_username}")
# #         else:
# #             print(f"❌ [HOME] No websocket client available to request history")
    
# #     def create_system_message(self, text):
# #         """Create a system message widget"""
# #         container = QFrame()
# #         container.setStyleSheet("background-color: transparent; border: none;")
        
# #         layout = QHBoxLayout(container)
# #         layout.setContentsMargins(0, 5, 0, 5)
        
# #         # System message (centered, italic)
# #         message_label = QLabel(text)
# #         message_label.setWordWrap(True)
# #         message_label.setAlignment(Qt.AlignCenter)
# #         message_label.setStyleSheet("""
# #             QLabel {
# #                 color: #7F8C8D;
# #                 font-size: 12px;
# #                 font-style: italic;
# #                 border: none;
# #                 padding: 10px;
# #             }
# #         """)
        
# #         layout.addWidget(message_label)
# #         return container
    
# #     def display_chat_messages(self, friend_username):
# #         """Display chat messages for friend with enhanced debugging"""
# #         if not hasattr(self, 'messages_layout'):
# #             return
        
# #         # Clear existing messages
# #         self.clear_layout(self.messages_layout)
        
# #         # Add messages if history exists
# #         if friend_username in self.chat_history:
# #             messages = self.chat_history[friend_username]
# #             sent_count = sum(1 for msg in messages if msg.get('is_sent', False))
# #             received_count = len(messages) - sent_count
            
# #             print(f"📺 [DISPLAY] Showing {len(messages)} messages for {friend_username}")
# #             print(f"📺 [DISPLAY]   {sent_count} sent messages, {received_count} received messages")
            
# #             for i, msg in enumerate(messages):
# #                 msg_type = msg.get('message_type', 'text')
# #                 is_sent = msg.get('is_sent', False)
# #                 sender = msg.get('sender', 'unknown')
# #                 content = msg.get('message', '')[:30]
# #                 direction = "SENT" if is_sent else "RECV"
                
# #                 print(f"📺 [DISPLAY]   {i+1}. {direction} {msg_type} from {sender}: {content}...")
                
# #                 # Check if it's an enhanced message with type info
# #                 if 'message_type' in msg:
# #                     self.add_message_to_display_with_type(msg)
# #                 else:
# #                     # Legacy text message
# #                     message_text = msg.get('message', '')
# #                     timestamp = msg.get('timestamp', '')
# #                     self.add_message_to_display(message_text, is_sent, timestamp)
# #         else:
# #             print(f"📺 [DISPLAY] No chat history found for {friend_username}")
        
# #         # Add stretch to keep messages at top
# #         self.messages_layout.addStretch()
        
# #         # Scroll to bottom
# #         QTimer.singleShot(100, self.scroll_to_bottom)
    
# #     def add_message_to_display(self, message_text, is_sent, timestamp):
# #         """Add message to chat display"""
# #         if not hasattr(self, 'messages_layout'):
# #             return
        
# #         # Remove stretch temporarily
# #         self.remove_layout_stretch(self.messages_layout)
        
# #         # Create message widget
# #         message_widget = self.create_message_widget(message_text, is_sent, timestamp)
# #         self.messages_layout.addWidget(message_widget)
        
# #         # Add stretch back
# #         self.messages_layout.addStretch()
        
# #         # Scroll to bottom
# #         QTimer.singleShot(50, self.scroll_to_bottom)
    
# #     def update_chat_list_preview(self, friend_username, message_preview, timestamp):
# #         """Update chat list item with latest message"""
# #         for i in range(self.chat_layout.count()):
# #             item = self.chat_layout.itemAt(i)
# #             if item and item.widget() and hasattr(item.widget(), 'objectName'):
# #                 if item.widget().objectName() == f"chat_{friend_username}":
# #                     # Update the preview (implementation depends on your chat item structure)
# #                     # This is a simplified version - adapt to your chat item layout
# #                     widget = item.widget()
# #                     try:
# #                         layout = widget.layout()
# #                         if layout and layout.count() >= 2:
# #                             # Find and update message label
# #                             for j in range(layout.count()):
# #                                 child_item = layout.itemAt(j)
# #                                 if child_item and isinstance(child_item.widget(), QLabel):
# #                                     label = child_item.widget()
# #                                     if ":" in label.text() or "message" in label.text().lower():
# #                                         preview = message_preview[:50] + "..." if len(message_preview) > 50 else message_preview
# #                                         label.setText(preview)
# #                                         break
# #                     except Exception as e:
# #                         print(f"❌ Error updating chat preview: {e}")
# #                     break
    
# #     # UI Setup Methods
# #     def setup_ui(self):
# #         """Setup main UI layout"""
# #         main_layout = QHBoxLayout(self)
# #         main_layout.setContentsMargins(0, 0, 0, 0)
# #         main_layout.setSpacing(0)
        
# #         # Add sidebar
# #         main_layout.addWidget(self.sidebar)
        
# #         # Add chat list
# #         self.setup_chat_list_sidebar(main_layout)
        
# #         # Add main content
# #         self.setup_main_content_area(main_layout)
    
# #     def setup_chat_list_sidebar(self, parent_layout):
# #         """Setup chat list sidebar"""
# #         chat_sidebar = QFrame()
# #         chat_sidebar.setFixedWidth(350)
# #         chat_sidebar.setStyleSheet("""
# #             QFrame {
# #                 background-color: #E8E1E1;
# #             }
# #         """)
        
# #         layout = QVBoxLayout(chat_sidebar)
# #         layout.setContentsMargins(0, 0, 0, 0)
# #         layout.setSpacing(0)
        
# #         # Header
# #         header = self.create_chat_header()
# #         layout.addWidget(header)
        
# #         # Search
# #         search = self.create_search_area()
# #         layout.addWidget(search)
        
# #         # Chat list
# #         self.setup_chat_scroll_area(layout)
        
# #         parent_layout.addWidget(chat_sidebar)
    
# #     def create_chat_header(self):
# #         """Create chat list header"""
# #         header = QFrame()
# #         header.setFixedHeight(66)
# #         header.setStyleSheet("""
# #             QFrame {
# #                 background-color: #9DB4B8;
# #             }
# #         """)
        
# #         layout = QVBoxLayout(header)
# #         layout.setContentsMargins(20, 0, 20, 0)
# #         layout.setAlignment(Qt.AlignCenter)
        
# #         title = QLabel("Start a new chat")
# #         title.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 16px;
# #                 font-weight: bold;
# #             }
# #         """)
# #         title.setAlignment(Qt.AlignCenter)
        
# #         layout.addWidget(title)
# #         return header
    
# #     def create_search_area(self):
# #         """Create search area"""
# #         search_container = QFrame()
# #         search_container.setFixedHeight(66)
# #         search_container.setStyleSheet("""
# #             QFrame {
# #                 background-color: #E8E1E1;
# #             }
# #         """)
        
# #         layout = QHBoxLayout(search_container)
# #         layout.setContentsMargins(15, 13, 15, 13)
        
# #         # Search input
# #         search_frame = QFrame()
# #         search_frame.setStyleSheet("""
# #             QFrame {
# #                 background-color: white;
# #                 border: 1px solid #B0C4C6;
# #                 border-radius: 8px;
# #             }
# #         """)
        
# #         search_layout = QHBoxLayout(search_frame)
# #         search_layout.setContentsMargins(10, 0, 10, 0)
# #         search_layout.setSpacing(8)
        
# #         search_icon = QLabel("🔍")
# #         search_icon.setStyleSheet("color: #7F8C8D; font-size: 14px;")
        
# #         self.chat_search_input = QLineEdit()
# #         self.chat_search_input.setPlaceholderText("Search for messages ...")
# #         self.chat_search_input.setStyleSheet("""
# #             QLineEdit {
# #                 border: none;
# #                 font-size: 14px;
# #                 color: #2C2C2C;
# #             }
# #         """)
        
# #         search_layout.addWidget(search_icon)
# #         search_layout.addWidget(self.chat_search_input)
        
# #         layout.addWidget(search_frame)
# #         return search_container
    
# #     def setup_chat_scroll_area(self, parent_layout):
# #         """Setup scrollable chat list"""
# #         self.chat_scroll_area = QScrollArea()
# #         self.chat_scroll_area.setWidgetResizable(True)
# #         self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
# #         self.chat_scroll_area.setStyleSheet("""
# #             QScrollArea {
# #                 background-color: #E8E1E1;
# #                 border: none;
# #             }
# #         """)
        
# #         self.chat_container = QWidget()
# #         self.chat_container.setStyleSheet("background-color: #E8E1E1;")
        
# #         self.chat_layout = QVBoxLayout(self.chat_container)
# #         self.chat_layout.setContentsMargins(0, 0, 0, 0)
# #         self.chat_layout.setSpacing(0)
# #         self.chat_layout.setAlignment(Qt.AlignTop)
# #         self.chat_layout.addStretch()
        
# #         self.chat_scroll_area.setWidget(self.chat_container)
# #         parent_layout.addWidget(self.chat_scroll_area)
    
# #     def setup_main_content_area(self, parent_layout):
# #         """Setup main content area"""
# #         self.main_content = QFrame()
# #         self.main_content.setStyleSheet("background-color: #9DB4B8;")
        
# #         self.content_layout = QVBoxLayout(self.main_content)
# #         self.content_layout.setContentsMargins(0, 0, 0, 0)
# #         self.content_layout.setSpacing(0)
        
# #         # Welcome area (shown initially)
# #         self.setup_welcome_area()
        
# #         # Message input (hidden initially)
# #         self.setup_message_input_area()
        
# #         parent_layout.addWidget(self.main_content)
    
# #     def setup_welcome_area(self):
# #         """Setup welcome message area"""
# #         self.welcome_area = QFrame()
# #         self.welcome_area.setStyleSheet("background-color: #9DB4B8;")
        
# #         layout = QVBoxLayout(self.welcome_area)
# #         layout.setAlignment(Qt.AlignCenter)
# #         layout.setSpacing(30)
# #         layout.setContentsMargins(50, 50, 50, 50)
        
# #         # Title
# #         title = QLabel("Welcome to Messenger!")
# #         title.setAlignment(Qt.AlignCenter)
# #         title.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 36px;
# #                 font-weight: bold;
# #             }
# #         """)
        
# #         # Subtitle
# #         subtitle = QLabel("Start by adding friends to begin chatting")
# #         subtitle.setAlignment(Qt.AlignCenter)
# #         subtitle.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 20px;
# #             }
# #         """)
        
# #         # Button
# #         friend_list_btn = QPushButton("Go to Friend List")
# #         friend_list_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: #7A9499;
# #                 color: white;
# #                 border: none;
# #                 border-radius: 15px;
# #                 padding: 20px 40px;
# #                 font-size: 18px;
# #                 font-weight: bold;
# #                 min-width: 200px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #6A8489;
# #             }
# #         """)
# #         friend_list_btn.clicked.connect(self.on_friend_list_clicked)
        
# #         layout.addWidget(title)
# #         layout.addWidget(subtitle)
# #         layout.addWidget(friend_list_btn, 0, Qt.AlignCenter)
        
# #         self.content_layout.addWidget(self.welcome_area)
    
# #     def setup_message_input_area(self):
# #         """Setup message input area with file attachment support"""
# #         self.input_container = QFrame()
# #         self.input_container.setFixedHeight(80)
# #         self.input_container.setStyleSheet("""
# #             QFrame {
# #                 background-color: #E8E1E1;
# #                 border-top: 2px solid #B0C4C6;
# #             }
# #         """)
        
# #         layout = QHBoxLayout(self.input_container)
# #         layout.setContentsMargins(20, 15, 20, 15)
# #         layout.setSpacing(15)
        
# #         # Attachment button - ENHANCED
# #         self.attach_btn = QPushButton("📎")
# #         self.attach_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: white;
# #                 border: 1px solid #B0C4C6;
# #                 border-radius: 8px;
# #                 font-size: 18px;
# #                 padding: 8px;
# #                 max-width: 40px;
# #                 max-height: 40px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #F0F0F0;
# #             }
# #         """)
# #         self.attach_btn.clicked.connect(self.open_file_dialog)  # Connect to file dialog
        
# #         # Message input
# #         self.message_input = QLineEdit()
# #         self.message_input.setPlaceholderText("Select a friend to start chatting...")
# #         self.message_input.setStyleSheet("""
# #             QLineEdit {
# #                 background-color: white;
# #                 border: 1px solid #B0C4C6;
# #                 border-radius: 8px;
# #                 padding: 12px 15px;
# #                 font-size: 16px;
# #                 color: #2C2C2C;
# #             }
# #             QLineEdit:focus {
# #                 border: 2px solid #7A9499;
# #             }
# #         """)
# #         self.message_input.setFixedHeight(50)
# #         self.message_input.setEnabled(False)
# #         self.message_input.returnPressed.connect(self.send_message)
        
# #         # Send button
# #         send_btn = QPushButton("Send")
# #         send_btn.setStyleSheet("""
# #             QPushButton {
# #                 background-color: #9DB4B8;
# #                 color: white;
# #                 border: none;
# #                 border-radius: 8px;
# #                 padding: 12px 25px;
# #                 font-size: 16px;
# #                 font-weight: bold;
# #                 min-width: 80px;
# #             }
# #             QPushButton:hover {
# #                 background-color: #8BA5A9;
# #             }
# #         """)
# #         send_btn.setFixedHeight(50)
# #         send_btn.clicked.connect(self.send_message)
        
# #         layout.addWidget(self.attach_btn)
# #         layout.addWidget(self.message_input)
# #         layout.addWidget(send_btn)
        
# #         self.input_container.hide()
# #         self.content_layout.addWidget(self.input_container)
    
# #     def show_chat_interface(self):
# #         """Show chat interface instead of welcome"""
# #         # Create or show chat area
# #         if not hasattr(self, 'chat_area'):
# #             self.create_chat_area()
        
# #         # Hide welcome, show chat and input
# #         self.welcome_area.hide()
# #         self.chat_area.show()
# #         self.input_container.show()
    
# #     def show_welcome_screen(self):
# #         """Show welcome screen (hide chat interface)"""
# #         if hasattr(self, 'chat_area'):
# #             self.chat_area.hide()
# #         self.input_container.hide()
# #         self.welcome_area.show()
# #         self.current_chat_user = None
    
# #     def create_chat_area(self):
# #         """Create chat messages area"""
# #         self.chat_area = QFrame()
# #         self.chat_area.setStyleSheet("background-color: #B8C4C8;")
        
# #         layout = QVBoxLayout(self.chat_area)
# #         layout.setContentsMargins(0, 0, 0, 0)
# #         layout.setSpacing(0)
        
# #         # Chat header
# #         chat_header = QFrame()
# #         chat_header.setFixedHeight(60)
# #         chat_header.setStyleSheet("""
# #             QFrame {
# #                 background-color: #B8C4C8;
# #                 border-bottom: 1px solid #A0A8AC;
# #             }
# #         """)
        
# #         header_layout = QHBoxLayout(chat_header)
# #         header_layout.setContentsMargins(30, 15, 30, 15)
        
# #         self.friend_name_label = QLabel("Friend")
# #         self.friend_name_label.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 18px;
# #                 font-weight: bold;
# #             }
# #         """)
        
# #         header_layout.addWidget(self.friend_name_label)
        
# #         # Messages scroll area
# #         self.messages_scroll = QScrollArea()
# #         self.messages_scroll.setWidgetResizable(True)
# #         self.messages_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
# #         self.messages_scroll.setStyleSheet("""
# #             QScrollArea {
# #                 background-color: #B8C4C8;
# #                 border: none;
# #             }
# #         """)
        
# #         self.messages_container = QWidget()
# #         self.messages_container.setStyleSheet("background-color: #B8C4C8;")
        
# #         self.messages_layout = QVBoxLayout(self.messages_container)
# #         self.messages_layout.setContentsMargins(20, 20, 20, 20)
# #         self.messages_layout.setSpacing(10)
# #         self.messages_layout.setAlignment(Qt.AlignTop)
# #         self.messages_layout.addStretch()
        
# #         self.messages_scroll.setWidget(self.messages_container)
        
# #         layout.addWidget(chat_header)
# #         layout.addWidget(self.messages_scroll)
        
# #         # Insert before input container
# #         self.content_layout.insertWidget(0, self.chat_area)
# #         self.chat_area.hide()  # Hidden initially
    
# #     def create_chat_item(self, friend_username):
# #         """Create chat list item"""
# #         chat_item = QFrame()
# #         chat_item.setFixedHeight(80)
# #         chat_item.setStyleSheet("""
# #             QFrame {
# #                 background-color: #E8E1E1;
# #                 border-bottom: 1px solid #D0C9C9;
# #             }
# #             QFrame:hover {
# #                 background-color: #D5CECE;
# #             }
# #         """)
# #         chat_item.setCursor(Qt.PointingHandCursor)
        
# #         layout = QVBoxLayout(chat_item)
# #         layout.setContentsMargins(15, 10, 15, 10)
# #         layout.setSpacing(5)
        
# #         # Top row: name and time
# #         top_row = QHBoxLayout()
        
# #         name_label = QLabel(friend_username)
# #         name_label.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 16px;
# #                 font-weight: bold;
# #             }
# #         """)
        
# #         time_label = QLabel("Now")
# #         time_label.setStyleSheet("""
# #             QLabel {
# #                 color: #7F8C8D;
# #                 font-size: 12px;
# #             }
# #         """)
# #         time_label.setAlignment(Qt.AlignRight)
        
# #         top_row.addWidget(name_label)
# #         top_row.addStretch()
# #         top_row.addWidget(time_label)
        
# #         # Bottom row: last message
# #         message_preview = "No messages yet"
# #         if friend_username in self.chat_history and self.chat_history[friend_username]:
# #             last_msg = self.chat_history[friend_username][-1]
# #             msg_type = last_msg.get('message_type', 'text')
            
# #             if msg_type == 'image':
# #                 preview_text = "📷 Image"
# #             elif msg_type == 'file':
# #                 preview_text = f"📎 {last_msg.get('file_name', 'File')}"
# #             else:
# #                 preview_text = last_msg.get('message', '')
            
# #             if last_msg.get('is_sent', False):
# #                 message_preview = f"You: {preview_text[:30]}..."
# #             else:
# #                 message_preview = preview_text[:40] + "..." if len(preview_text) > 40 else preview_text
        
# #         message_label = QLabel(message_preview)
# #         message_label.setStyleSheet("""
# #             QLabel {
# #                 color: #7F8C8D;
# #                 font-size: 14px;
# #             }
# #         """)
        
# #         layout.addLayout(top_row)
# #         layout.addWidget(message_label)
        
# #         return chat_item
    
# #     def create_message_widget(self, message_text, is_sent, timestamp):
# #         """Create message bubble widget"""
# #         container = QFrame()
# #         container.setStyleSheet("background-color: transparent; border: none;")
        
# #         layout = QHBoxLayout(container)
# #         layout.setContentsMargins(0, 0, 0, 0)
        
# #         # Message bubble
# #         bubble = QFrame()
# #         bubble.setMaximumWidth(400)
        
# #         if is_sent:
# #             bubble.setStyleSheet("""
# #                 QFrame {
# #                     background-color: #A8B8BC;
# #                     border-radius: 15px;
# #                     padding: 10px 15px;
# #                 }
# #             """)
# #             layout.addStretch()
# #             layout.addWidget(bubble)
# #         else:
# #             bubble.setStyleSheet("""
# #                 QFrame {
# #                     background-color: #D5CECE;
# #                     border-radius: 15px;
# #                     padding: 10px 15px;
# #                 }
# #             """)
# #             layout.addWidget(bubble)
# #             layout.addStretch()
        
# #         bubble_layout = QVBoxLayout(bubble)
# #         bubble_layout.setContentsMargins(5, 5, 5, 5)
# #         bubble_layout.setSpacing(2)
        
# #         # Message text
# #         message_label = QLabel(message_text)
# #         message_label.setWordWrap(True)
# #         message_label.setStyleSheet("""
# #             QLabel {
# #                 color: #2C2C2C;
# #                 font-size: 14px;
# #                 border: none;
# #             }
# #         """)
        
# #         # Timestamp
# #         time_label = QLabel(timestamp)
# #         time_label.setStyleSheet("""
# #             QLabel {
# #                 color: #7F8C8D;
# #                 font-size: 10px;
# #                 border: none;
# #             }
# #         """)
# #         time_label.setAlignment(Qt.AlignRight if is_sent else Qt.AlignLeft)
        
# #         bubble_layout.addWidget(message_label)
# #         bubble_layout.addWidget(time_label)
        
# #         return container
    
# #     # Utility Methods
# #     def clear_layout(self, layout):
# #         """Clear all widgets from layout"""
# #         while layout.count():
# #             child = layout.takeAt(0)
# #             if child.widget():
# #                 child.widget().deleteLater()
    
# #     def clear_layout_stretches(self, layout):
# #         """Remove stretch items from layout"""
# #         for i in range(layout.count() - 1, -1, -1):
# #             item = layout.itemAt(i)
# #             if item and item.spacerItem():
# #                 layout.removeItem(item)
    
# #     def remove_layout_stretch(self, layout):
# #         """Remove the last stretch item"""
# #         for i in range(layout.count() - 1, -1, -1):
# #             item = layout.itemAt(i)
# #             if item and item.spacerItem():
# #                 layout.removeItem(item)
# #                 break
    
# #     def scroll_to_bottom(self):
# #         """Scroll messages to bottom"""
# #         if hasattr(self, 'messages_scroll'):
# #             scrollbar = self.messages_scroll.verticalScrollBar()
# #             scrollbar.setValue(scrollbar.maximum())
    
# #     @pyqtSlot()
# #     def on_friend_list_clicked(self):
# #         """Handle friend list navigation"""
# #         print("👥 Friend list navigation requested")
# #         self.friend_list_requested.emit()
    
# #     def add_chat_to_list(self, friend_username):
# #         """Public method to add chat (called from main app)"""
# #         self.add_friend_to_chat_list(friend_username)
        
# #         # If this is the first chat and no chat is currently selected, auto-open it
# #         if not self.current_chat_user:
# #             print(f"📱 Auto-opening first chat with {friend_username}")
# #             self.start_chat_with_friend(friend_username)
    
# #     def closeEvent(self, event):
# #         """Clean up on close"""
# #         if self.websocket_client:
# #             self.websocket_client.stop()
# #             self.websocket_client.wait()
# #         event.accept()

# import asyncio
# import base64
# import json
# import logging
# import os
# import ssl
# import websockets
# from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot, Qt, QTimer
# from PyQt5.QtGui import QPixmap, QPainter, QColor
# from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QFrame, QVBoxLayout

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# # --- Download Manager (Handles download logic) ---
# class DownloadManager(QObject):
#     """Manages file download operations."""
#     download_complete = pyqtSignal(str, str)  # file_path, local_save_path
#     download_error = pyqtSignal(str, str)    # file_path, error_message

#     def __init__(self, websocket_client):
#         super().__init__()
#         self.websocket_client = websocket_client
#         self.active_downloads = {}

#     def start_download(self, file_info, save_path):
#         """Initiates a file download request."""
#         file_path = file_info.get("file_path")
#         if not file_path:
#             self.download_error.emit("", "File path is missing from message.")
#             return

#         print(f"📥 Requesting download for: {file_path} -> {save_path}")
        
#         # Create a downloader thread to avoid freezing the UI
#         downloader = FileDownloader(self.websocket_client, file_info, save_path)
#         downloader.download_complete.connect(self.download_complete)
#         downloader.download_error.connect(self.download_error)
        
#         self.active_downloads[file_path] = downloader
#         downloader.start()

# class FileDownloader(QThread):
#     """Worker thread to handle a single file download."""
#     download_complete = pyqtSignal(str, str)
#     download_error = pyqtSignal(str, str)

#     def __init__(self, websocket_client, file_info, save_path):
#         super().__init__()
#         self.websocket_client = websocket_client
#         self.file_info = file_info
#         self.save_path = save_path

#     def run(self):
#         """Send download request and wait for the file data response."""
#         file_path = self.file_info.get("file_path")
        
#         # This function returns a "future" object that will eventually hold the result.
#         future = self.websocket_client.request_file_data(file_path)
        
#         try:
#             # Wait for the file data to be received from the server (with a timeout)
#             file_data_b64 = future.result(timeout=45) # 45-second timeout for larger files
            
#             if file_data_b64:
#                 print(f"📦 Received file data for {file_path}, decoding and saving...")
#                 # Decode the base64 data and write it to the chosen file path
#                 file_bytes = base64.b64decode(file_data_b64)
#                 with open(self.save_path, 'wb') as f:
#                     f.write(file_bytes)
#                 print(f"✅ Successfully saved to {self.save_path}")
#                 self.download_complete.emit(file_path, self.save_path)
#             else:
#                 self.download_error.emit(file_path, "No data received from server.")

#         except asyncio.TimeoutError:
#             self.download_error.emit(file_path, "Download request timed out.")
#         except Exception as e:
#             self.download_error.emit(file_path, f"An error occurred: {str(e)}")
#         finally:
#             # Clean up the request from the websocket client
#             self.websocket_client.cleanup_file_request(file_path)


# # --- WebSocket Client (Handles communication with the server) ---
# class WebSocketClient(QObject):
#     """Handles all WebSocket communication for the home page."""
#     # Signals to communicate with the main UI
#     connection_established = pyqtSignal()
#     connection_lost = pyqtSignal()
#     previous_conversations_received = pyqtSignal(dict)
#     message_received = pyqtSignal(dict)
#     file_message_received = pyqtSignal(dict, bool)

#     def __init__(self, token, session_id):
#         super().__init__()
#         self.auth_token = token
#         self.session_id = session_id
#         self.websocket = None
#         self.loop = None
#         self._should_stop = False
#         self.username = ""
#         # NEW: Dictionary to track pending file download requests
#         self.file_request_futures = {}

#     def connect(self):
#         """Starts the WebSocket connection thread."""
#         self.thread = QThread()
#         self.moveToThread(self.thread)
#         self.thread.started.connect(self._run_async_loop)
#         self.thread.start()

#     def _run_async_loop(self):
#         """Initializes and runs the asyncio event loop."""
#         self.loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(self.loop)
#         self.loop.run_until_complete(self.listen())

#     async def listen(self):
#         """The main loop that connects and listens for messages."""
#         uri = "wss://localhost:8443"
#         ssl_context = ssl.create_default_context()
#         ssl_context.check_hostname = False
#         ssl_context.verify_mode = ssl.CERT_NONE

#         while not self._should_stop:
#             try:
#                 async with websockets.connect(uri, ssl=ssl_context, max_size=10 * 1024 * 1024) as websocket:
#                     self.websocket = websocket
#                     self.connection_established.emit()
                    
#                     # Authenticate upon connection
#                     auth_payload = {"token": self.auth_token, "session_id": self.session_id}
#                     await self.websocket.send(json.dumps(auth_payload))

#                     # Listen for messages
#                     async for message_json in self.websocket:
#                         message = json.loads(message_json)
#                         message_type = message.get("type")

#                         if message_type == "auth_success":
#                             self.username = message.get("user", {}).get("username")
#                             logger.info(f"Authenticated as {self.username}")
                            
#                             # --- FIX: Proactively request chat history after successful authentication ---
#                             logger.info("✅ Authentication successful. Requesting previous conversations...")
#                             await self.websocket.send(json.dumps({"type": "get_previous_conversations"}))
#                             # --------------------------------------------------------------------------

#                         elif message_type == "previous_conversations":
#                             self.previous_conversations_received.emit(message.get("conversations", {}))

#                         elif message_type == "new_message":
#                             is_self = message.get("message", {}).get('sender_username') == self.username
#                             if not is_self:
#                                 self.message_received.emit(message)

#                         elif message_type == "chat_message" and message.get("message_type") in ["image", "file"]:
#                              is_self = message.get('sender_username') == self.username
#                              self.file_message_received.emit(message, is_self)

#                         # --- NEW: Handle the server's response for a file download ---
#                         elif message_type == "file_download_response":
#                             file_path = message.get("file_path")
#                             if file_path in self.file_request_futures:
#                                 future = self.file_request_futures[file_path]
#                                 if not future.done():
#                                     if message.get("status") == "success":
#                                         # If successful, set the result of the future to the file data
#                                         future.set_result(message.get("file_data"))
#                                     else:
#                                         # If failed, raise an exception in the future
#                                         future.set_exception(Exception(message.get("message", "Unknown server error")))
            
#             except Exception as e:
#                 logger.error(f"WebSocket connection error: {e}")
#                 self.connection_lost.emit()
#                 await asyncio.sleep(5) # Wait before retrying

#     # --- NEW: Methods to manage file download requests ---
#     def request_file_data(self, file_path):
#         """Sends a download request to the server and returns a future."""
#         future = asyncio.Future()
#         self.file_request_futures[file_path] = future
        
#         request = {
#             "type": "request_file_download",
#             "file_path": file_path,
#             "token": self.auth_token # Authentication is crucial
#         }
#         # Safely run the async send operation from our sync Qt thread
#         asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps(request)), self.loop)
#         return future

#     def cleanup_file_request(self, file_path):
#         """Removes a download request future after it's been handled."""
#         if file_path in self.file_request_futures:
#             del self.file_request_futures[file_path]

#     def send_message(self, payload):
#         """Sends a JSON payload to the server."""
#         if self.websocket and self.loop:
#             asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps(payload)), self.loop)

#     def stop(self):
#         """Stops the WebSocket connection."""
#         self._should_stop = True
#         if self.loop:
#             self.loop.call_soon_threadsafe(self.loop.stop)
#         self.thread.quit()
#         self.thread.wait()


# # --- Main Backend Class (Connects UI to WebSocket and Download Logic) ---
# class HomePageBackend(QObject):
#     # Signals for the frontend UI
#     friend_list_requested = pyqtSignal()
#     display_message_signal = pyqtSignal(dict, bool)
#     display_conversations_signal = pyqtSignal(dict)

#     def __init__(self, token, session_id, parent=None):
#         super().__init__(parent)
#         self.current_user = None
#         self.current_chat_user = None
#         self.chat_histories = {}
        
#         # Setup WebSocket client
#         self.websocket_client = WebSocketClient(token, session_id)
        
#         # --- NEW: Initialize Download Manager ---
#         self.download_manager = DownloadManager(self.websocket_client)
        
#         self.connect_signals()
#         self.websocket_client.connect()

#     def connect_signals(self):
#         """Connect signals from WebSocket and Download Manager to handler slots."""
#         self.websocket_client.message_received.connect(self.handle_new_message)
#         self.websocket_client.previous_conversations_received.connect(self.handle_previous_conversations)
        
#         # --- NEW: Connect download manager signals ---
#         self.download_manager.download_complete.connect(self.on_download_complete)
#         self.download_manager.download_error.connect(self.on_download_error)

#     def set_user_info(self, user_info):
#         """Stores the current user's information."""
#         self.current_user = user_info
#         if self.websocket_client:
#             self.websocket_client.username = user_info.get("username")

#     @pyqtSlot(dict)
#     def handle_previous_conversations(self, conversations):
#         """Processes chat history received from the server."""
#         logger.info(f"📚 Received {len(conversations)} conversations from server.")
#         self.chat_histories = conversations
#         self.display_conversations_signal.emit(conversations)

#     @pyqtSlot(dict)
#     def handle_new_message(self, message_data):
#         """Handles a new incoming message."""
#         message = message_data.get("message", {})
#         sender = message.get("sender_username")
        
#         if sender not in self.chat_histories:
#             self.chat_histories[sender] = []
#         self.chat_histories[sender].append(message)
        
#         is_self = sender == self.current_user.get("username")
#         self.display_message_signal.emit(message, is_self)

#     # --- MODIFIED: This is now the central point for triggering a download ---
#     def download_file_clicked(self, message_data):
#         """
#         Handles the click event on a file or image message.
#         Opens a dialog to save the file and starts the download.
#         """
#         file_info = message_data.get('file_info', message_data) # Handle different message structures
#         file_name = file_info.get("file_name", "downloaded_file")
        
#         # Open the native "Save As..." dialog
#         save_path, _ = QFileDialog.getSaveFileName(None, "Save File", file_name)

#         if save_path:
#             # If the user chose a location, start the download
#             self.download_manager.start_download(file_info, save_path)
#             QMessageBox.information(None, "Download Started", f"Downloading {file_name}...")

#     # --- NEW: Slots to handle download results ---
#     @pyqtSlot(str, str)
#     def on_download_complete(self, file_path, local_save_path):
#         """Shows a success message when a download finishes."""
#         file_name = os.path.basename(local_save_path)
#         QMessageBox.information(None, "Download Complete", f"'{file_name}' has been saved successfully.")
#         logger.info(f"✅ Download complete: {file_path} -> {local_save_path}")

#     @pyqtSlot(str, str)
#     def on_download_error(self, file_path, error_message):
#         """Shows an error message if a download fails."""
#         QMessageBox.warning(None, "Download Failed", f"Could not download the file.\nError: {error_message}")
#         logger.error(f"❌ Download error for {file_path}: {error_message}")

#     def send_text_message(self, recipient_username, text):
#         """Sends a text message."""
#         payload = {
#             "type": "chat_message",
#             "recipient_id": recipient_username,
#             "message": text,
#             "message_type": "text"
#         }
#         self.websocket_client.send_message(payload)

#     def send_file_message(self, recipient_username, file_path):
#         """Reads a file, encodes it, and sends it."""
#         try:
#             with open(file_path, 'rb') as f:
#                 file_bytes = f.read()
            
#             file_data_b64 = base64.b64encode(file_bytes).decode('utf-8')
#             file_name = os.path.basename(file_path)
            
#             payload = {
#                 "type": "chat_message",
#                 "recipient_id": recipient_username,
#                 "message_type": "file", # or "image"
#                 "file_name": file_name,
#                 "file_data": file_data_b64,
#                 "file_size": len(file_bytes)
#             }
#             self.websocket_client.send_message(payload)
#         except Exception as e:
#             logger.error(f"Failed to send file: {e}")

#     def request_history(self, friend_username):
#         """Requests chat history for a specific friend."""
#         payload = {
#             "type": "request_conversation_history",
#             "friend_username": friend_username
#         }
#         self.websocket_client.send_message(payload)

import asyncio
import base64
import json
import logging
import os
import ssl
import websockets
from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot, Qt, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QFrame, QVBoxLayout

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Download Manager (Handles download logic) ---
class DownloadManager(QObject):
    """Manages file download operations."""
    download_complete = pyqtSignal(str, str)  # file_path, local_save_path
    download_error = pyqtSignal(str, str)    # file_path, error_message

    def __init__(self, websocket_client):
        super().__init__()
        self.websocket_client = websocket_client
        self.active_downloads = {}

    def start_download(self, file_info, save_path):
        """Initiates a file download request."""
        file_path = file_info.get("file_path")
        if not file_path:
            self.download_error.emit("", "File path is missing from message.")
            return

        print(f"📥 Requesting download for: {file_path} -> {save_path}")
        
        # Create a downloader thread to avoid freezing the UI
        downloader = FileDownloader(self.websocket_client, file_info, save_path)
        downloader.download_complete.connect(self.download_complete)
        downloader.download_error.connect(self.download_error)
        
        self.active_downloads[file_path] = downloader
        downloader.start()

class FileDownloader(QThread):
    """Worker thread to handle a single file download."""
    download_complete = pyqtSignal(str, str)
    download_error = pyqtSignal(str, str)

    def __init__(self, websocket_client, file_info, save_path):
        super().__init__()
        self.websocket_client = websocket_client
        self.file_info = file_info
        self.save_path = save_path

    def run(self):
        """Send download request and wait for the file data response."""
        file_path = self.file_info.get("file_path")
        
        # This function returns a "future" object that will eventually hold the result.
        future = self.websocket_client.request_file_data(file_path)
        
        try:
            # Wait for the file data to be received from the server (with a timeout)
            file_data_b64 = future.result(timeout=45) # 45-second timeout for larger files
            
            if file_data_b64:
                print(f"📦 Received file data for {file_path}, decoding and saving...")
                # Decode the base64 data and write it to the chosen file path
                file_bytes = base64.b64decode(file_data_b64)
                with open(self.save_path, 'wb') as f:
                    f.write(file_bytes)
                print(f"✅ Successfully saved to {self.save_path}")
                self.download_complete.emit(file_path, self.save_path)
            else:
                self.download_error.emit(file_path, "No data received from server.")

        except asyncio.TimeoutError:
            self.download_error.emit(file_path, "Download request timed out.")
        except Exception as e:
            self.download_error.emit(file_path, f"An error occurred: {str(e)}")
        finally:
            # Clean up the request from the websocket client
            self.websocket_client.cleanup_file_request(file_path)


# --- WebSocket Client (Handles communication with the server) ---
class WebSocketClient(QObject):
    """Handles all WebSocket communication for the home page."""
    # Signals to communicate with the main UI
    connection_established = pyqtSignal()
    connection_lost = pyqtSignal()
    previous_conversations_received = pyqtSignal(dict)
    message_received = pyqtSignal(dict)
    file_message_received = pyqtSignal(dict, bool)

    def __init__(self, token, session_id):
        super().__init__()
        self.auth_token = token
        self.session_id = session_id
        self.websocket = None
        self.loop = None
        self._should_stop = False
        self.username = ""
        # NEW: Dictionary to track pending file download requests
        self.file_request_futures = {}

    def connect(self):
        """Starts the WebSocket connection thread."""
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self._run_async_loop)
        self.thread.start()

    def _run_async_loop(self):
        """Initializes and runs the asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.listen())

    async def listen(self):
        """The main loop that connects and listens for messages."""
        uri = "wss://localhost:8443"
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        while not self._should_stop:
            try:
                async with websockets.connect(uri, ssl=ssl_context, max_size=10 * 1024 * 1024) as websocket:
                    self.websocket = websocket
                    self.connection_established.emit()
                    
                    # Authenticate upon connection
                    auth_payload = {"token": self.auth_token, "session_id": self.session_id}
                    await self.websocket.send(json.dumps(auth_payload))

                    # Listen for messages
                    async for message_json in self.websocket:
                        message = json.loads(message_json)
                        message_type = message.get("type")

                        if message_type == "auth_success":
                            self.username = message.get("user", {}).get("username")
                            logger.info(f"Authenticated as {self.username}")
                            
                            # --- FIX: Proactively request chat history after successful authentication ---
                            logger.info("✅ Authentication successful. Requesting previous conversations...")
                            await self.websocket.send(json.dumps({"type": "get_previous_conversations"}))
                            # --------------------------------------------------------------------------

                        elif message_type == "previous_conversations":
                            self.previous_conversations_received.emit(message.get("conversations", {}))

                        elif message_type == "new_message":
                            is_self = message.get("message", {}).get('sender_username') == self.username
                            if not is_self:
                                self.message_received.emit(message)

                        elif message_type == "chat_message" and message.get("message_type") in ["image", "file"]:
                             is_self = message.get('sender_username') == self.username
                             self.file_message_received.emit(message, is_self)

                        # --- NEW: Handle the server's response for a file download ---
                        elif message_type == "file_download_response":
                            file_path = message.get("file_path")
                            if file_path in self.file_request_futures:
                                future = self.file_request_futures[file_path]
                                if not future.done():
                                    if message.get("status") == "success":
                                        # If successful, set the result of the future to the file data
                                        future.set_result(message.get("file_data"))
                                    else:
                                        # If failed, raise an exception in the future
                                        future.set_exception(Exception(message.get("message", "Unknown server error")))
            
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                self.connection_lost.emit()
                await asyncio.sleep(5) # Wait before retrying

    # --- NEW: Methods to manage file download requests ---
    def request_file_data(self, file_path):
        """Sends a download request to the server and returns a future."""
        future = asyncio.Future()
        self.file_request_futures[file_path] = future
        
        request = {
            "type": "request_file_download",
            "file_path": file_path,
            "token": self.auth_token # Authentication is crucial
        }
        # Safely run the async send operation from our sync Qt thread
        asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps(request)), self.loop)
        return future

    def cleanup_file_request(self, file_path):
        """Removes a download request future after it's been handled."""
        if file_path in self.file_request_futures:
            del self.file_request_futures[file_path]

    def send_message(self, payload):
        """Sends a JSON payload to the server."""
        if self.websocket and self.loop:
            asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps(payload)), self.loop)

    def stop(self):
        """Stops the WebSocket connection."""
        self._should_stop = True
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.quit()
        self.thread.wait()


# --- Main Backend Class (Connects UI to WebSocket and Download Logic) ---
class HomePageBackend(QObject):
    # Signals for the frontend UI
    friend_list_requested = pyqtSignal()
    display_message_signal = pyqtSignal(dict, bool)
    display_conversations_signal = pyqtSignal(dict)

    def __init__(self, token, session_id, parent=None):
        super().__init__(parent)
        self.current_user = None
        self.current_chat_user = None
        self.chat_histories = {}
        
        # Setup WebSocket client
        self.websocket_client = WebSocketClient(token, session_id)
        
        # --- NEW: Initialize Download Manager ---
        self.download_manager = DownloadManager(self.websocket_client)
        
        self.connect_signals()
        self.websocket_client.connect()

    def connect_signals(self):
        """Connect signals from WebSocket and Download Manager to handler slots."""
        self.websocket_client.message_received.connect(self.handle_new_message)
        self.websocket_client.previous_conversations_received.connect(self.handle_previous_conversations)
        
        # --- NEW: Connect download manager signals ---
        self.download_manager.download_complete.connect(self.on_download_complete)
        self.download_manager.download_error.connect(self.on_download_error)

    def set_user_info(self, user_info):
        """Stores the current user's information."""
        self.current_user = user_info
        if self.websocket_client:
            self.websocket_client.username = user_info.get("username")

    @pyqtSlot(dict)
    def handle_previous_conversations(self, conversations):
        """Processes chat history received from the server."""
        logger.info(f"📚 Received {len(conversations)} conversations from server.")
        self.chat_histories = conversations
        self.display_conversations_signal.emit(conversations)

    @pyqtSlot(dict)
    def handle_new_message(self, message_data):
        """Handles a new incoming message."""
        message = message_data.get("message", {})
        sender = message.get("sender_username")
        
        if sender not in self.chat_histories:
            self.chat_histories[sender] = []
        self.chat_histories[sender].append(message)
        
        is_self = sender == self.current_user.get("username")
        self.display_message_signal.emit(message, is_self)

    # --- MODIFIED: This is now the central point for triggering a download ---
    def download_file_clicked(self, message_data):
        """
        Handles the click event on a file or image message.
        Opens a dialog to save the file and starts the download.
        """
        file_info = message_data.get('file_info', message_data) # Handle different message structures
        file_name = file_info.get("file_name", "downloaded_file")
        
        # Open the native "Save As..." dialog
        save_path, _ = QFileDialog.getSaveFileName(None, "Save File", file_name)

        if save_path:
            # If the user chose a location, start the download
            self.download_manager.start_download(file_info, save_path)
            QMessageBox.information(None, "Download Started", f"Downloading {file_name}...")

    # --- NEW: Slots to handle download results ---
    @pyqtSlot(str, str)
    def on_download_complete(self, file_path, local_save_path):
        """Shows a success message when a download finishes."""
        file_name = os.path.basename(local_save_path)
        QMessageBox.information(None, "Download Complete", f"'{file_name}' has been saved successfully.")
        logger.info(f"✅ Download complete: {file_path} -> {local_save_path}")

    @pyqtSlot(str, str)
    def on_download_error(self, file_path, error_message):
        """Shows an error message if a download fails."""
        QMessageBox.warning(None, "Download Failed", f"Could not download the file.\nError: {error_message}")
        logger.error(f"❌ Download error for {file_path}: {error_message}")

    def send_text_message(self, recipient_username, text):
        """Sends a text message."""
        payload = {
            "type": "chat_message",
            "recipient_id": recipient_username,
            "message": text,
            "message_type": "text"
        }
        self.websocket_client.send_message(payload)

    def send_file_message(self, recipient_username, file_path):
        """Reads a file, encodes it, and sends it."""
        try:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            file_data_b64 = base64.b64encode(file_bytes).decode('utf-8')
            file_name = os.path.basename(file_path)
            
            payload = {
                "type": "chat_message",
                "recipient_id": recipient_username,
                "message_type": "file", # or "image"
                "file_name": file_name,
                "file_data": file_data_b64,
                "file_size": len(file_bytes)
            }
            self.websocket_client.send_message(payload)
        except Exception as e:
            logger.error(f"Failed to send file: {e}")

    def request_history(self, friend_username):
        """Requests chat history for a specific friend."""
        payload = {
            "type": "request_conversation_history",
            "friend_username": friend_username
        }
        self.websocket_client.send_message(payload)

