# http_client.py

import requests
import json
from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
import time

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Configuration ---
SERVER_URL = "https://localhost:8443"
API_AUTH_URL = f"{SERVER_URL}/api/auth"
API_USERS_URL = f"{SERVER_URL}/api/users"
API_ADD_FRIEND_URL = f"{SERVER_URL}/api/add_friend"
API_FRIENDS_URL = f"{SERVER_URL}/api/friends"


class Worker(QThread):
    """
    A generic worker thread. Now accepts a parent to integrate
    with Qt's memory management.
    """
    result = pyqtSignal(object)
    error = pyqtSignal(Exception)

    # --- MODIFICATION: Accept a parent object ---
    def __init__(self, func, *args, parent=None, **kwargs):
        super().__init__(parent) # Pass parent to the QThread constructor
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.func(*self.args, **self.kwargs)
            self.result.emit(res)
        except Exception as e:
            self.error.emit(e)



class HttpClient(QObject):
    """
    Backend client with full support for room-based chat API.
    """
    login_response = pyqtSignal(dict)
    register_response = pyqtSignal(dict)
    users_fetched = pyqtSignal(list)
    friend_added_response = pyqtSignal(dict)
    friend_list_fetched = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    room_info_fetched = pyqtSignal(dict)
    message_history_fetched = pyqtSignal(dict)
    message_sent_response = pyqtSignal(dict)
    new_messages_received = pyqtSignal(list)


    def __init__(self):
        super().__init__()
        self.is_polling = False
        self.polling_worker = None
        self.session = requests.Session()
        self.session.verify = False
        self.token = None
        self.workers = []

    def start_polling_for_messages(self):
        """Starts the long polling loop in a background thread."""
        if self.is_polling:
            return # Polling is already active
        
        print("CLIENT: Starting long polling for new messages...")
        self.is_polling = True
        # Use a dedicated attribute for the polling worker
        self.polling_worker = Worker(self._poll_loop, parent=self)
        self.polling_worker.start()

    def stop_polling(self):
        """Stops the long polling loop."""
        print("CLIENT: Stopping long polling.")
        self.is_polling = False
        # The thread will exit gracefully on its own after the current request times out

    def _poll_loop(self):
        """The main loop that continuously polls for messages."""
        while self.is_polling:
            try:
                if not self.token or not self.is_polling:
                    break # Exit loop if not authenticated or stopped
                
                # This is a blocking request with a long timeout
                response = self.session.get(f"{SERVER_URL}/api/receive?poll=true", timeout=35)
                
                if not self.is_polling:
                    break # Exit immediately if polling was stopped during the request

                if response.status_code == 200:
                    data = response.json()
                    messages = data.get("messages", [])
                    if messages:
                        print(f"CLIENT (Poll): Received {len(messages)} new message(s).")
                        self.new_messages_received.emit(messages)
                else:
                    # If there's an error, wait a bit before retrying
                    time.sleep(5)

            except requests.exceptions.Timeout:
                # This is expected. Just continue the loop to start a new poll.
                continue
            except Exception as e:
                # Handle other errors, like connection loss
                print(f"CLIENT (Poll): Error during polling: {e}")
                self.error_occurred.emit(f"Connection lost. Retrying in 5 seconds...")
                time.sleep(5)

    def _start_worker(self, func, on_success, on_error, *args, **kwargs):
        worker = Worker(func, *args, parent=self, **kwargs)
        worker.result.connect(on_success)
        worker.error.connect(on_error)
        def cleanup():
            if worker in self.workers:
                self.workers.remove(worker)
            worker.deleteLater()
        worker.finished.connect(cleanup)
        self.workers.append(worker)
        worker.start()

    def download_file_from_url(self, file_path):
        """Downloads a file given its relative path from the server."""
        if not self.token:
            self.error_occurred.emit("Authentication token is missing.")
            return None
        
        full_url = f"{SERVER_URL}{file_path}"
        print(f"CLIENT: Downloading file from {full_url}")
        
        try:
            # This is a synchronous call, but should be fast enough for this context.
            # For very large files, this should also be in a thread.
            response = self.session.get(full_url, timeout=20)
            response.raise_for_status()
            return response.content # Return the raw binary data
        except Exception as e:
            self.error_occurred.emit(f"Failed to download file: {e}")
            return None

    # --- NO CHANGES ARE NEEDED FOR ANY METHOD BELOW THIS LINE ---
    # The fix is entirely contained in __init__ and _start_worker above.

    def _handle_error(self, e):
        if isinstance(e, requests.exceptions.HTTPError):
            print(f"❌ HTTP Error: {e.response.status_code} - {e.response.reason}")
            self.error_occurred.emit(f"Server Error: {e.response.status_code}")
        elif isinstance(e, requests.exceptions.ConnectionError):
            self.error_occurred.emit("Cannot connect to server.")
        else:
            self.error_occurred.emit(f"An error occurred: {e}")

    def find_or_create_room(self, peer_id):
        """Asks the server for a private room with a peer."""
        if not self.token: return self.error_occurred.emit("Authentication token is missing.")
        
        print(f"CLIENT: Finding/creating room for peer_id: {peer_id}")
        payload = {"peer_id": peer_id}
        self._start_worker(
            lambda: self.session.post(f"{SERVER_URL}/api/rooms/find-or-create", json=payload),
            on_success=lambda r: self.room_info_fetched.emit(r.json()),
            on_error=self._handle_error
        )

    def get_messages(self, room_id):
        """Fetches the message history for a given room."""
        if not self.token: return self.error_occurred.emit("Authentication token is missing.")
            
        print(f"CLIENT: Fetching messages for room_id: {room_id}")
        self._start_worker(
            lambda: self.session.get(f"{SERVER_URL}/api/messages/{room_id}"),
            on_success=lambda r: self.message_history_fetched.emit(r.json()),
            on_error=self._handle_error
        )

    def send_message(self, room_id, message_data):
        """Sends a message object (text, image, or file) to a specific room."""
        if not self.token: return self.error_occurred.emit("Authentication token missing.")

        # This payload matches the server's expectation from friend_bridge_server_4.py
        payload = {
            "room_id": room_id,
            **message_data
        }
        print(f"CLIENT: Sending payload to /api/send_message: {payload}")
        self._start_worker(
            lambda: self.session.post(f"{SERVER_URL}/api/send_message", json=payload),
            on_success=self.handle_send_message_response,
            on_error=self._handle_error
        )
        
    def handle_send_message_response(self, response):
        response.raise_for_status()
        self.message_sent_response.emit(response.json())

    def set_auth_token(self, token):
        self.token = token
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            self.session.headers.pop("Authorization", None)

    def login(self, username, password_hash):
        payload = {"type": "login", "username": username, "password": password_hash}
        self._start_worker(
            lambda: self.session.post(API_AUTH_URL, json=payload, timeout=10),
            on_success=lambda r: self.handle_auth_response(r, "login"),
            on_error=self._handle_error
        )

    def register(self, username, password_hash):
        payload = {"type": "register", "username": username, "password": password_hash}
        self._start_worker(
            lambda: self.session.post(API_AUTH_URL, json=payload, timeout=10),
            on_success=lambda r: self.handle_auth_response(r, "register"),
            on_error=self._handle_error
        )

    def handle_auth_response(self, response, auth_type):
        response.raise_for_status()
        data = response.json()
        if auth_type == "login":
            if data.get("status") == "success":
                self.set_auth_token(data.get("token"))
            self.login_response.emit(data)
        elif auth_type == "register":
            self.register_response.emit(data)

    def get_users(self):
        self._start_worker(
            lambda: self.session.get(API_USERS_URL, timeout=10),
            on_success=self.handle_get_users_response,
            on_error=self._handle_error
        )

    def handle_get_users_response(self, response):
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            self.users_fetched.emit(data.get("users", []))
        else:
            self.error_occurred.emit(data.get("message", "Failed to fetch users."))

    def add_friend(self, friend_username):
        payload = {"username": friend_username}
        self._start_worker(
            lambda: self.session.post(API_ADD_FRIEND_URL, json=payload, timeout=10),
            on_success=self.handle_add_friend_response,
            on_error=self._handle_error
        )
        
    def handle_add_friend_response(self, response):
        response.raise_for_status()
        data = response.json()
        self.friend_added_response.emit(data)
        
    def get_friends(self):
        if not self.token:
            self.error_occurred.emit("Not authenticated. Cannot fetch friends.")
            return
        print("CLIENT: Fetching friend list from server...")
        self._start_worker(
            lambda: self.session.get(f"{SERVER_URL}/api/friends", timeout=10),
            on_success=self.handle_get_friends_response,
            on_error=self._handle_error
        )

    def handle_get_friends_response(self, response):
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            print(f"CLIENT: Successfully fetched {data.get('count', 0)} friends.")
            self.friend_list_fetched.emit(data)
        else:
            self.error_occurred.emit(data.get("message", "Failed to fetch friend list."))

    def get_messages(self, contact):
        """Get message history with contact"""
        if not self.token:
            self.error_occurred.emit("Not authenticated. Cannot fetch messages.")
            return
        
        print(f"CLIENT: Fetching messages with {contact}")
        self._start_worker(
            lambda: self.session.get(f"{SERVER_URL}/api/messages/{contact}", timeout=10),
            on_success=self.handle_get_messages_response,
            on_error=self._handle_error
        )

    def handle_get_messages_response(self, response):
        """Handles the server's response for the message history."""
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            print(f"CLIENT: Fetched {len(data.get('messages', []))} messages")
            # --- FIX: Use the correct signal name 'message_history_fetched' ---
            self.message_history_fetched.emit(data)
        else:
            self.error_occurred.emit(data.get("message", "Failed to fetch messages."))
            
    def cleanup(self):
        self.set_auth_token(None)
        print("HTTP Client cleaned up.")