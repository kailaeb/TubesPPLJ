import json
import asyncio
from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
import websockets
import ssl, time
from datetime import datetime

class FriendListBackend(QObject):
    """WebSocket-based backend for friend list management"""
    
    # Signals for frontend communication
    connection_established = pyqtSignal()
    connection_failed = pyqtSignal(str)
    friends_loaded = pyqtSignal(list)  # Emit list of friend objects
    friend_added = pyqtSignal(dict)  # Emit friend object when added
    error_occurred = pyqtSignal(str)
    
    # NEW: Signal for forwarding conversations to home page
    conversations_received = pyqtSignal(dict)  # Emit processed conversations
    
    def __init__(self, auth_token=None):
        super().__init__()
        self.is_connected = False
        self.auth_token = auth_token
        self.websocket = None
        self.websocket_thread = None
        
        # Server configuration - WebSocket URL without /websocket endpoint
        self.SERVER_HOST = "localhost"
        self.SERVER_PORT = 8443
        self.SERVER_WSS_URL = f"wss://{self.SERVER_HOST}:{self.SERVER_PORT}"
        
        print(f"🔧 Friend List Backend initialized (WebSocket)")
        print(f"🎯 Server: {self.SERVER_WSS_URL}")
    
    def set_auth_token(self, token):
        """Set authentication token after login"""
        self.auth_token = token
        print(f"🔑 Auth token set for friend list: {token[:20]}..." if token else "No token")
        
        # Auto-connect if we have a token
        if token and not self.is_connected:
            print("🔄 Auto-connecting with new token...")
            self.connect_to_server()
    
    
    def connect_to_server(self):
        """Connect to WebSocket server"""
        print("🔌 Connecting to WebSocket server...")
        
        if not self.auth_token:
            print("❌ No authentication token available")
            self.connection_failed.emit("No authentication token available")
            return
        
        # Start WebSocket connection in separate thread
        self.websocket_thread = WebSocketThread(self.SERVER_WSS_URL, self.auth_token)
        self.websocket_thread.connection_established.connect(self.handle_connection_established)
        self.websocket_thread.connection_failed.connect(self.handle_connection_failed)
        # In your friend_list_backend.py setup_backend_connections():
        self.websocket_thread.message_received.connect(self.handle_websocket_message)
        self.websocket_thread.start()
    
    @pyqtSlot()
    def handle_connection_established(self):
        """Handle successful WebSocket connection"""
        print(f"✅ WebSocket connection established")
        self.is_connected = True
        self.websocket = self.websocket_thread.websocket
        self.connection_established.emit()
    
    @pyqtSlot(str)
    def handle_connection_failed(self, error_message):
        """Handle failed WebSocket connection"""
        print(f"❌ WebSocket connection failed: {error_message}")
        self.is_connected = False
        self.connection_failed.emit(error_message)
    
    @pyqtSlot(dict)
    def handle_websocket_message(self, message):
        """Handle incoming WebSocket messages"""
        message_type = message.get('type')
        
        if message_type == 'friends_list_response':
            self.handle_friends_list_response(message)
        elif message_type == 'add_friend_response':
            self.handle_add_friend_response(message)
        # elif message_type == 'previous_conversations':
        #     # NEW: Handle previous conversations and forward to home page
        #     self.handle_previous_conversations(message)
        elif message_type == 'error':
            self.error_occurred.emit(message.get('message', 'Unknown error'))
        else:
            print(f"📨 Received unhandled message: {message}")

    
    def format_timestamp(self, iso_timestamp):
        """Convert ISO timestamp to display format"""
        try:
            if iso_timestamp:
                dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
                return dt.strftime("%H:%M")
            return "00:00"
        except Exception as e:
            print(f"❌ Error formatting timestamp {iso_timestamp}: {e}")
            return "00:00"
    
    def handle_friends_list_response(self, message):
        """Handle friends list response from server"""
        if message.get('status') == 'success':
            friends_data = message.get('friends', [])
            
            # Convert to friend objects format expected by UI
            friends_list = []
            for friend in friends_data:
                friend_obj = {
                    'user_id': friend.get('user_id'),
                    'username': friend.get('username'),
                    'display_name': friend.get('username'),
                    'status': 'online',  # Default status
                    'created_at': friend.get('created_at', '')
                }
                friends_list.append(friend_obj)
            
            print(f"✅ Friends list loaded: {len(friends_list)} friends")
            self.friends_loaded.emit(friends_list)
        else:
            error_msg = message.get('message', 'Failed to load friends')
            print(f"❌ Load friends failed: {error_msg}")
            self.error_occurred.emit(error_msg)
    

    def handle_add_friend_response(self, message):
        """Handle add friend response from server"""
        if message.get('status') == 'success':
            friend_data = {
                'username': message.get('username', 'Unknown'),
                'display_name': message.get('username', 'Unknown'),
                'status': 'online'
            }
            print(f"✅ Friend added successfully: {friend_data['username']}")
            self.friend_added.emit(friend_data)
            self.load_friends_list()
        else:
            error_msg = message.get('message', 'Failed to add friend')
            print(f"❌ Add friend failed: {error_msg}")
            self.error_occurred.emit(error_msg)

    
    def load_friends_list(self):
        """Load friends list from server via WebSocket"""
        if not self.is_connected:
            self.error_occurred.emit("Not connected to server")
            return
        
        print("📋 Requesting friends list from server...")
        
        message = {
            'type': 'get_friends_list',
            'timestamp': int(asyncio.get_event_loop().time()) if asyncio.get_event_loop().is_running() else 0
        }
        
        self.send_websocket_message(message)
    
    def add_friend(self, username):
        """Add friend by username via WebSocket"""
        if not self.is_connected:
            self.error_occurred.emit("Not connected to server")
            return
        
        print(f"👥 Adding friend: {username}")
        
        message = {
            'type': 'add_friend',
            'username': username,
            'timestamp': int(asyncio.get_event_loop().time()) if asyncio.get_event_loop().is_running() else 0
        }
        
        self.send_websocket_message(message)
    
    def send_websocket_message(self, message):
        """Send message via WebSocket"""
        if self.websocket_thread and self.is_connected:
            self.websocket_thread.send_message(message)
        else:
            self.error_occurred.emit("WebSocket not connected")
    
    def disconnect_from_server(self):
        """Clean up WebSocket connection"""
        self.is_connected = False
        if self.websocket_thread:
            self.websocket_thread.stop()
            self.websocket_thread.wait()
        print("✅ Friend list backend disconnected")


class WebSocketThread(QThread):
    """Thread to handle WebSocket connection and communication"""
    
    connection_established = pyqtSignal()
    connection_failed = pyqtSignal(str)
    message_received = pyqtSignal(dict)
    
    def __init__(self, websocket_url, auth_token):
        super().__init__()
        self.websocket_url = websocket_url
        self.auth_token = auth_token
        self.websocket = None
        self.running = False
        
    def run(self):
        """Main thread execution"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create message queue in the correct event loop
            self.message_queue = asyncio.Queue()
            
            loop.run_until_complete(self.connect_and_listen())
        except Exception as e:
            self.connection_failed.emit(str(e))
        finally:
            try:
                loop.close()
            except:
                pass
    
    async def connect_and_listen(self):
        """Connect to WebSocket and listen for messages"""
        try:
            # Create SSL context for WSS
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            print(f"🔗 Connecting to: {self.websocket_url}")
            
            # Connect to WebSocket
            async with websockets.connect(
                self.websocket_url,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=10
            ) as websocket:
                self.websocket = websocket
                self.running = True
                
                # Send authentication (matching your server's expected format)
                auth_message = {
                    'token': self.auth_token,
                    'session_id': f'auto_friends_client_{int(time.time())}',   # This will skip auto-friends
                    #'connection_type': 'search'  # Optional: explicit type
                }
                print(f"📤 Sending auth: {self.auth_token[:20]}...")
                await websocket.send(json.dumps(auth_message))
                
                # Wait for authentication response
                auth_response = await websocket.recv()
                auth_data = json.loads(auth_response)
                print(f"📨 Auth response: {auth_data}")
                
                if auth_data.get('type') == 'auth_success':
                    self.connection_established.emit()
                    
                    # Start message handling tasks
                    await asyncio.gather(
                        self.listen_for_messages(),
                        self.send_queued_messages()
                    )
                else:
                    error_msg = auth_data.get('error', 'Authentication failed')
                    self.connection_failed.emit(error_msg)
                    
        except websockets.exceptions.ConnectionClosed:
            self.connection_failed.emit("WebSocket connection closed")
        except Exception as e:
            self.connection_failed.emit(f"WebSocket error: {str(e)}")
    
    async def listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        try:
            while self.running and self.websocket:
                message = await self.websocket.recv()
                try:
                    data = json.loads(message)
                    print(f"📨 Received: {data}")
                    self.message_received.emit(data)
                except json.JSONDecodeError:
                    print(f"⚠️ Received invalid JSON: {message}")
        except websockets.exceptions.ConnectionClosed:
            print("🔌 WebSocket connection closed")
            self.running = False
        except Exception as e:
            print(f"❌ Error listening for messages: {e}")
            self.running = False
    
    async def send_queued_messages(self):
        """Send queued messages to WebSocket"""
        try:
            while self.running and self.websocket:
                try:
                    # Wait for a message to send (with timeout)
                    message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                    await self.websocket.send(json.dumps(message))
                    print(f"📤 Sent WebSocket message: {message}")
                except asyncio.TimeoutError:
                    # No message to send, continue
                    continue
                except Exception as e:
                    print(f"❌ Error sending message: {e}")
                    break
        except Exception as e:
            print(f"❌ Error in send queue: {e}")
    
    def send_message(self, message):
        """Queue a message to be sent"""
        try:
            # Check if we have a valid event loop and queue
            if hasattr(self, 'message_queue') and self.message_queue:
                # Get the event loop from this thread
                loop = asyncio.get_event_loop()
                if loop and not loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        self.message_queue.put(message), 
                        loop
                    )
                else:
                    print(f"❌ No valid event loop for sending message")
            else:
                print(f"❌ No message queue available")
        except Exception as e:
            print(f"❌ Error queuing message: {e}")
    
    def stop(self):
        """Stop the WebSocket thread"""
        self.running = False
        if self.websocket:
            try:
                # Create a new event loop to close the websocket
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.websocket.close())
                loop.close()
            except:
                pass