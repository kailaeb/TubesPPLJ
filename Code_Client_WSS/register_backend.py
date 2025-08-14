import json
import hashlib
import asyncio
from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
import websockets
import ssl


class RegisterBackend(QObject):
    """WebSocket-based backend client for registration"""
    
    # Signals for frontend communication
    connection_established = pyqtSignal()
    connection_failed = pyqtSignal(str)
    register_response = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_connected = False
        self.websocket_thread = None
        
        # Server configuration - WebSocket endpoint
        self.SERVER_HOST = "localhost"
        self.SERVER_PORT = 8443
        self.SERVER_WSS_URL = f"wss://{self.SERVER_HOST}:{self.SERVER_PORT}/"
        
        print(f"🔧 Register Backend client initialized (WebSocket)")
        print(f"🎯 Target server: {self.SERVER_WSS_URL}")
    
    def connect_to_server(self):
        """Test WebSocket connection to server"""
        print("🔌 Testing WebSocket connection to server...")
       
        self.test_thread = TestConnectionThread(self.SERVER_WSS_URL)
        self.test_thread.connection_result.connect(self.handle_test_connection)
        self.test_thread.start()
    
    @pyqtSlot(bool, str)
    def handle_test_connection(self, success, message):
        """Handle test connection result"""
        if success:
            print(f"✅ WebSocket server connection verified: {message}")
            self.is_connected = True
            self.connection_established.emit()
        else:
            print(f"❌ WebSocket server connection failed: {message}")
            self.is_connected = False
            self.connection_failed.emit(message)
    
    def disconnect_from_server(self):
        """Clean up WebSocket connections"""
        print("🔌 Cleaning up WebSocket connections...")
        
        if self.websocket_thread and self.websocket_thread.isRunning():
            self.websocket_thread.stop()
            self.websocket_thread.wait(3000)
        
        if hasattr(self, 'test_thread') and self.test_thread.isRunning():
            self.test_thread.stop()
            self.test_thread.wait(1000)
        
        self.is_connected = False
        print("✅ Disconnected from WebSocket server")
    
    def hash_password(self, password):
        """Hash password using SHA256 (though server uses plain text)"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def send_register_request(self, username, password):
        """Send registration request to server via WebSocket"""
        if not self.is_connected:
            self.error_occurred.emit("Not connected to server. Please wait for connection.")
            return
    
        if not username.strip() or not password:
            self.error_occurred.emit("Username and password are required")
            return
    
        if len(password) < 8:
            self.error_occurred.emit("Password must be at least 8 characters")
            return
    
        self._last_username = username
    
    # Hash the password before sending (SECURITY FIX)
        hashed_password = self.hash_password(password)
    
        print(f"📤 Sending WebSocket registration request for user: {username}")
        print(f"🔒 Password hashed: {password[:2]}... -> {hashed_password[:10]}...")
    
    # Send WebSocket registration request with hashed password
        self.websocket_thread = WebSocketRegisterThread(
            self.SERVER_WSS_URL,
            username,
            hashed_password  # Send hashed password for security
        )
        self.websocket_thread.register_result.connect(self.handle_register_result)
        self.websocket_thread.start()
    
    @pyqtSlot(bool, dict, str)
    def handle_register_result(self, success, response_data, error_message):
        """Handle WebSocket registration result"""
        if success:
            print(f"✅ Registration successful for {response_data.get('user', {}).get('username')}")
            
            # Emit success response to frontend
            final_response = {
                "status": "success",
                "message": response_data.get("message", "Registration successful"),
                "user": response_data.get("user", {}),
                "token": response_data.get("token"),
                "session_id": response_data.get("session_id"),
                "username": response_data.get("user", {}).get("username", self._last_username)
            }
            self.register_response.emit(final_response)
            
        else:
            print(f"❌ Registration failed: {error_message}")
            self.register_response.emit({
                "status": "error",
                "message": error_message
            })
    
    def set_server_config(self, host, port=8443):
        """Update server configuration"""
        self.SERVER_HOST = host
        self.SERVER_PORT = port
        self.SERVER_WSS_URL = f"wss://{host}:{port}"
        print(f"🔧 Server config updated: {self.SERVER_WSS_URL}")


class TestConnectionThread(QThread):
    """Thread to test if WebSocket server is available"""
    
    connection_result = pyqtSignal(bool, str)
    
    def __init__(self, websocket_url):
        super().__init__()
        self.websocket_url = websocket_url
        self.should_stop = False
    
    def run(self):
        """Test WebSocket connection to server"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.test_connection())
        except Exception as e:
            self.connection_result.emit(False, f"Test failed: {str(e)}")
        finally:
            try:
                loop.close()
            except:
                pass
    
    async def test_connection(self):
        """Quick WebSocket connection test"""
        try:
            # Create SSL context that ignores certificate errors (for self-signed certs)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Test WebSocket connection with short timeout
            async with websockets.connect(
                self.websocket_url,
                ssl=ssl_context,
                ping_interval=None,  # Disable ping for test
                close_timeout=2
            ) as websocket:
                # Send a test message (server expects auth, but we just want to test connection)
                test_message = {"type": "connection_test"}
                await websocket.send(json.dumps(test_message))
                
                # Try to receive a response (may be an error, but connection works)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    self.connection_result.emit(True, "WebSocket server is running")
                except asyncio.TimeoutError:
                    # No response, but connection was established
                    self.connection_result.emit(True, "WebSocket server is running")
                        
        except websockets.exceptions.ConnectionClosed:
            self.connection_result.emit(False, "WebSocket connection closed by server")
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 426:  # Upgrade Required - means server is there but wrong protocol
                self.connection_result.emit(False, "Server found but doesn't support WebSocket")
            else:
                self.connection_result.emit(False, f"WebSocket server returned status {e.status_code}")
        except OSError as e:
            if "Connection refused" in str(e):
                self.connection_result.emit(False, "WebSocket server is not running")
            else:
                self.connection_result.emit(False, f"Connection error: {str(e)}")
        except Exception as e:
            self.connection_result.emit(False, f"Connection test failed: {str(e)}")
    
    def stop(self):
        """Stop the test thread"""
        self.should_stop = True


class WebSocketRegisterThread(QThread):
    """Thread for WebSocket registration"""
    
    register_result = pyqtSignal(bool, dict, str)  # success, response_data, error_message
    
    def __init__(self, websocket_url, username, hashed_password):
        super().__init__()
        self.websocket_url = websocket_url
        self.username = username
        self.hashed_password = hashed_password
        self.should_stop = False
    
    def run(self):
        """Perform WebSocket registration"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.register())
        except Exception as e:
            self.register_result.emit(False, {}, f"Registration error: {str(e)}")
        finally:
            try:
                loop.close()
            except:
                pass
    
    async def register(self):
        """Send WebSocket registration request"""
        try:
            # Create SSL context that ignores certificate errors
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with websockets.connect(
                self.websocket_url,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=10
            ) as websocket:
                
                # Send registration request as the first message
                # Note: This requires server modification to handle unauthenticated registration
                register_data = {
                    "type": "register",  # Special registration message type
                    "username": self.username,
                    "password": self.hashed_password,
                    "action": "register"  # Make it clear this is a registration attempt
                }
                
                print(f"📤 Sending WebSocket registration data: {json.dumps({**register_data, 'password': '***'})}")
                
                await websocket.send(json.dumps(register_data))
                
                # Wait for registration response
                try:
                    response_text = await asyncio.wait_for(websocket.recv(), timeout=10)
                    response_data = json.loads(response_text)
                    
                    print(f"📨 WebSocket server response: {response_data}")
                    
                    # Check if registration was successful
                    if response_data.get("type") == "register_response":
                        if response_data.get("status") == "success":
                            self.register_result.emit(True, response_data, "")
                        else:
                            error_msg = response_data.get("message", "Registration failed")
                            self.register_result.emit(False, {}, error_msg)
                    elif response_data.get("error"):
                        # Server sent an error (probably expects auth first)
                        error_msg = response_data.get("error", "Server rejected registration request")
                        self.register_result.emit(False, {}, f"Server error: {error_msg}")
                    else:
                        # Unexpected response
                        self.register_result.emit(False, {}, "Unexpected server response")
                        
                except asyncio.TimeoutError:
                    self.register_result.emit(False, {}, "Registration timeout - no response from server")
                except json.JSONDecodeError:
                    self.register_result.emit(False, {}, "Invalid response from server")
                        
        except websockets.exceptions.ConnectionClosed:
            self.register_result.emit(False, {}, "WebSocket connection closed by server")
        except websockets.exceptions.InvalidStatusCode as e:
            self.register_result.emit(False, {}, f"WebSocket server returned status {e.status_code}")
        except OSError as e:
            if "Connection refused" in str(e):
                self.register_result.emit(False, {}, "Cannot connect to WebSocket server")
            else:
                self.register_result.emit(False, {}, f"Connection error: {str(e)}")
        except Exception as e:
            self.register_result.emit(False, {}, f"Registration failed: {str(e)}")
    
    def stop(self):
        """Stop the registration thread"""
        self.should_stop = True