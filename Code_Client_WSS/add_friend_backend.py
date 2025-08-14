import json
import asyncio
import websockets
from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
import ssl


class AddFriendBackend(QObject):
    """Pure WebSocket backend for add friend functionality"""
    
    # Signals for frontend communication
    search_user_response = pyqtSignal(dict)  # For username search results
    add_friend_response = pyqtSignal(dict)   # For add friend results
    error_occurred = pyqtSignal(str)
    
    def __init__(self, auth_token=None):
        super().__init__()
        self.auth_token = auth_token
    
        # Server configuration - Pure WebSocket
        self.SERVER_HOST = "localhost"
        self.SERVER_PORT = 8443
        self.SERVER_WSS_URL = f"wss://{self.SERVER_HOST}:{self.SERVER_PORT}"

        print(f"🔧 Pure WebSocket Add Friend Backend initialized")
        print(f"🎯 WSS (search & add friend): {self.SERVER_WSS_URL}")
    
    def set_auth_token(self, token):
        """Set authentication token after login"""
        self.auth_token = token
        print(f"🔑 Auth token set: {token[:20]}…" if token else "No token")

    def search_user(self, username):
        """Search for a user by username using WebSocket"""
        if not self.auth_token:
            self.error_occurred.emit("Not authenticated. Please login first.")
            return

        if not username.strip():
            self.error_occurred.emit("Username is required for search")
            return

        print(f"🔍 Searching for user via WebSocket: {username}")

        self.search_thread = SearchUserThread(
            self.SERVER_WSS_URL,
            self.auth_token,
            username.strip()
        )
        self.search_thread.search_result.connect(self.handle_search_result)
        self.search_thread.start()

    def add_friend(self, username):
        """Add friend using WebSocket"""
        if not self.auth_token:
            self.error_occurred.emit("Not authenticated. Please login first.")
            return

        if not username.strip():
            self.error_occurred.emit("Username is required to add friend")
            return

        print(f"➕ Adding friend via WebSocket: {username}")

        self.add_friend_thread = AddFriendThread(
            self.SERVER_WSS_URL,
            self.auth_token,
            username.strip()
        )
        self.add_friend_thread.add_friend_result.connect(self.handle_add_friend_result)
        self.add_friend_thread.start()

    @pyqtSlot(bool, dict, str)
    def handle_search_result(self, success, response_data, error_message):
        """Handle user search result"""
        if success:
            print(f"✅ User search successful: {response_data}")
            self.search_user_response.emit({"status": "success", "data": response_data})
        else:
            print(f"❌ User search failed: {error_message}")
            self.search_user_response.emit({"status": "error", "message": error_message})

    @pyqtSlot(bool, dict, str)
    def handle_add_friend_result(self, success, response_data, error_message):
        """Handle add friend result"""
        if success:
            print(f"✅ Add friend successful: {response_data}")
            self.add_friend_response.emit({"status": "success", "data": response_data})
        else:
            print(f"❌ Add friend failed: {error_message}")
            self.add_friend_response.emit({"status": "error", "message": error_message})


class SearchUserThread(QThread):
    """Thread for searching users using WebSocket"""
    
    search_result = pyqtSignal(bool, dict, str)  # success, response_data, error_message
    
    def __init__(self, server_url, auth_token, username):
        super().__init__()
        self.server_url = server_url
        self.auth_token = auth_token
        self.username = username
    
    def run(self):
        """Perform user search using WebSocket"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.search_user()) 
        except Exception as e:
            self.search_result.emit(False, {}, f"Search error: {str(e)}") 
        finally:
            try:
                loop.close()
            except:
                pass
    
    async def search_user(self):
        """Search for user using WebSocket"""   
        try:
            print(f"🚀 WSS Search - Starting search for: '{self.username}'")
            print(f"🔑 Auth token: {self.auth_token[:20] if self.auth_token else 'None'}...")
            
            # Create SSL context for WSS
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            print(f"🔗 WSS Search - Connecting to: {self.server_url}")
            
            async with websockets.connect(
                self.server_url,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=10
            ) as websocket:
                
                # Send authentication first
                auth_message = {
                    "token": self.auth_token,
                    "session_id": "search_user_client"
                }
                print(f"📤 Sending auth: {self.auth_token[:20]}...")
                await websocket.send(json.dumps(auth_message))
                
                # Wait for auth response
                auth_response = await websocket.recv()
                auth_data = json.loads(auth_response)
                print(f"📨 Auth response: {auth_data}")
                
                if auth_data.get("type") != "auth_success":
                    error_msg = auth_data.get("error", "Authentication failed")
                    self.search_result.emit(False, {}, f"WSS Auth failed: {error_msg}")
                    return

                # Send search user request via WebSocket
                search_message = {
                    "type": "search_user",
                    "username": self.username
                }
                print(f"📤 Sending search request: {search_message}")
                await websocket.send(json.dumps(search_message))

                # Wait for response
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"📨 Search response: {response_data}")
                
                # Handle search response
                if response_data.get("type") == "search_user_response":
                    response = await websocket.recv()
                    print(f"🔍 [DEBUG] Raw response received: {response}")
                    print(f"🔍 [DEBUG] Response type: {type(response)}")
                    print(f"🔍 [DEBUG] Response length: {len(response) if response else 0}")
        
                    response_data = json.loads(response)
                    print(f"📨 Search response: {response_data}")
                    print(f"🔍 [DEBUG] Response type field: {response_data.get('type')}")
                    if response_data.get("status") == "success":
                        user_data = response_data.get("user", {})
                        print(f"✅ WSS Search Success: Found user {user_data}")
                        self.search_result.emit(True, {
                            "user": user_data,
                            "username": user_data.get("username"),
                            "user_id": user_data.get("user_id")
                        }, "")
                    else:
                        error_msg = response_data.get("message", f"User '{self.username}' not found")
                        print(f"❌ WSS Search Failed: {error_msg}")
                        self.search_result.emit(False, {}, error_msg)
                else:
                    print(f"❌ WSS Search: Invalid response type - {response_data}")
                    self.search_result.emit(False, {}, "Invalid response from server")

        except websockets.exceptions.ConnectionClosed:
            print(f"❌ WSS Search: Connection closed by server")
            self.search_result.emit(False, {}, "WebSocket connection closed by server")
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"❌ WSS Search: Invalid status code {e.status_code}")
            self.search_result.emit(False, {}, f"WebSocket connection failed: HTTP {e.status_code}")
        except OSError as e:
            if "Connection refused" in str(e):
                print(f"❌ WSS Search: Server not running")
                self.search_result.emit(False, {}, "Cannot connect to WebSocket server - server not running")
            else:
                print(f"❌ WSS Search: Connection error - {e}")
                self.search_result.emit(False, {}, f"WebSocket connection error: {e}")
        except asyncio.TimeoutError:
            print(f"❌ WSS Search: Timeout after 10 seconds")
            self.search_result.emit(False, {}, "Search timeout - server too slow")
        except Exception as e:
            print(f"❌ WSS Search: Unexpected error - {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.search_result.emit(False, {}, f"Search failed: {str(e)}")


class AddFriendThread(QThread):
    """Thread for adding friends via WebSocket"""
    
    add_friend_result = pyqtSignal(bool, dict, str)  # success, response_data, error_message
    
    def __init__(self, server_url, auth_token, username):
        super().__init__()
        self.server_url = server_url
        self.auth_token = auth_token
        self.username = username
    
    def run(self):
        """Perform add friend via WebSocket"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.add_friend()) 
        except Exception as e:
            self.add_friend_result.emit(False, {}, f"Add friend error: {str(e)}") 
        finally:
            try:
                loop.close()
            except:
                pass
    
    async def add_friend(self):
        """Add friend via WebSocket"""
        try:
            print(f"🚀 WSS Add Friend - Starting for: '{self.username}'")
            print(f"🔑 Auth token: {self.auth_token[:20] if self.auth_token else 'None'}...")

        # Create SSL context for WSS
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            print(f"🔗 WSS Add Friend - Connecting to: {self.server_url}")

            async with websockets.connect(
                self.server_url,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=10
            ) as websocket:

            # Step 1: Send authentication
                auth_message = {
                    "token": self.auth_token,
                    "session_id": "add_friend_client"
                }
                print(f"📤 Sending auth: {self.auth_token[:20]}...")
                await websocket.send(json.dumps(auth_message))

            # Step 2: Wait for auth success
                while True:
                    auth_response = await websocket.recv()
                    auth_data = json.loads(auth_response)
                    print(f"📨 Received during auth: {auth_data}")
                    if auth_data.get("type") == "auth_success":
                        break
                    elif auth_data.get("type") == "auth_error":
                        self.add_friend_result.emit(False, {}, f"WSS Auth failed: {auth_data.get('message', 'Unknown error')}")
                        return

            # Step 3: Send add friend request
                add_friend_message = {
                    "type": "add_friend",
                    "username": self.username
                }
                print(f"📤 Sending add friend: {add_friend_message}")
                await websocket.send(json.dumps(add_friend_message))

            # Step 4: Wait for add_friend_response
                while True:
                    response = await websocket.recv()
                    response_data = json.loads(response)
                    print(f"📨 Received: {response_data}")

                    if response_data.get("type") == "add_friend_response":
                        if response_data.get("status") == "success":
                            print(f"✅ WSS Add Friend Success: {response_data}")
                            self.add_friend_result.emit(True, {
                                "username": self.username,
                                "message": response_data.get("message", "Friend added successfully")
                            }, "")
                        else:
                            error_msg = response_data.get("message", "Add friend failed")
                            print(f"❌ WSS Add Friend Failed: {error_msg}")
                            self.add_friend_result.emit(False, {}, error_msg)
                        break  # ✅ Done
                    else:
                        print(f"⚠️ Ignored message: {response_data.get('type')}")

        except websockets.exceptions.ConnectionClosed:
            print(f"❌ WSS Add Friend: Connection closed by server")
            self.add_friend_result.emit(False, {}, "WebSocket connection closed by server")
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"❌ WSS Add Friend: Invalid status code {e.status_code}")
            self.add_friend_result.emit(False, {}, f"WebSocket connection failed: HTTP {e.status_code}")
        except OSError as e:
            if "Connection refused" in str(e):
                print(f"❌ WSS Add Friend: Server not running")
                self.add_friend_result.emit(False, {}, "Cannot connect to WebSocket server - server not running")
            else:
                print(f"❌ WSS Add Friend: Connection error - {e}")
                self.add_friend_result.emit(False, {}, f"WebSocket connection error: {e}")
        except Exception as e:
            print(f"❌ WSS Add Friend: Unexpected error - {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.add_friend_result.emit(False, {}, f"Add friend failed: {str(e)}")
