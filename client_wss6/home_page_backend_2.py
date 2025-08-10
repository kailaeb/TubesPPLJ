import json
import asyncio
import websockets
from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
import ssl
from typing import Dict, List, Optional


class HomePageBackend(QObject):
    """Pure WebSocket-based backend client for chat functionality"""
    
    # Signals for frontend communication
    connection_established = pyqtSignal()
    connection_lost = pyqtSignal(str)
    message_received = pyqtSignal(dict)  # New message from another user
    message_sent = pyqtSignal(dict)     # Confirmation message was sent
    chat_history_received = pyqtSignal(list)  # Chat history data
    friends_list_received = pyqtSignal(list)  # Friends list data
    friend_added = pyqtSignal(dict)     # Friend successfully added
    friend_status_changed = pyqtSignal(dict)  # Friend online/offline status
    error_occurred = pyqtSignal(str)    # Error messages
    
    def __init__(self, auth_token=None, user_data=None):
        super().__init__()
        self.auth_token = auth_token
        self.current_user = user_data or {}
        self.is_connected = False
        self.websocket_thread = None
        
        # Server configuration - WebSocket only
        self.SERVER_HOST = "localhost"
        self.SERVER_PORT = 8443
        self.SERVER_WSS_URL = f"wss://{self.SERVER_HOST}:{self.SERVER_PORT}/"
        
        print(f"🔧 Home Page Backend initialized (Pure WebSocket)")
        print(f"🎯 Target server: {self.SERVER_WSS_URL}")
        print(f"👤 Current user: {self.current_user.get('username', 'Unknown')}")
    
    def connect_to_server(self):
        """Establish authenticated WebSocket connection for real-time chat"""
        if not self.auth_token:
            self.error_occurred.emit("No authentication token available")
            return
        
        print("🔌 Connecting to WebSocket server for real-time chat...")
        
        self.websocket_thread = AuthenticatedWebSocketThread(
            self.SERVER_WSS_URL,
            self.auth_token,
            self.current_user
        )
        
        # Connect all signals
        self.websocket_thread.connection_established.connect(self.handle_connection_established)
        self.websocket_thread.connection_lost.connect(self.handle_connection_lost)
        self.websocket_thread.message_received.connect(self.handle_message_received)
        self.websocket_thread.response_received.connect(self.handle_server_response)
        self.websocket_thread.error_occurred.connect(self.handle_websocket_error)
        
        self.websocket_thread.start()
    
    @pyqtSlot()
    def handle_connection_established(self):
        """Handle successful WebSocket connection"""
        print("✅ WebSocket connection established")
        self.is_connected = True
        self.connection_established.emit()
        
        # Request initial data
        self.request_friends_list()
    
    @pyqtSlot(str)
    def handle_connection_lost(self, reason):
        """Handle lost WebSocket connection"""
        print(f"❌ WebSocket connection lost: {reason}")
        self.is_connected = False
        self.connection_lost.emit(reason)
    
    @pyqtSlot(dict)
    def handle_message_received(self, message_data):
        """Handle incoming message from another user"""
        print(f"📨 New message received: {message_data}")
        self.message_received.emit(message_data)
    
    @pyqtSlot(dict)
    def handle_server_response(self, response_data):
        """Handle various server responses"""
        response_type = response_data.get("type")
        
        if response_type == "message_sent":
            self.message_sent.emit(response_data)
        elif response_type == "chat_history":
            self.chat_history_received.emit(response_data.get("messages", []))
        elif response_type == "friends_list":
            self.friends_list_received.emit(response_data.get("friends", []))
        elif response_type == "friend_added":
            self.friend_added.emit(response_data)
        elif response_type == "friend_status":
            self.friend_status_changed.emit(response_data)
        elif response_type == "previous_conversations":
            conversations = response_data.get("conversations", [])
    # Process conversations and extract chat history
            self.process_previous_conversations(conversations)
        elif response_type == "error":
            self.error_occurred.emit(response_data.get("message", "Unknown error"))
        else:
            print(f"🤷 Unhandled server response: {response_data}")
    
    @pyqtSlot(str)
    def handle_websocket_error(self, error_message):
        """Handle WebSocket errors"""
        print(f"❌ WebSocket error: {error_message}")
        self.error_occurred.emit(error_message)
    


    def process_previous_conversations(self, conversations):
        """Process previous conversations from server"""
        print(f"📨 Received {len(conversations)} previous conversations")
    
    # You'll need to process the conversations dict structure
    # and emit chat_history_received for specific friends
        for room_id, messages in conversations.items():
            if messages:
            # Extract the other participant from the conversation
                first_message = messages[0]
                sender_id = first_message.get("sender_id")
                recipient_id = first_message.get("recipient_id")
            
            # Determine who the chat partner is
                current_user_id = self.current_user.get("user_id")
                chat_partner_id = recipient_id if sender_id == current_user_id else sender_id
            
            # Emit chat history for this specific partner
                self.chat_history_received.emit({
                    "chat_partner_id": chat_partner_id,
                    "messages": messages,
                    "room_id": room_id
                })
    
    def send_message(self, recipient_id: str, message_text: str):
        """Send a message to another user by recipient_id."""
        if not self.is_connected:
            self.error_occurred.emit("Not connected to server")
            return
    
        if not recipient_id.strip() or not message_text.strip():
            self.error_occurred.emit("Username and message cannot be empty")
            return
    
        message_data = {
            "recipient_id": recipient_id,
             "message": message_text
        }
    
        print(f"📤 Sending message to recipient {recipient_id}: {message_text[:50]}...")
        self.websocket_thread.send_message(message_data)

    
    def request_chat_history(self, with_username: str, limit: int = 100):
        """Request chat history with a specific user"""
        if not self.is_connected:
            self.error_occurred.emit("Not connected to server")
            return
        
        request_data = {
            "type": "get_chat_history",
            "with_username": with_username,
            "limit": limit
        }
        
        print(f"📤 Requesting chat history with {with_username}")
        self.websocket_thread.send_message(request_data)
    
    def request_friends_list(self):
        """Request current user's friends list"""
        if not self.is_connected:
            self.error_occurred.emit("Not connected to server")
            return
        
        request_data = {
            "type": "get_friends_list"
        }
        
        print("📤 Requesting friends list")
        self.websocket_thread.send_message(request_data)
    
    def add_friend(self, friend_username: str):
        """Add a new friend"""
        if not self.is_connected:
            self.error_occurred.emit("Not connected to server")
            return
        
        if not friend_username.strip():
            self.error_occurred.emit("Friend username cannot be empty")
            return
        
        request_data = {
            "type": "add_friend",
            "friend_username": friend_username
        }
        
        print(f"📤 Adding friend: {friend_username}")
        self.websocket_thread.send_message(request_data)
    
    def disconnect_from_server(self):
        """Clean up WebSocket connections"""
        print("🔌 Disconnecting from WebSocket server...")
        
        if self.websocket_thread and self.websocket_thread.isRunning():
            self.websocket_thread.stop()
            self.websocket_thread.wait(3000)
        
        self.is_connected = False
        print("✅ Disconnected from WebSocket server")
    
    def set_server_config(self, host, port=8443):
        """Update server configuration"""
        self.SERVER_HOST = host
        self.SERVER_PORT = port
        self.SERVER_WSS_URL = f"wss://{host}:{port}/"
        print(f"🔧 Server config updated: {self.SERVER_WSS_URL}")


class AuthenticatedWebSocketThread(QThread):
    """Thread for maintaining authenticated WebSocket connection"""
    
    connection_established = pyqtSignal()
    connection_lost = pyqtSignal(str)
    message_received = pyqtSignal(dict)
    response_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, websocket_url, auth_token, user_data):
        super().__init__()
        self.websocket_url = websocket_url
        self.auth_token = auth_token
        self.user_data = user_data
        self.should_stop = False
        self.websocket = None
        self.message_queue = asyncio.Queue()
    
    def run(self):
        """Main WebSocket connection loop"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.websocket_loop())
        except Exception as e:
            self.error_occurred.emit(f"WebSocket thread error: {str(e)}")
        finally:
            try:
                loop.close()
            except:
                pass
    
    async def websocket_loop(self):
        """Main WebSocket connection and message handling loop"""
        try:
            # Create custom SSL context for self-signed certificate
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with websockets.connect(
                self.websocket_url,
                extra_headers={"Authorization": f"Bearer {self.auth_token}"},
                ping_interval=30,
                ping_timeout=10,
                ssl=ssl_context
            ) as websocket:
                                
                self.websocket = websocket

                # Send authentication message first
                # WITH THIS:
                auth_message = {
                    "token": self.auth_token,
                    "session_id": "home_chat"  # Server uses this to identify connection type
                }
                
                await websocket.send(json.dumps(auth_message))
                print("📤 Sent authentication message")
                                
                # Wait for authentication confirmation
                auth_response = await websocket.recv()
                auth_data = json.loads(auth_response)
                                
                if auth_data.get("type") == "auth_success":
                    print("✅ Authentication successful")
                    self.connection_established.emit()
                                
                    # Handle messages
                    await asyncio.gather(
                        self.message_sender(), 
                        self.message_receiver()
                    )
                else:
                    error_msg = auth_data.get("message", "Authentication failed")
                    self.error_occurred.emit(error_msg)
                                
        except Exception as e:
            if not self.should_stop:
                self.error_occurred.emit(f"WebSocket error: {str(e)}")
                self.connection_lost.emit(str(e))
    
    
    async def message_sender(self):
        """Send messages from the message queue."""
        try:
            while not self.should_stop and self.websocket:
                try:
                    message = await asyncio.wait_for(
                        self.message_queue.get(), 
                        timeout=1.0
                    )
                    if self.websocket and not self.websocket.close:
                        await self.websocket.send(json.dumps(message))
                        print(f"📤 Sent message: {message.get('type')}")
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"❌ Error sending message: {e}")

        except Exception as e:
            self.error_occurred.emit(f"Message sender error: {str(e)}")

    async def message_receiver(self):
        """Receive messages from WebSocket server."""
        try:
            while not self.should_stop and self.websocket:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=1.0
                    )
                    message_data = json.loads(message)
                    message_type = message_data.get("type")

                    print(f"📨 Received message: {message_type}")

                    if message_type == "new_message":
                        self.message_received.emit(message_data)
                    else:
                        self.response_received.emit(message_data)

                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    if not self.should_stop:
                        self.connection_lost.emit("WebSocket connection closed.")
                    break
                except Exception as e:
                    print(f"❌ Error receiving message: {e}")

        except Exception as e:
            self.error_occurred.emit(f"Message receiver error: {str(e)}")

    
    def send_message(self, message_data):
        """Thread-safe message sending."""
        if not self.loop or not self.loop.is_running():
            print("❌ Loop not running")
            return

        asyncio.run_coroutine_threadsafe(
            self.message_queue.put(message_data), 
            self.loop
        )

    def stop(self):
        """Stop the WebSocket thread gracefully."""
        print("🛑 Stopping WebSocket thread...")
        self.should_stop = True

        if self.websocket and not self.websocket.closed:
            asyncio.run_coroutine_threadsafe(
                self.websocket.close(), 
                self.loop
            )