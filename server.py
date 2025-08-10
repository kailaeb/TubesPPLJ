import asyncio
import ssl
import json
import time
import hashlib
import sqlite3
import os
from collections import defaultdict, deque
from aiohttp import web, WSMsgType
import aiohttp_cors
import uuid
import weakref
from datetime import datetime, timedelta
import jwt
import psycopg2
import pytz
import contextlib
import base64

CHAT_LOG_FILE = 'chat_log.json'
chat_log_lock = asyncio.Lock()

def load_chat_log():
    """Memuat data chat dari file JSON."""
    try:
        with open(CHAT_LOG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Jika file tidak ada atau rusak, kembalikan struktur default
        return {"conversations": {}}

def save_chat_log(data):
    """Menyimpan data chat ke file JSON."""
    with open(CHAT_LOG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Database setup
DATABASE_FILE = 'auth_bridge.db'
JWT_SECRET = 'your-secret-key-change-in-production'  # Change this in production!

def get_db_connection():
    """Get database connection"""
    try:
    #     # Coba PostgreSQL dulu
        conn = psycopg2.connect(
            host="aws-0-ap-southeast-1.pooler.supabase.com",
            port=6543,                                 
            database="postgres",                         
            user="postgres.ziymoatadswbppsrsanr",         
            password="Oriorion21!",      
            sslmode='require'
        )
        return conn # , 'postgresql'
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise
    # except:
    #     # Fallback ke SQLite
    #     conn = sqlite3.connect(DATABASE_FILE)
    #     conn.row_factory = sqlite3.Row
    #     return conn, 'sqlite'


# def hash_password(password):
#     """Hash password using SHA-256"""
#     return hashlib.sha256(password.encode()).hexdigest()

@contextlib.contextmanager
def get_db_cursor():
    """PERBAIKAN: Context manager for database operations"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        yield cursor, conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def init_database():
    """Initialize SQLite database with users table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table matching your schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    # Create friendships table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS friendships (
            user_id INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, friend_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (friend_id) REFERENCES users (user_id)
        )
    ''')

    # Tabel untuk menyimpan informasi room
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            room_id SERIAL PRIMARY KEY,
            type VARCHAR(50) NOT NULL, -- 'private' untuk 1-on-1, 'group' untuk grup
            room_name VARCHAR(255),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabel untuk menyimpan anggota dari setiap room
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS room_members (
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role VARCHAR(50) DEFAULT 'member', -- bisa 'admin' atau 'member'
            PRIMARY KEY (room_id, user_id),
            FOREIGN KEY (room_id) REFERENCES rooms (room_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')
    
    # # Create sessions table for active sessions
    # cursor.execute('''
    #     CREATE TABLE IF NOT EXISTS user_sessions (
    #         session_id TEXT PRIMARY KEY,
    #         user_id INTEGER,
    #         username TEXT,
    #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #         expires_at TIMESTAMP,
    #         is_active BOOLEAN DEFAULT TRUE,
    #         FOREIGN KEY (user_id) REFERENCES users (user_id)
    #     )
    # ''')
    
    conn.commit()
    conn.close()
    # print(f"✅ Database initialized: {DATABASE_FILE}")

def verify_password(password, password_hash):
    """Verify password against hash"""
    return password == password_hash

def create_jwt_token(user_id, username):
    """Create JWT token for user session"""
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.now(pytz.UTC) + timedelta(hours=24),  # 24 hour expiry
        'iat': datetime.now(pytz.UTC)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token):
    """Verify JWT token and return user info"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

class AuthenticatedMessageBridge:
    def __init__(self):
        # Store active WebSocket connections with user info
        self.websocket_clients = {}  # {ws: {'user_id': int, 'username': str, 'session_id': str}}
        
        # Message queues untuk setiap user
        self.user_message_queues = defaultdict(lambda: deque(maxlen=100))
        
        # HTTP clients yang sedang long-polling per user
        self.http_long_poll_clients = {}  # {client_id: {'future': future, 'user_id': int}}
        
        # Statistics
        self.stats = {
            'total_messages': 0,
            'active_websocket_clients': 0,
            'active_http_polls': 0,
            'registered_users': 0,
            'active_sessions': 0
        }
        
        # Update stats on init
        self.update_user_stats()
    
    def update_user_stats(self):
        """Update user statistics from database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Count registered users
            cursor.execute("SELECT COUNT(*) FROM users")
            self.stats['registered_users'] = cursor.fetchone()[0]
            
            # Count active sessions
            # cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE is_active = TRUE AND expires_at > ?", 
            #              (datetime.now(pytz.UTC),))
            # self.stats['active_sessions'] = cursor.fetchone()[0]
            
            conn.close()
        except Exception as e:
            print(f"❌ Error updating user stats: {e}")
    
    def add_websocket_client(self, ws, user_id, username, session_id):
        """Add authenticated WebSocket client"""
        self.websocket_clients[ws] = {
            'user_id': user_id,
            'username': username,
            'session_id': session_id,
            'connected_at': time.time()
        }
        self.stats['active_websocket_clients'] = len(self.websocket_clients)
        print(f"🔌 WebSocket client connected: {username} (ID: {user_id})")
    
    def remove_websocket_client(self, ws):
        """Remove WebSocket client"""
        if ws in self.websocket_clients:
            user_info = self.websocket_clients[ws]
            del self.websocket_clients[ws]
            self.stats['active_websocket_clients'] = len(self.websocket_clients)
            print(f"🔌 WebSocket client disconnected: {user_info['username']}")
    
    def get_user_from_ws(self, ws):
        """Get user info from WebSocket connection"""
        return self.websocket_clients.get(ws)
    
    async def send_to_user_websockets(self, target_user_id, message, exclude_ws=None):
        """Send message to specific user's WebSocket connections"""
        sent_count = 0
        closed_clients = set()
        
        for ws, user_info in self.websocket_clients.items():
            if user_info['user_id'] == target_user_id and ws != exclude_ws:
                try:
                    if ws.closed:
                        closed_clients.add(ws)
                    else:
                        await ws.send_str(json.dumps(message))
                        sent_count += 1
                        print(f"📤 [WS] Sent to {user_info['username']}: {message}")
                except Exception as e:
                    print(f"❌ Error sending to WebSocket {user_info['username']}: {e}")
                    closed_clients.add(ws)
        
        # Clean up closed connections
        for ws in closed_clients:
            self.remove_websocket_client(ws)
        
        return sent_count
    
    async def broadcast_to_all_websockets(self, message, exclude_ws=None):
        """Broadcast message to all WebSocket connections"""
        sent_count = 0
        closed_clients = set()
        
        for ws, user_info in self.websocket_clients.items():
            if ws != exclude_ws:
                try:
                    if ws.closed:
                        closed_clients.add(ws)
                    else:
                        await ws.send_str(json.dumps(message))
                        sent_count += 1
                except Exception as e:
                    print(f"❌ Error broadcasting to {user_info['username']}: {e}")
                    closed_clients.add(ws)
        
        # Clean up closed connections
        for ws in closed_clients:
            self.remove_websocket_client(ws)
        
        return sent_count
    
    def add_message_for_user(self, target_user_id, message):
        """Add message to queue for specific user's HTTP clients"""
        enhanced_message = {
            **message,
            'bridge_id': str(uuid.uuid4()),
            'bridge_timestamp': time.time(),
            'target_user_id': target_user_id
        }
        
        self.user_message_queues[target_user_id].append(enhanced_message)
        self.stats['total_messages'] += 1
        print(f"📦 [Bridge] Queued message for user {target_user_id}: {enhanced_message}")
        
        # Notify waiting HTTP clients for this user
        self._notify_user_http_clients(target_user_id, enhanced_message)
    
    def get_messages_for_user(self, user_id, since_timestamp=None):
        """Get messages for specific user"""
        messages = list(self.user_message_queues[user_id])
        if since_timestamp:
            messages = [msg for msg in messages if msg['bridge_timestamp'] > since_timestamp]
        return messages
    
    def _notify_user_http_clients(self, user_id, message):
        """Notify waiting HTTP long-poll clients for specific user"""
        for client_id, client_info in list(self.http_long_poll_clients.items()):
            if client_info['user_id'] == user_id and not client_info['future'].done():
                client_info['future'].set_result([message])
                del self.http_long_poll_clients[client_id]
    
    async def wait_for_user_messages(self, client_id, user_id, timeout=30):
        """Long polling untuk HTTP clients untuk specific user"""
        future = asyncio.Future()
        self.http_long_poll_clients[client_id] = {
            'future': future,
            'user_id': user_id
        }
        self.stats['active_http_polls'] = len(self.http_long_poll_clients)
        
        try:
            messages = await asyncio.wait_for(future, timeout=timeout)
            return messages
        except asyncio.TimeoutError:
            self.http_long_poll_clients.pop(client_id, None)
            self.stats['active_http_polls'] = len(self.http_long_poll_clients)
            return []
        except asyncio.CancelledError:
            self.http_long_poll_clients.pop(client_id, None)
            self.stats['active_http_polls'] = len(self.http_long_poll_clients)
            return []
        except Exception as e:
            self.http_long_poll_clients.pop(client_id, None)
            self.stats['active_http_polls'] = len(self.http_long_poll_clients)
            print(f"❌ [Bridge] Error in wait_for_user_messages: {e}")
            return []

# Global authenticated bridge instance
auth_bridge = AuthenticatedMessageBridge()

def get_user_from_token(request):
    """Extract user info from JWT token in request"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    return verify_jwt_token(token)

async def auth_login_register(request):
    """PERBAIKAN: Auth with proper database handling"""
    try:
        data = await request.json()
        action_type = data.get('type')
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return web.json_response({
                'status': 'error',
                'message': 'Username and password are required'
            }, status=400)
        
        if action_type not in ['login', 'register']:
            return web.json_response({
                'status': 'error',
                'message': 'Type must be "login" or "register"'
            }, status=400)
        
        with get_db_cursor() as (cursor, conn):
            if action_type == 'register':
                try:
                    cursor.execute(
                        "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING user_id",
                        (username, password)
                    )
                    user_id = cursor.fetchone()[0]
                    conn.commit()

                    print(f"✅ [Auth] New user registered: {username} (ID: {user_id})")
                    
                    token = create_jwt_token(user_id, username)
                    session_id = str(uuid.uuid4())
                    
                    response_data = {
                        'status': 'success',
                        'message': 'Registration successful',
                        'user': {'user_id': user_id, 'username': username},
                        'token': token,
                        'session_id': session_id
                    }
                    
                except psycopg2.IntegrityError:
                    response_data = {
                        'status': 'error',
                        'message': 'Username already exists'
                    }
                    
            else:  # login
                cursor.execute(
                    "SELECT user_id, username, password_hash FROM users WHERE username = %s",
                    (username,)
                )
                user = cursor.fetchone()
                
                if user and verify_password(password, user[2]):
                    user_id, db_username, _ = user
                    
                    token = create_jwt_token(user_id, username)
                    session_id = str(uuid.uuid4())
                    
                    print(f"✅ [Auth] User logged in: {username} (ID: {user_id})")
                    
                    response_data = {
                        'status': 'success',
                        'message': 'Login successful',
                        'user': {'user_id': user_id, 'username': db_username},
                        'token': token,
                        'session_id': session_id
                    }
                    
                else:
                    response_data = {
                        'status': 'error',
                        'message': 'Invalid username or password'
                    }
        
        auth_bridge.update_user_stats()
        print(f"📨 [Auth] {action_type.title()} request from {request.remote}: {response_data['status']}")
        return web.json_response(response_data)
        
    except Exception as e:
        print(f"❌ [Auth] Error in {action_type}: {e}")
        return web.json_response({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)

async def auth_logout(request):
    """Handle logout requests"""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({
            'status': 'error',
            'message': 'Not authenticated'
        }, status=401)
    
    try:
        # Mark session as inactive
        conn = get_db_connection()
        cursor = conn.cursor()
        # cursor.execute(
        #     "UPDATE user_sessions SET is_active = FALSE WHERE user_id = ? AND is_active = TRUE",
        #     (user_info['user_id'],)
        # )
        conn.commit()
        conn.close()
        
        print(f"✅ [Auth] User logged out: {user_info['username']}")
        
        return web.json_response({
            'status': 'success',
            'message': 'Logout successful'
        })
        
    except Exception as e:
        print(f"❌ [Auth] Logout error: {e}")
        return web.json_response({
            'status': 'error',
            'message': 'Logout failed'
        }, status=500)
    
async def websocket_handler(request):
    """Enhanced WebSocket handler with login, registration, and authentication support"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    client_ip = request.remote
    user_info = None
    
    print(f"🔌 WebSocket connection attempt from {client_ip}")
    
    try:
        # Wait for first message (could be login, registration, OR authentication)
        first_msg_timeout = 10  # 10 seconds for first message
        first_msg = await asyncio.wait_for(ws.receive(), timeout=first_msg_timeout)
        
        if first_msg.type != WSMsgType.TEXT:
            await ws.send_str(json.dumps({'error': 'Authentication, login, or registration required'}))
            return ws
        
        try:
            first_data = json.loads(first_msg.data)
            message_type = first_data.get('type')
            
            # Handle login request (no auth needed)
            if message_type == 'login':
                await handle_websocket_login(ws, first_data)
                return ws  # Close connection after login (client gets token and reconnects)
            
            # Handle registration request (no auth needed)
            elif message_type == 'register':
                await handle_websocket_registration(ws, first_data)
                return ws  # Close connection after registration
            
            # Handle authentication with token (existing logic)
            token = first_data.get('token')
            
            if not token:
                await ws.send_str(json.dumps({'error': 'Token required for authentication'}))
                return ws
            
            user_info = verify_jwt_token(token)
            if not user_info:
                await ws.send_str(json.dumps({'error': 'Invalid or expired token'}))
                return ws
            
            # Add authenticated client
            session_id = first_data.get('session_id', 'unknown')
            auth_bridge.add_websocket_client(ws, user_info['user_id'], user_info['username'], session_id)
            
            # Send authentication success
            welcome_msg = {
                "type": "auth_success",
                "message": f"Welcome {user_info['username']}!",
                "user": {
                    "user_id": user_info['user_id'],
                    "username": user_info['username']
                },
                "timestamp": time.time()
            }
            await ws.send_str(json.dumps(welcome_msg))
            
            # Determine connection type and handle accordingly
            is_search_connection = 'search' in session_id.lower()
            is_friends_connection = 'auto_friends' in session_id.lower() or 'friends' in session_id.lower() or 'home' in session_id.lower()
            
            if is_search_connection:
                print(f"🔍 [WS] Search connection detected for {user_info['username']} - waiting for search request")
                # Don't auto-send friends for search connections
            elif is_friends_connection or session_id == 'unknown':
                # Auto-send friends for main friend list connections
                print(f"📤 [WS] Auto-sending friends list to {user_info['username']}...")
                try:
                    await handle_get_friends_websocket(ws, user_info)
                    print(f"✅ [WS] Auto-sent friends to {user_info['username']}")
                except Exception as friends_error:
                    print(f"❌ [WS] Error auto-sending friends: {friends_error}")
                    friends_error_response = {
                        "type": "friends_list_response",
                        "status": "error",
                        "message": "Failed to load friends",
                        "timestamp": time.time()
                    }
                    await ws.send_str(json.dumps(friends_error_response))
            else:
                print(f"❓ [WS] Unknown connection type for {user_info['username']} - session: {session_id}")
            
            # Send previous conversations
            previous_conversations = await get_user_previous_conversations(user_info['user_id'])
            if previous_conversations:
                conversations_msg = {
                    "type": "previous_conversations",
                    "conversations": previous_conversations,
                    "timestamp": time.time()
                }
                await ws.send_str(json.dumps(conversations_msg))
                print(f"📤 [WS] Sent {len(previous_conversations)} previous conversations to {user_info['username']}")
            
        except json.JSONDecodeError:
            await ws.send_str(json.dumps({'error': 'Invalid message format'}))
            return ws
        
        # MAIN MESSAGE HANDLING LOOP - AUTHENTICATION ALREADY VERIFIED
        print(f"🔄 [WS] Starting message loop for authenticated user: {user_info['username']}")
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    print(f"📨 [WS] Received from {user_info['username']}: {data}")
                    
                    # Handle friend-related messages (search, add friend, get friends)
                    if await handle_friend_websocket_message(ws, user_info, data):
                        # Message was handled by friend system
                        # If this was an add_friend request that succeeded, 
                        # broadcast updated friends list to all user's connections
                        if data.get('type') == 'add_friend':
                            await broadcast_friends_update_to_user(user_info['user_id'])
                        continue

                    # Handle chat messages (FIXED LOGIC - Accept username or user_id)
                    # In websocket_handler function, replace the chat message handling block

                    # --- START OF MODIFIED BLOCK ---
                    # Handle chat messages (text, image, or file)
                    if data.get('recipient_id') and (data.get('message') or data.get('file_data')):
                        recipient_id = data.get("recipient_id")
                        message_type = data.get("message_type", "text")
                        
                        # --- Logic to handle different message types ---
                        try:
                            # 1. Determine recipient ID (handle username or user_id)
                            if isinstance(recipient_id, str) and not recipient_id.isdigit():
                                with get_db_cursor() as (cursor, conn):
                                    cursor.execute("SELECT user_id FROM users WHERE username = %s", (recipient_id,))
                                    user_result = cursor.fetchone()
                                    if user_result:
                                        recipient_id = user_result[0]
                                    else:
                                        raise ValueError(f"Username '{data.get('recipient_id')}' not found")

                            recipient_id = int(recipient_id)
                            final_content = ""
                            original_filename = None

                            # 2. Process content based on type (text, image, or file)
                            if message_type in ['image', 'file']:
                                print(f"🖼️  [WS] Received {message_type} message from {user_info['username']}")
                                file_content_base64 = data.get('file_data')
                                original_filename = data.get('file_name')
                                if not file_content_base64 or not original_filename:
                                    raise ValueError("File message requires 'file_data' and 'file_name'")

                                upload_dir = f"uploads/{message_type}s"
                                os.makedirs(upload_dir, exist_ok=True)
                                
                                file_data = base64.b64decode(file_content_base64)
                                file_extension = os.path.splitext(original_filename)[1]
                                unique_filename = f"{uuid.uuid4().hex}{file_extension}"
                                file_path = os.path.join(upload_dir, unique_filename)

                                with open(file_path, 'wb') as f:
                                    f.write(file_data)
                                
                                final_content = f"/{file_path.replace(os.sep, '/')}"
                                print(f"✅ [WS] {message_type.capitalize()} saved to {file_path}")
                            else: # Default to text
                                final_content = data.get("message")
                                if not final_content:
                                    raise ValueError("Text message content cannot be empty")

                            # 3. Create room and the message object to be saved
                            room_id = get_or_create_room_id(user_info['user_id'], recipient_id)
                            new_message = {
                                "sender_id": user_info['user_id'],
                                "sender_username": user_info['username'],
                                "timestamp": datetime.now(pytz.UTC).isoformat(),
                                "type": message_type,
                                "content": final_content,
                                "filename": original_filename,
                                "room_id": room_id,
                                "recipient_id": recipient_id
                            }

                            # 4. Save to chat log
                            async with chat_log_lock:
                                chat_data = load_chat_log()
                                chat_data.setdefault("conversations", {})
                                if room_id not in chat_data["conversations"]:
                                    chat_data["conversations"][room_id] = []
                                chat_data["conversations"][room_id].append(new_message)
                                save_chat_log(chat_data)
                            print(f"✅ [Message Saved via WS to Room {room_id}]")

                            # 5. Push real-time update to the recipient
                            websocket_payload = {
                                "type": "new_message",
                                "message": new_message
                            }
                            await auth_bridge.send_to_user_websockets(
                                target_user_id=recipient_id,
                                message=websocket_payload,
                                exclude_ws=ws
                            )
                            
                            # 6. Confirm back to the sender
                            echo_response = {
                                "type": "message_sent",
                                "message": new_message,
                                "status": "delivered",
                                "server_timestamp": time.time()
                            }
                            await ws.send_str(json.dumps(echo_response))

                        except Exception as e:
                            print(f"❌ [WS] Error handling chat message: {e}")
                            await ws.send_str(json.dumps({"type": "error", "message": str(e)}))
                        
                        continue # Skip to the next message
                    # --- END OF MODIFIED BLOCK ---
                    
                    # Handle room_id and message (LEGACY SUPPORT)
                    room_id = data.get('room_id')
                    message_content = data.get('message', '').strip()
                    
                    if room_id and message_content:
                        sender_id = user_info['user_id']
                        
                        # Create message object
                        new_message = {
                            "sender_id": sender_id,
                            "sender_username": user_info['username'],
                            "timestamp": datetime.now(pytz.UTC).isoformat(),
                            "type": "text",
                            "content": message_content
                        }

                        # Save to chat_log.json
                        async with chat_log_lock:
                            chat_data = load_chat_log()
                            if room_id not in chat_data.get("conversations", {}):
                                chat_data.setdefault("conversations", {})[room_id] = []
                            
                            chat_data["conversations"][room_id].append(new_message)
                            save_chat_log(chat_data)

                        print(f"✅ [Legacy Message Saved via WS to Room {room_id}] from {user_info['username']}")

                        # Find recipient from room members
                        recipient_id = None
                        with get_db_cursor() as (cursor, conn):
                            cursor.execute(
                                "SELECT user_id FROM room_members WHERE room_id = %s", (int(room_id),)
                            )
                            members = cursor.fetchall()
                        
                        if members:
                            for member_tuple in members:
                                if member_tuple[0] != sender_id:
                                    recipient_id = member_tuple[0]
                                    break
                        
                        # Send to recipient if found
                        if recipient_id:
                            print(f"📡 Queuing message for HTTP poll for user {recipient_id}...")
                            auth_bridge.add_message_for_user(recipient_id, new_message)
                        continue
                    
                    # Handle as regular bridge message (fallback)
                    enhanced_data = {
                        **data,
                        "sender": {
                            "user_id": user_info['user_id'],
                            "username": user_info['username']
                        },
                        "timestamp": time.time(),
                        "protocol": "websocket"
                    }
                    
                    # Determine message target
                    target_user_id = data.get('target_user_id')
                    
                    if target_user_id:
                        # Send to specific user
                        auth_bridge.add_message_for_user(target_user_id, enhanced_data)
                        await auth_bridge.send_to_user_websockets(target_user_id, enhanced_data, exclude_ws=ws)
                    else:
                        # Broadcast to all users
                        await auth_bridge.broadcast_to_all_websockets(enhanced_data, exclude_ws=ws)
                        auth_bridge.add_message_for_user(user_info['user_id'], enhanced_data)
                    
                    # Echo back to sender
                    echo_response = {
                        "type": "message_sent",
                        "original": enhanced_data,
                        "server_timestamp": time.time(),
                        "status": "delivered"
                    }
                    await ws.send_str(json.dumps(echo_response))
                    
                except json.JSONDecodeError as e:
                    error_msg = {"error": "Invalid JSON", "details": str(e)}
                    await ws.send_str(json.dumps(error_msg))
                except Exception as e:
                    print(f"❌ [WS] Error processing message: {e}")
                    await ws.send_str(json.dumps({'error': f'Server error: {e}'}))
                    
            elif msg.type == WSMsgType.ERROR:
                print(f'❌ [WS] Error from {user_info["username"]}: {ws.exception()}')
                break
    
    except asyncio.TimeoutError:
        print(f"⏰ WebSocket timeout from {client_ip}")
        await ws.send_str(json.dumps({'error': 'Message timeout'}))
    except Exception as e:
        print(f"❌ [WS] Exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if user_info and ws in auth_bridge.websocket_clients:
            auth_bridge.remove_websocket_client(ws)
            print(f"🔌 [WS] Disconnected: {user_info['username']}")
    
    return ws

async def api_send_authenticated_message(request):
    """HTTP endpoint untuk mengirim message dengan authentication"""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({
            'status': 'error',
            'message': 'Authentication required'
        }, status=401)
    
    try:
        data = await request.json()
        print(f"📨 [HTTP] Authenticated message from {user_info['username']}: {data}")
        
        # Enhanced message with sender info
        enhanced_data = {
            **data,
            "sender": {
                "user_id": user_info['user_id'],
                "username": user_info['username']
            },
            "timestamp": time.time(),
            "protocol": "http"
        }
        
        # Determine target
        target_user_id = data.get('target_user_id')
        
        if target_user_id:
            # Send to specific user
            auth_bridge.add_message_for_user(target_user_id, enhanced_data)
            sent_count = await auth_bridge.send_to_user_websockets(target_user_id, enhanced_data)
        else:
            # Broadcast to all
            sent_count = await auth_bridge.broadcast_to_all_websockets(enhanced_data)
        
        response_data = {
            "status": "success",
            "message": "Message sent successfully",
            "sent_to_websocket_clients": sent_count,
            "bridged_message": enhanced_data,
            "timestamp": time.time()
        }
        
        return web.json_response(response_data)
        
    except Exception as e:
        print(f"❌ [HTTP] Error: {e}")
        return web.json_response({
            "status": "error",
            "error": str(e)
        }, status=500)

async def api_receive_authenticated_messages(request):
    """HTTP endpoint untuk menerima messages dengan authentication"""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({
            'status': 'error',
            'message': 'Authentication required'
        }, status=401)
    
    client_id = f"http_{uuid.uuid4().hex[:8]}"
    user_id = user_info['user_id']
    
    try:
        since_param = request.query.get('since')
        since_timestamp = float(since_param) if since_param else None
    except (ValueError, TypeError):
        since_timestamp = None
    
    poll = request.query.get('poll', 'false').lower() == 'true'
    
    print(f"📡 [HTTP] User {user_info['username']} requesting messages (poll={poll})")
    
    try:
        if poll:
            messages = await auth_bridge.wait_for_user_messages(client_id, user_id, timeout=30)
        else:
            messages = auth_bridge.get_messages_for_user(user_id, since_timestamp)
        
        response_data = {
            "status": "success",
            "messages": messages,
            "count": len(messages),
            "user_id": user_id,
            "timestamp": time.time()
        }
        
        if messages:
            print(f"📤 [HTTP] Sending {len(messages)} messages to {user_info['username']}")
        
        return web.json_response(response_data)
        
    except Exception as e:
        print(f"❌ [HTTP] Error for {user_info['username']}: {e}")
        return web.json_response({
            "status": "error",
            "error": str(e)
        }, status=500)

async def api_get_users(request):
    """Get list of registered users (for targeting messages)"""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({
            'status': 'error',
            'message': 'Authentication required'
        }, status=401)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username FROM users ORDER BY username")
        users = [{'user_id': row[0], 'username': row[1]} for row in cursor.fetchall()]
        conn.close()
        
        return web.json_response({
            'status': 'success',
            'users': users,
            'current_user': user_info
        })
        
    except Exception as e:
        return web.json_response({
            'status': 'error',
            'error': str(e)
        }, status=500)
    
async def api_add_friend(request):
    """PERBAIKAN: Add friend with proper database handling"""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({
            'status': 'error',
            'message': 'Authentication required'
        }, status=401)
    
    try:
        data = await request.json()
        friend_username = data.get('username', '').strip()
        
        if not friend_username:
            return web.json_response({
                'status': 'error',
                'message': 'Friend username is required'
            }, status=400)
        
        with get_db_cursor() as (cursor, conn):
            # Find friend by username
            cursor.execute(
                "SELECT user_id FROM users WHERE username = %s",
                (friend_username,)
            )
            friend = cursor.fetchone()
            
            if not friend:
                return web.json_response({
                    'status': 'error',
                    'message': 'User not found'
                })
            
            friend_id = friend[0]
            
            if friend_id == user_info['user_id']:
                return web.json_response({
                    'status': 'error',
                    'message': 'Cannot add yourself as friend'
                })
            
            # Check if friendship already exists
            cursor.execute(
                "SELECT status FROM friendships WHERE user_id = %s AND friend_id = %s",
                (user_info['user_id'], friend_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                return web.json_response({
                    'status': 'error',
                    'message': f'Friend request already exists with status: {existing[0]}'
                })
            
            # Add bidirectional friendship
            cursor.execute(
                "INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, %s), (%s, %s, %s)",
                (user_info['user_id'], friend_id, 'accepted', friend_id, user_info['user_id'], 'accepted')
            )
        
        print(f"✅ [Friend] {user_info['username']} added {friend_username} as friend")
        
        return web.json_response({
            'status': 'success',
            'message': f'Successfully added {friend_username} as friend'
        })
        
    except Exception as e:
        print(f"❌ [Friend] Error: {e}")
        return web.json_response({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)
    
async def api_get_available_friends(request):
    """Get list of friend"""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({
            'status': 'error',
            'message': 'Authentication required'
        }, status=401)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get accepted friend
        cursor.execute("""
            SELECT u.user_id, u.username
            FROM users u
            WHERE u.user_id != %s
            AND u.user_id NOT IN (
                SELECT f.friend_id
                FROM friendships f
                WHERE f.user_id = %s AND f.status = 'accepted'       
            )
            ORDER BY u.username
        """, (user_info['user_id'], user_info['user_id']))
        
        friends = []
        for row in cursor.fetchall():
            friends.append({
                'user_id': row[0],
                'username': row[1],
                'created_at': str(row[2])
            })
        
        conn.close()
        
        return web.json_response({
            'status': 'success',
            'friends': friends,
            'count': len(friends)
        })
        
    except Exception as e:
        return web.json_response({
            'status': 'error',
            'error': str(e)
        }, status=500)
    
async def api_get_friends(request):
    """PERBAIKAN: Get friends with proper database handling"""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({
            'status': 'error',
            'message': 'Authentication required'
        }, status=401)
    
    try:
        with get_db_cursor() as (cursor, conn):
            # Get accepted friends
            cursor.execute("""
                SELECT u.user_id, u.username, f.created_at 
                FROM friendships f 
                JOIN users u ON f.friend_id = u.user_id 
                WHERE f.user_id = %s AND f.status = 'accepted'
                ORDER BY u.username
            """, (user_info['user_id'],))
            
            friends = []
            for row in cursor.fetchall():
                friends.append({
                    'user_id': row[0],
                    'username': row[1],
                    'created_at': str(row[2]) if row[2] else None
                })
        
        return web.json_response({
            'status': 'success',
            'friends': friends,
            'count': len(friends)
        })
        
    except Exception as e:
        print(f"❌ [Friends] Error: {e}")
        return web.json_response({
            'status': 'error',
            'error': str(e)
        }, status=500)

async def api_find_or_create_private_room(request):
    """PERBAIKAN: Room creation with proper database handling"""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({'status': 'error', 'message': 'Authentication required'}, status=401)
    
    try:
        data = await request.json()
        peer_id = int(data.get('peer_id'))
        current_user_id = user_info['user_id']

        if current_user_id == peer_id:
            return web.json_response({'status': 'error', 'message': 'Cannot create a room with yourself'}, status=400)

        with get_db_cursor() as (cursor, conn):
            # Search for existing private room
            cursor.execute("""
                SELECT r.room_id
                FROM rooms r
                JOIN room_members rm ON r.room_id = rm.room_id
                WHERE r.type = 'private'
                  AND r.room_id IN (
                    SELECT room_id FROM room_members WHERE user_id = %s
                    INTERSECT
                    SELECT room_id FROM room_members WHERE user_id = %s
                  )
                GROUP BY r.room_id
                HAVING COUNT(rm.user_id) = 2
            """, (current_user_id, peer_id))
            
            existing_room = cursor.fetchone()

            if existing_room:
                room_id = existing_room[0]
                return web.json_response({'status': 'success', 'room_id': room_id, 'created': False})
            else:
                # Create new room
                cursor.execute(
                    "INSERT INTO rooms (type) VALUES ('private') RETURNING room_id"
                )
                new_room_id = cursor.fetchone()[0]

                # Add members
                cursor.execute(
                    "INSERT INTO room_members (room_id, user_id) VALUES (%s, %s), (%s, %s)",
                    (new_room_id, current_user_id, new_room_id, peer_id)
                )
                
                print(f"✅ [Room] Created private room {new_room_id} for users {current_user_id} and {peer_id}")
                return web.json_response({'status': 'success', 'room_id': new_room_id, 'created': True})

    except Exception as e:
        print(f"❌ [Find/Create Room] Error: {e}")
        return web.json_response({'status': 'error', 'message': 'Internal server error'}, status=500)
'''
# --- MODIFIKASI TOTAL ---
async def api_send_message(request):
    """Menyimpan pesan ke file JSON dan mengirimkannya HANYA ke lawan bicara."""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({'status': 'error', 'message': 'Authentication required'}, status=401)
    
    try:
        data = await request.json()
        room_id = str(data.get('room_id'))
        message_content = data.get('message', '').strip()
        
        if not room_id or not message_content:
            return web.json_response({'status': 'error', 'message': 'room_id and message are required'}, status=400)
        
        sender_id = user_info['user_id']

        new_message = {
            "sender_id": sender_id,
            "sender_username": user_info['username'],
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "type": "text",
            "content": message_content
        }

        # Simpan pesan ke log file JSON
        async with chat_log_lock:
            chat_data = load_chat_log()
            if room_id not in chat_data.get("conversations", {}):
                chat_data.setdefault("conversations", {})[room_id] = []
            
            chat_data["conversations"][room_id].append(new_message)
            save_chat_log(chat_data)

        print(f"✅ [Message Saved to Room {room_id}] from {user_info['username']}")

        # --- LOGIKA PENGIRIMAN PESAN DIPERBAIKI ---
        
        recipient_id = None
        # 1. Dapatkan semua anggota dari room ini dari database
        with get_db_cursor() as (cursor, conn):
            cursor.execute(
                "SELECT user_id FROM room_members WHERE room_id = %s",
                (int(room_id),)
            )
            members = cursor.fetchall()  # Hasilnya akan [(id_pengirim,), (id_penerima,)]

        # 2. Cari ID penerima (anggota room yang BUKAN si pengirim)
        if members:
            for member_tuple in members:
                member_id = member_tuple[0]
                if member_id != sender_id:
                    recipient_id = member_id
                    break  # Kita sudah menemukan penerima, hentikan loop

        # 3. Jika penerima ditemukan, kirim pesan hanya ke dia
        if recipient_id:
            print(f"📡 Forwarding message from user {sender_id} to user {recipient_id} in room {room_id}...")
            await auth_bridge.send_to_user_websockets(
                target_user_id=recipient_id,
                message=new_message
            )
            auth_bridge.add_message_for_user(recipient_id, new_message)
        else:
            print(f"⚠️ Could not determine recipient for room {room_id}.")
            
        # --- AKHIR DARI LOGIKA YANG DIPERBAIKI ---
            
        return web.json_response({'status': 'success', 'message': 'Message sent and forwarded successfully'})
            
    except Exception as e:
        print(f"❌ [API Send Message] Error: {e}")
        return web.json_response({'status': 'error', 'message': 'Internal server error'}, status=500)
'''
'''
async def api_send_message(request):
    """Menyimpan pesan ke file JSON dan mengirimkannya ke lawan bicara."""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({'status': 'error', 'message': 'Authentication required'}, status=401)
    
    try:
        data = await request.json()
        room_id = str(data.get('room_id'))
        message_content = data.get('message', '').strip()
        
        if not room_id or not message_content:
            return web.json_response({'status': 'error', 'message': 'room_id and message are required'}, status=400)
        
        sender_id = user_info['user_id']

        new_message = {
            "sender_id": sender_id,
            "sender_username": user_info['username'],
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "type": "text",
            "content": message_content,
            "room_id": room_id  # <--- THIS IS THE FIX
        }

        # Simpan pesan ke log file JSON
        async with chat_log_lock:
            chat_data = load_chat_log()
            if room_id not in chat_data.get("conversations", {}):
                chat_data.setdefault("conversations", {})[room_id] = []
            
            chat_data["conversations"][room_id].append(new_message)
            save_chat_log(chat_data)

        print(f"✅ [Message Saved to Room {room_id}] from {user_info['username']}")
        
        recipient_id = None
        # Get all members from this room
        with get_db_cursor() as (cursor, conn):
            cursor.execute(
                "SELECT user_id FROM room_members WHERE room_id = %s",
                (int(room_id),)
            )
            members = cursor.fetchall()

        # Find the recipient (the member who is NOT the sender)
        if members:
            for member_tuple in members:
                member_id = member_tuple[0]
                if member_id != sender_id:
                    recipient_id = member_id
                    break
        
        if recipient_id:
            print(f"📡 Forwarding message from user {sender_id} to user {recipient_id} in room {room_id}...")
            # This notifies WebSocket clients
            await auth_bridge.send_to_user_websockets(
                target_user_id=recipient_id,
                message=new_message
            )
            # This notifies HTTP long-polling clients
            auth_bridge.add_message_for_user(recipient_id, new_message)
        else:
            print(f"⚠️ Could not determine recipient for room {room_id}.")
            
        return web.json_response({'status': 'success', 'message': 'Message sent and forwarded successfully'})
            
    except Exception as e:
        print(f"❌ [API Send Message] Error: {e}")
        return web.json_response({'status': 'error', 'message': 'Internal server error'}, status=500)
'''
async def api_send_message(request):
    """Handles sending text, image, or file messages."""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({'status': 'error', 'message': 'Authentication required'}, status=401)
    
    try:
        data = await request.json()
        room_id = str(data.get('room_id'))
        message_type = data.get('type', 'text') # Default to text
        message_content = data.get('content', '').strip()
        
        if not room_id or not message_content:
            return web.json_response({'status': 'error', 'message': 'room_id and content are required'}, status=400)
        
        sender_id = user_info['user_id']
        final_content = message_content
        original_filename = data.get('filename')

        # --- NEW: Handle file and image uploads ---
        if message_type in ['image', 'file']:
            # Create uploads directories if they don't exist
            upload_dir = f"uploads/{message_type}s"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Decode the base64 content
            try:
                file_data = base64.b64decode(message_content)
            except (ValueError, TypeError):
                return web.json_response({'status': 'error', 'message': 'Invalid base64 content'}, status=400)

            # Create a unique filename to avoid collisions
            file_extension = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(upload_dir, unique_filename)

            # Save the file to the server's disk
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # The content stored in the log is now the URL path
            final_content = f"/{file_path.replace(os.sep, '/')}"
            print(f"✅ [{message_type.capitalize()} Saved] to {file_path}")

        new_message = {
            "sender_id": sender_id,
            "sender_username": user_info['username'],
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "type": message_type,
            "content": final_content,
            "filename": original_filename, # Store original filename for display
            "room_id": room_id
        }

        # ... (The rest of the function for saving to JSON and notifying clients is the same) ...
        # ... (It saves the new_message object, which now contains the file path) ...
        
        # Simpan pesan ke log file JSON
        async with chat_log_lock:
            chat_data = load_chat_log()
            if room_id not in chat_data.get("conversations", {}):
                chat_data.setdefault("conversations", {})[room_id] = []
            
            chat_data["conversations"][room_id].append(new_message)
            save_chat_log(chat_data)

        print(f"✅ [Message Saved to Room {room_id}] from {user_info['username']}")
        
        # Find recipient and notify them
        recipient_id = None
        with get_db_cursor() as (cursor, conn):
            cursor.execute("SELECT user_id FROM room_members WHERE room_id = %s", (int(room_id),))
            members = cursor.fetchall()
        
        if members:
            for member_tuple in members:
                if member_tuple[0] != sender_id:
                    recipient_id = member_tuple[0]
                    break
        
        if recipient_id:
            auth_bridge.add_message_for_user(recipient_id, new_message)
            
        return web.json_response({'status': 'success', 'message': 'Message processed successfully'})
            
    except Exception as e:
        print(f"❌ [API Send Message] Error: {e}")
        return web.json_response({'status': 'error', 'message': 'Internal server error'}, status=500)


# --- MODIFIKASI TOTAL ---
async def api_get_messages(request):
    """Mengambil riwayat pesan dari file JSON berdasarkan room_id."""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({'status': 'error', 'message': 'Authentication required'}, status=401)
    
    try:
        room_id = request.match_info.get('room_id', '').strip()
        if not room_id:
            return web.json_response({'status': 'error', 'message': 'room_id is required in URL'}, status=400)

        # (Opsional tapi dianjurkan) Verifikasi bahwa user adalah anggota room
        # ... (logika ini bisa ditambahkan untuk keamanan) ...

        messages_to_return = []
        async with chat_log_lock:
            chat_data = load_chat_log()
            messages_to_return = chat_data.get("conversations", {}).get(room_id, [])

        # Ubah format timestamp agar lebih ramah dibaca klien
        for msg in messages_to_return:
             iso_timestamp = datetime.fromisoformat(msg["timestamp"])
             msg["timestamp"] = iso_timestamp.strftime("%I:%M %p").lower()

        return web.json_response({
            'status': 'success',
            'room_id': room_id,
            'messages': messages_to_return
        })

    except Exception as e:
        print(f"❌ [API Get Messages] Error: {e}")
        return web.json_response({'status': 'error', 'message': 'Internal server error'}, status=500)
    
#async def api_accept_friend(request):
    """Accept friend request"""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({
            'status': 'error',
            'message': 'Authentication required'
        }, status=401)
    
    try:
        data = await request.json()
        friend_user_id = data.get('user_id')
        
        if not friend_user_id:
            return web.json_response({
                'status': 'error',
                'message': 'Friend user_id is required'
            }, status=400)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update status to accepted
        cursor.execute(
            "UPDATE friendships SET status = 'accepted' WHERE user_id = %s AND friend_id = %s AND status = 'pending'",
            (friend_user_id, user_info['user_id'])
        )
        
        if cursor.rowcount == 0:
            return web.json_response({
                'status': 'error',
                'message': 'Friend request not found'
            })
        
        # Add reverse friendship (bidirectional)
        cursor.execute(
            "INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, 'accepted') ON CONFLICT (user_id, friend_id) DO UPDATE SET status = 'accepted'",
            (user_info['user_id'], friend_user_id)
        )
        
        conn.commit()
        conn.close()
        
        return web.json_response({
            'status': 'success',
            'message': 'Friend request accepted'
        })
        
    except Exception as e:
        return web.json_response({
            'status': 'error',
            'error': str(e)
        }, status=500)

async def api_get_stats(request):
    """Get enhanced statistics"""
    auth_bridge.update_user_stats()
    
    response_data = {
        "status": "success",
        "stats": auth_bridge.stats,
        "timestamp": time.time()
    }
    
    return web.json_response(response_data)

# ===== FUNGSI-FUNGSI YANG PERLU DITAMBAHKAN KE friend_bridge_server_3.py =====

# 1. WEBSOCKET LOGIN HANDLER
async def handle_websocket_login(ws, data):
    """Handle login request via WebSocket (before authentication)"""
    try:
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            error_response = {
                'type': 'login_response',
                'status': 'error',
                'message': 'Username and password are required'
            }
            await ws.send_str(json.dumps(error_response))
            return
        
        with get_db_cursor() as (cursor, conn):
            cursor.execute(
                "SELECT user_id, username, password_hash FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()
            
            if user and verify_password(password, user[2]):
                user_id, db_username, _ = user
                
                print(f"✅ [WS-Auth] User logged in: {username} (ID: {user_id})")
                
                token = create_jwt_token(user_id, username)
                session_id = str(uuid.uuid4())
                
                success_response = {
                    'type': 'login_response',
                    'status': 'success',
                    'message': 'Login successful',
                    'user': {
                        'user_id': user_id,
                        'username': db_username
                    },
                    'token': token,
                    'session_id': session_id
                }
                
                await ws.send_str(json.dumps(success_response))
                print(f"📤 [WS-Auth] Login success sent to {username}")
                
            else:
                error_response = {
                    'type': 'login_response',
                    'status': 'error',
                    'message': 'Invalid username or password'
                }
                await ws.send_str(json.dumps(error_response))
                
    except Exception as e:
        print(f"❌ [WS-Auth] Login error: {e}")
        error_response = {
            'type': 'login_response',
            'status': 'error',
            'message': 'Internal server error'
        }
        await ws.send_str(json.dumps(error_response))

# 2. WEBSOCKET REGISTRATION HANDLER
async def handle_websocket_registration(ws, data):
    """Handle registration request via WebSocket (before authentication)"""
    try:
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            error_response = {
                'type': 'register_response',
                'status': 'error',
                'message': 'Username and password are required'
            }
            await ws.send_str(json.dumps(error_response))
            return
        
        try:
            with get_db_cursor() as (cursor, conn):
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING user_id",
                    (username, password)
                )
                user_id = cursor.fetchone()[0]
                
                print(f"✅ [WS-Auth] New user registered: {username} (ID: {user_id})")
                
                token = create_jwt_token(user_id, username)
                session_id = str(uuid.uuid4())
                
                success_response = {
                    'type': 'register_response',
                    'status': 'success',
                    'message': 'Registration successful',
                    'user': {
                        'user_id': user_id,
                        'username': username
                    },
                    'token': token,
                    'session_id': session_id
                }
                
                await ws.send_str(json.dumps(success_response))
                print(f"📤 [WS-Auth] Registration success sent to {username}")
                
        except psycopg2.IntegrityError:
            error_response = {
                'type': 'register_response',
                'status': 'error',
                'message': 'Username already exists'
            }
            await ws.send_str(json.dumps(error_response))
            
    except Exception as e:
        print(f"❌ [WS-Auth] Registration error: {e}")
        error_response = {
            'type': 'register_response',
            'status': 'error',
            'message': 'Internal server error'
        }
        await ws.send_str(json.dumps(error_response))

# 3. HANDLE FRIENDS VIA WEBSOCKET
async def handle_get_friends_websocket(ws, user_info):
    """Handle get friends list via WebSocket"""
    try:
        with get_db_cursor() as (cursor, conn):
            cursor.execute("""
                SELECT f.friend_id, u.username, f.created_at 
                FROM friendships f 
                JOIN users u ON f.friend_id = u.user_id 
                WHERE f.user_id = %s AND f.status = 'accepted'
                ORDER BY u.username
            """, (user_info['user_id'],))
            
            friends = []
            for row in cursor.fetchall():
                friends.append({
                    'user_id': row[0],
                    'username': row[1],
                    'created_at': str(row[2]) if row[2] else None
                })
        
        response = {
            'type': 'friends_list_response',
            'status': 'success',
            'friends': friends,
            'count': len(friends),
            'timestamp': time.time()
        }
        
        await ws.send_str(json.dumps(response))
        print(f"📋 [WS] Sent friends list to {user_info['username']}: {len(friends)} friends")
        
    except Exception as e:
        error_response = {
            'type': 'friends_list_response',
            'status': 'error',
            'message': f'Failed to load friends: {str(e)}',
            'timestamp': time.time()
        }
        await ws.send_str(json.dumps(error_response))

# 4. HANDLE ADD FRIEND VIA WEBSOCKET
async def handle_add_friend_websocket(ws, user_info, data):
    """Handle add friend via WebSocket"""
    try:
        friend_username = data.get('username', '').strip()
        
        if not friend_username:
            error_response = {
                'type': 'add_friend_response',
                'status': 'error',
                'message': 'Friend username is required',
                'timestamp': time.time()
            }
            await ws.send_str(json.dumps(error_response))
            return
        
        with get_db_cursor() as (cursor, conn):
            # Find friend by username
            cursor.execute(
                "SELECT user_id FROM users WHERE username = %s",
                (friend_username,)
            )
            friend = cursor.fetchone()
            
            if not friend:
                error_response = {
                    'type': 'add_friend_response',
                    'status': 'error',
                    'message': 'User not found',
                    'timestamp': time.time()
                }
                await ws.send_str(json.dumps(error_response))
                return
            
            friend_id = friend[0]
            
            if friend_id == user_info['user_id']:
                error_response = {
                    'type': 'add_friend_response',
                    'status': 'error',
                    'message': 'Cannot add yourself as friend',
                    'timestamp': time.time()
                }
                await ws.send_str(json.dumps(error_response))
                return
            
            # Check if friendship already exists
            cursor.execute(
                "SELECT status FROM friendships WHERE user_id = %s AND friend_id = %s",
                (user_info['user_id'], friend_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                error_response = {
                    'type': 'add_friend_response',
                    'status': 'error',
                    'message': f'Friend request already exists with status: {existing[0]}',
                    'timestamp': time.time()
                }
                await ws.send_str(json.dumps(error_response))
                return
            
            # Add bidirectional friendship
            cursor.execute(
                "INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, %s), (%s, %s, %s)",
                (user_info['user_id'], friend_id, 'accepted', friend_id, user_info['user_id'], 'accepted')
            )
        
        success_response = {
            'type': 'add_friend_response',
            'status': 'success',
            'message': f'Successfully added {friend_username} as friend',
            'username': friend_username,
            'timestamp': time.time()
        }
        
        await ws.send_str(json.dumps(success_response))
        print(f"✅ [WS] {user_info['username']} added {friend_username} as friend (bidirectional)")
        
    except Exception as e:
        error_response = {
            'type': 'add_friend_response',
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'timestamp': time.time()
        }
        await ws.send_str(json.dumps(error_response))

# 5. HANDLE SEARCH USER VIA WEBSOCKET
async def handle_search_user_websocket(ws, user_info, data):
    """Handle user search via WebSocket"""
    try:
        search_username = data.get('username', '').strip()
        
        if not search_username:
            error_response = {
                'type': 'search_user_response',
                'status': 'error',
                'message': 'Username is required for search',
                'timestamp': time.time()
            }
            await ws.send_str(json.dumps(error_response))
            return
        
        with get_db_cursor() as (cursor, conn):
            cursor.execute(
                "SELECT user_id, username FROM users WHERE username = %s",
                (search_username,)
            )
            user = cursor.fetchone()
        
        if user:
            user_id, username = user
            success_response = {
                'type': 'search_user_response',
                'status': 'success',
                'user': {
                    'user_id': user_id,
                    'username': username
                },
                'timestamp': time.time()
            }
            await ws.send_str(json.dumps(success_response))
            print(f"✅ [WS] User search: Found {username} for {user_info['username']}")
        else:
            error_response = {
                'type': 'search_user_response',
                'status': 'error',
                'message': f'User "{search_username}" not found',
                'timestamp': time.time()
            }
            await ws.send_str(json.dumps(error_response))
            print(f"❌ [WS] User search: {search_username} not found")
        
    except Exception as e:
        print(f"❌ [WS] User search error: {e}")
        error_response = {
            'type': 'search_user_response',
            'status': 'error',
            'message': f'Search failed: {str(e)}',
            'timestamp': time.time()
        }
        await ws.send_str(json.dumps(error_response))

# 6. HANDLE FRIEND WEBSOCKET MESSAGES
async def handle_friend_websocket_message(ws, user_info, data):
    """Handle friend-related WebSocket messages"""
    message_type = data.get('type')
    
    try:
        if message_type == 'add_friend':
            await handle_add_friend_websocket(ws, user_info, data)
        elif message_type == 'search_user':
            await handle_search_user_websocket(ws, user_info, data)
        elif message_type == 'get_friends':
            await handle_get_friends_websocket(ws, user_info)
        else:
            return False  # Message not handled
        return True
    except Exception as e:
        error_response = {
            'type': 'error',
            'message': f'Error handling {message_type}: {str(e)}',
            'timestamp': time.time()
        }
        await ws.send_str(json.dumps(error_response))
        return True

# 7. GET PREVIOUS CONVERSATIONS
async def get_user_previous_conversations(user_id):
    """Get previous conversations with actual messages for user"""
    try:
        print(f"📚 [Server] Getting conversations with messages for user {user_id}")
        
        # Load chat data from JSON
        async with chat_log_lock:
            chat_data = load_chat_log()
            all_conversations = chat_data.get("conversations", {})
        
        user_conversations = {}
        
        with get_db_cursor() as (cursor, conn):
            # Get all rooms where user is a member
            cursor.execute("""
                SELECT r.room_id
                FROM rooms r
                JOIN room_members rm ON r.room_id = rm.room_id
                WHERE rm.user_id = %s AND r.type = 'private'
            """, (user_id,))
            
            user_room_ids = [str(row[0]) for row in cursor.fetchall()]
            print(f"📚 [Server] User {user_id} is member of rooms: {user_room_ids}")
        
        # Filter conversations to only include user's rooms and include actual messages
        for room_id in user_room_ids:
            if room_id in all_conversations:
                messages = all_conversations[room_id]
                if messages:  # Only include rooms with actual messages
                    user_conversations[room_id] = messages
                    print(f"📚 [Server] Added {len(messages)} messages for room {room_id}")
        
        print(f"📚 [Server] Returning {len(user_conversations)} conversations with messages for user {user_id}")
        return user_conversations
            
    except Exception as e:
        print(f"❌ [Server] Error getting conversations: {e}")
        import traceback
        traceback.print_exc()
        return {}

# 8. GET OR CREATE ROOM ID
def get_or_create_room_id(sender_id, recipient_id):
    """Cari room private antara dua user di database, atau buat baru jika belum ada."""
    try:
        # Ensure both IDs are integers
        sender_id = int(sender_id)
        recipient_id = int(recipient_id)
        
        with get_db_cursor() as (cursor, conn):
            # Cari room private yang berisi kedua user dengan query yang diperbaiki
            cursor.execute("""
                SELECT DISTINCT r.room_id
                FROM rooms r
                WHERE r.type = 'private'
                  AND r.room_id IN (
                    SELECT rm1.room_id 
                    FROM room_members rm1 
                    WHERE rm1.user_id = %s
                  )
                  AND r.room_id IN (
                    SELECT rm2.room_id 
                    FROM room_members rm2 
                    WHERE rm2.user_id = %s
                  )
                  AND (
                    SELECT COUNT(*) 
                    FROM room_members rm3 
                    WHERE rm3.room_id = r.room_id
                  ) = 2
                LIMIT 1
            """, (sender_id, recipient_id))
            
            existing_room = cursor.fetchone()
            if existing_room:
                print(f"✅ Found existing room {existing_room[0]} for users {sender_id} and {recipient_id}")
                return str(existing_room[0])
            
            # Jika belum ada, buat baru
            cursor.execute(
                "INSERT INTO rooms (type) VALUES ('private') RETURNING room_id"
            )
            new_room_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO room_members (room_id, user_id) VALUES (%s, %s), (%s, %s)",
                (new_room_id, sender_id, new_room_id, recipient_id)
            )
            print(f"✅ Created new room {new_room_id} for users {sender_id} and {recipient_id}")
            return str(new_room_id)
            
    except Exception as e:
        print(f"❌ Error in get_or_create_room_id: {e}")
        import traceback
        traceback.print_exc()
        return str(uuid.uuid4())

# 9. HANDLE NEW MESSAGE SAVE
async def handle_new_message_save(user_info, data):
    """Save new message to database - FIXED room creation logic"""
    try:
        recipient_id = data.get("recipient_id")
        message_content = data.get("message")
        
        if not recipient_id or not message_content:
            print(f"❌ Missing recipient_id or message content")
            return None
        
        original_recipient = recipient_id

        # Convert recipient_id to int if it's a string
        if isinstance(recipient_id, str):
            if recipient_id.isdigit():
                recipient_id = int(recipient_id)
            else:
                # It's a username, convert to user_id
                with get_db_cursor() as (cursor, conn):
                    cursor.execute(
                        "SELECT user_id FROM users WHERE username = %s",
                        (recipient_id,)
                    )
                    user_result = cursor.fetchone()
                    if user_result:
                        recipient_id = user_result[0]
                        print(f"💬 [Server] Converted username '{original_recipient}' to user_id {recipient_id}")
                    else:
                        print(f"❌ [Server] Username '{original_recipient}' not found")
                        return None
        
        # Get existing room or create new one
        room_id = get_or_create_room_id(user_info['user_id'], recipient_id)
        
        # Create message object
        new_message = {
            "sender_id": user_info['user_id'],
            "sender_username": user_info['username'],
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "type": "text",
            "content": message_content,
            "room_id": room_id,
            "recipient_id": recipient_id
        }
        
        # Save to JSON file
        async with chat_log_lock:
            chat_data = load_chat_log()
            conversations = chat_data.setdefault("conversations", {})

            if room_id not in conversations:
                conversations[room_id] = []

            conversations[room_id].append(new_message)
            save_chat_log(chat_data)
        
        print(f"✅ [Message to Room {room_id}] from {user_info['username']} to recipient {recipient_id}")
        
        # Broadcast the new message to both participants
        websocket_message = {
            'type': 'new_message',
            'room_id': room_id,
            'message': new_message
        }
        # Send to recipient's WebSocket connections
        sent_count = await auth_bridge.send_to_user_websockets(
            target_user_id=recipient_id,
            message=websocket_message
        )
        print(f"📤 [Server] Sent to {sent_count} WebSocket connections for user {recipient_id}")
        
        # ENHANCED: Add to HTTP message queue for recipient
        auth_bridge.add_message_for_user(recipient_id, websocket_message)
        print(f"📦 [Server] Added message to HTTP queue for user {recipient_id}")
        
        return new_message
        
    except Exception as e:
        print(f"❌ [Server] Error saving message: {e}")
        import traceback
        traceback.print_exc()
        return None

# 10. BROADCAST FRIENDS UPDATE
async def broadcast_friends_update_to_user(user_id):
    """Send updated friends list to all of user's friend list connections"""
    try:
        # Find all friend list connections for this user
        user_connections = []
        for ws_client in auth_bridge.websocket_clients:
            client_info = auth_bridge.websocket_clients[ws_client]
            if (client_info['user_id'] == user_id and 
                ('auto_friends' in client_info.get('session_id', '') or 
                 'friends' in client_info.get('session_id', '') or
                 client_info.get('session_id', '') == 'unknown')):
                user_connections.append((ws_client, client_info))
        
        if user_connections:
            print(f"📤 [WS] Broadcasting friends update to {len(user_connections)} connections for user {user_id}")
            
            # Get updated friends list
            with get_db_cursor() as (cursor, conn):
                cursor.execute("""
                    SELECT f.friend_id, u.username, f.created_at
                    FROM friendships f
                    JOIN users u ON f.friend_id = u.user_id
                    WHERE f.user_id = %s AND f.status = 'accepted'
                    ORDER BY u.username
                """, (user_id,))
                
                friends = []
                for row in cursor.fetchall():
                    friends.append({
                        'user_id': row[0],
                        'username': row[1],
                        'created_at': str(row[2]) if row[2] else None
                    })
            
            # Send updated friends list to all friend list connections
            friends_update = {
                'type': 'friends_list_response',
                'status': 'success',
                'friends': friends,
                'count': len(friends),
                'timestamp': time.time(),
                'update_reason': 'friend_added'
            }
            
            for ws_client, client_info in user_connections:
                try:
                    await ws_client.send_str(json.dumps(friends_update))
                    print(f"✅ [WS] Sent friends update to session {client_info.get('session_id', 'unknown')}")
                except Exception as e:
                    print(f"❌ [WS] Failed to send friends update: {e}")
                    
    except Exception as e:
        print(f"❌ [WS] Error broadcasting friends update: {e}")

async def serve_auth_interface(request):
    """Serve enhanced HTML interface dengan authentication"""
    client_ip = request.remote
    print(f"🌐 [HTTP] GET / from {client_ip}")
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authenticated Cross-Protocol Bridge</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f0f0; }
            .container { max-width: 1400px; margin: 0 auto; }
            .auth-panel { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .main-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .panel { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .full-width { grid-column: 1 / -1; }
            h1 { text-align: center; margin-bottom: 30px; color: #333; }
            h2 { color: #555; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
            .message-area { 
                background: #f8f9fa; 
                border: 1px solid #dee2e6; 
                padding: 15px; 
                margin: 10px 0; 
                min-height: 200px;
                max-height: 300px;
                overflow-y: auto;
                font-family: monospace;
                font-size: 12px;
                border-radius: 4px;
            }
            .controls { margin: 15px 0; }
            input[type="text"], input[type="password"], textarea, select { 
                width: 100%; 
                padding: 10px; 
                margin: 5px 0; 
                border: 1px solid #ddd; 
                border-radius: 4px;
                font-family: monospace;
                box-sizing: border-box;
            }
            button { 
                padding: 10px 20px; 
                margin: 5px; 
                border: none; 
                border-radius: 4px; 
                cursor: pointer;
                font-weight: bold;
            }
            .btn-primary { background: #007bff; color: white; }
            .btn-success { background: #28a745; color: white; }
            .btn-warning { background: #ffc107; color: black; }
            .btn-danger { background: #dc3545; color: white; }
            .btn-secondary { background: #6c757d; color: white; }
            .status { padding: 8px; margin: 5px 0; border-radius: 4px; font-size: 12px; }
            .status-connected { background: #d4edda; color: #155724; }
            .status-disconnected { background: #f8d7da; color: #721c24; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
            .stat-box { background: #e9ecef; padding: 10px; border-radius: 4px; text-align: center; }
            .message-item { margin: 5px 0; padding: 8px; border-left: 3px solid #007bff; background: white; }
            .from-ws { border-left-color: #28a745; }
            .from-http { border-left-color: #dc3545; }
            .json-input { height: 100px; }
            .hidden { display: none; }
            .user-select { width: 100%; margin: 5px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Authenticated Cross-Protocol Message Bridge</h1>
            
            <!-- Authentication Panel -->
            <div class="auth-panel" id="authPanel">
                <h2>🔑 Authentication</h2>
                <div class="controls">
                    <input type="text" id="authUsername" placeholder="Username">
                    <input type="password" id="authPassword" placeholder="Password">
                    <button class="btn-primary" onclick="login()">Login</button>
                    <button class="btn-success" onclick="register()">Register</button>
                </div>
                <div id="authStatus" class="status status-disconnected">Not authenticated</div>
            </div>
            
            <!-- Main Interface (hidden until authenticated) -->
            <div id="mainInterface" class="hidden">
                <div class="auth-panel">
                    <span id="userInfo"></span>
                    <button class="btn-danger" onclick="logout()">Logout</button>
                </div>
                
                <div class="main-container">
                    <!-- WebSocket Panel -->
                    <div class="panel">
                        <h2>📡 WebSocket Client</h2>
                        <div id="wsStatus" class="status status-disconnected">🔴 WebSocket: Disconnected</div>
                        
                        <div class="controls">
                            <button class="btn-danger" onclick="disconnectWebSocket()">Disconnect</button>
                            <button class="btn-secondary" onclick="clearWSMessages()">Clear</button>
                        </div>
                        
                        <div class="controls">
                            <select id="wsTargetUser" class="user-select">
                                <option value="">Broadcast to all users</option>
                            </select>
                            <input type="text" id="wsMessageInput" placeholder="Message text...">
                            <button class="btn-success" onclick="sendWSMessage()">Send Message</button>
                        </div>
                        
                        <div class="controls">
                            <textarea id="wsJsonInput" class="json-input" placeholder='{"type": "custom", "message": "your message", "target_user_id": null}'></textarea>
                            <button class="btn-success" onclick="sendWSJSON()">Send JSON</button>
                        </div>
                        
                        <div class="message-area" id="wsMessages"></div>
                    </div>
                    
                    <!-- HTTP Panel -->
                    <div class="panel">
                        <h2>🌐 HTTP Client</h2>
                        <div id="httpStatus" class="status status-disconnected">🔴 HTTP Polling: Stopped</div>
                        
                        <div class="controls">
                            <button class="btn-primary" onclick="startHTTPPolling()">Start Polling</button>
                            <button class="btn-danger" onclick="stopHTTPPolling()">Stop Polling</button>
                            <button class="btn-secondary" onclick="clearHTTPMessages()">Clear</button>
                        </div>
                        
                        <div class="controls">
                            <select id="httpTargetUser" class="user-select">
                                <option value="">Broadcast to all users</option>
                            </select>
                            <input type="text" id="httpMessageInput" placeholder="Message to send via HTTP...">
                            <button class="btn-success" onclick="sendHTTPMessage()">Send Message</button>
                        </div>
                        
                        <div class="controls">
                            <textarea id="httpJsonInput" class="json-input" placeholder='{"type": "notification", "message": "Hello!", "target_user_id": null}'></textarea>
                            <button class="btn-success" onclick="sendHTTPJSON()">Send JSON</button>
                        </div>
                        
                        <div class="message-area" id="httpMessages"></div>
                    </div>
                    
                    <!-- Statistics Panel -->
                    <div class="panel full-width">
                        <h2>📊 System Statistics</h2>
                        <div class="stats" id="statsContainer">
                            <div class="stat-box"><strong>Total Messages:</strong> <span id="statTotalMessages">0</span></div>
                            <div class="stat-box"><strong>Active WS Clients:</strong> <span id="statWSClients">0</span></div>
                            <div class="stat-box"><strong>Active HTTP Polls:</strong> <span id="statHTTPPolls">0</span></div>
                            <div class="stat-box"><strong>Registered Users:</strong> <span id="statRegisteredUsers">0</span></div>
                            <div class="stat-box"><strong>Active Sessions:</strong> <span id="statActiveSessions">0</span></div>
                        </div>
                        <button class="btn-warning" onclick="refreshStats()">Refresh Stats</button>
                        <button class="btn-secondary" onclick="refreshUsers()">Refresh Users</button>
                        <div class="controls">
                            <input type="text" id="friendUsername" placeholder="Enter username to add as friend">
                            <button class="btn-success" onclick="addFriend()">Add Friend</button>
                        </div>
                        <div class="controls">
                            <button class="btn-warning" onclick="loadFriendRequests()">Show Friend Requests</button>
                            <div id="friendRequests" style="margin-top: 10px;"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let authToken = null;
            let sessionId = null;
            let currentUser = null;
            let ws = null;
            let httpPolling = false;
            let httpPollTimeout = null;
            
            // Authentication functions
            async function login() {
                const username = document.getElementById('authUsername').value.trim();
                const password = document.getElementById('authPassword').value;
                
                if (!username || !password) {
                    alert('Please enter username and password');
                    return;
                }
                
                try {
                    const response = await fetch('/api/auth', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            type: 'login',
                            username: username,
                            password: password
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        authToken = data.token;
                        sessionId = data.session_id;
                        currentUser = data.user;
                        
                        document.getElementById('authStatus').innerHTML = 
                            `🟢 Authenticated as: ${currentUser.username}`;
                        document.getElementById('authStatus').className = 'status status-connected';
                        
                        showMainInterface();
                        
                        // Clear password field
                        document.getElementById('authPassword').value = '';
                        
                    } else {
                        document.getElementById('authStatus').innerHTML = 
                            `🔴 Login failed: ${data.message}`;
                        document.getElementById('authStatus').className = 'status status-disconnected';
                    }
                    
                } catch (error) {
                    document.getElementById('authStatus').innerHTML = 
                        `🔴 Login error: ${error.message}`;
                    document.getElementById('authStatus').className = 'status status-disconnected';
                }
            }
            
            async function register() {
                const username = document.getElementById('authUsername').value.trim();
                const password = document.getElementById('authPassword').value;
                
                if (!username || !password) {
                    alert('Please enter username and password');
                    return;
                }
                
                if (password.length < 4) {
                    alert('Password must be at least 4 characters long');
                    return;
                }
                
                try {
                    const response = await fetch('/api/auth', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            type: 'register',
                            username: username,
                            password: password
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        authToken = data.token;
                        sessionId = data.session_id;
                        currentUser = data.user;
                        
                        document.getElementById('authStatus').innerHTML = 
                            `🟢 Registered and logged in as: ${currentUser.username}`;
                        document.getElementById('authStatus').className = 'status status-connected';
                        
                        showMainInterface();
                        
                        // Clear password field
                        document.getElementById('authPassword').value = '';
                        
                    } else {
                        document.getElementById('authStatus').innerHTML = 
                            `🔴 Registration failed: ${data.message}`;
                        document.getElementById('authStatus').className = 'status status-disconnected';
                    }
                    
                } catch (error) {
                    document.getElementById('authStatus').innerHTML = 
                        `🔴 Registration error: ${error.message}`;
                    document.getElementById('authStatus').className = 'status status-disconnected';
                }
            }
            
            async function logout() {
                try {
                    await fetch('/api/logout', {
                        method: 'POST',
                        headers: { 
                            'Authorization': `Bearer ${authToken}`,
                            'Content-Type': 'application/json'
                        }
                    });
                } catch (error) {
                    console.error('Logout error:', error);
                }
                
                // Reset client state
                authToken = null;
                sessionId = null;
                currentUser = null;
                
                disconnectWebSocket();
                stopHTTPPolling();
                
                // Show auth panel, hide main interface
                document.getElementById('authPanel').classList.remove('hidden');
                document.getElementById('mainInterface').classList.add('hidden');
                
                document.getElementById('authStatus').innerHTML = '🔴 Not authenticated';
                document.getElementById('authStatus').className = 'status status-disconnected';
            }
            
            function showMainInterface() {
                document.getElementById('authPanel').classList.add('hidden');
                document.getElementById('mainInterface').classList.remove('hidden');
                
                document.getElementById('userInfo').innerHTML = 
                    `Welcome, ${currentUser.username} (ID: ${currentUser.user_id})`;
                
                // Auto-connect WebSocket and start polling
                setTimeout(() => {
                    connectWebSocket();
                    refreshUsers();
                    refreshStats();
                }, 500);
            }
            
            // Utility functions
            function log(message, target = 'both', type = 'info') {
                const timestamp = new Date().toLocaleTimeString();
                const colors = {
                    info: '#007bff',
                    success: '#28a745',
                    error: '#dc3545',
                    warning: '#ffc107'
                };
                
                const logEntry = `<div class="message-item" style="border-left-color: ${colors[type]};">
                    <small>[${timestamp}]</small> ${message}
                </div>`;
                
                if (target === 'ws' || target === 'both') {
                    const wsMessages = document.getElementById('wsMessages');
                    wsMessages.innerHTML += logEntry;
                    wsMessages.scrollTop = wsMessages.scrollHeight;
                }
                
                if (target === 'http' || target === 'both') {
                    const httpMessages = document.getElementById('httpMessages');
                    httpMessages.innerHTML += logEntry;
                    httpMessages.scrollTop = httpMessages.scrollHeight;
                }
                
                console.log(`[${timestamp}] ${message}`);
            }
            
            function getAuthHeaders() {
                return {
                    'Authorization': `Bearer ${authToken}`,
                    'Content-Type': 'application/json'
                };
            }
            
            // WebSocket functions
            function connectWebSocket() {
                if (!authToken) {
                    alert('Please login first');
                    return;
                }
                
                // Prevent multiple connections
                if (ws && ws.readyState === WebSocket.OPEN) {
                    return;
                }
                
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/websocket`;
                
                log(`Connecting to ${wsUrl}...`, 'ws', 'info');
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function() {
                    // Send authentication immediately after connection
                    const authMsg = {
                        token: authToken,
                        session_id: sessionId
                    };
                    ws.send(JSON.stringify(authMsg));
                };
                
                ws.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'auth_success') {
                            log('✅ WebSocket authenticated successfully!', 'ws', 'success');
                            document.getElementById('wsStatus').innerHTML = '🟢 WebSocket: Connected & Authenticated';
                            document.getElementById('wsStatus').className = 'status status-connected';
                        } else if (data.error) {
                            log(`❌ WebSocket error: ${data.error}`, 'ws', 'error');
                        } else {
                            log(`📨 Received: ${JSON.stringify(data, null, 2)}`, 'ws', 'success');
                        }
                    } catch (e) {
                        log(`📨 Received (raw): ${event.data}`, 'ws', 'info');
                    }
                };
                
                ws.onclose = function(event) {
                    log(`❌ WebSocket closed (Code: ${event.code})`, 'ws', 'error');
                    document.getElementById('wsStatus').innerHTML = '🔴 WebSocket: Disconnected';
                    document.getElementById('wsStatus').className = 'status status-disconnected';
                    
                    // Auto-reconnect after 3 seconds if we're still authenticated
                    if (authToken && event.code !== 1000) {
                        log('🔄 Attempting to reconnect in 3 seconds...', 'ws', 'warning');
                        setTimeout(() => {
                            if (authToken) {
                                connectWebSocket();
                            }
                        }, 3000);
                    }
                };
                
                ws.onerror = function(error) {
                    log(`❌ WebSocket error: ${error}`, 'ws', 'error');
                };
            }
            
            function disconnectWebSocket() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }
            
            function sendWSMessage() {
                const input = document.getElementById('wsMessageInput');
                const targetSelect = document.getElementById('wsTargetUser');
                
                if (ws && ws.readyState === WebSocket.OPEN && input.value.trim()) {
                    const message = {
                        type: 'text_message',
                        message: input.value.trim(),
                        target_user_id: targetSelect.value ? parseInt(targetSelect.value) : null,
                        timestamp: Date.now()
                    };
                    
                    ws.send(JSON.stringify(message));
                    log(`📤 Sent: ${JSON.stringify(message)}`, 'ws', 'info');
                    input.value = '';
                } else {
                    alert('WebSocket not connected or message is empty!');
                }
            }
            
            function sendWSJSON() {
                const input = document.getElementById('wsJsonInput');
                if (ws && ws.readyState === WebSocket.OPEN && input.value.trim()) {
                    try {
                        const message = JSON.parse(input.value.trim());
                        ws.send(JSON.stringify(message));
                        log(`📤 Sent JSON: ${JSON.stringify(message)}`, 'ws', 'info');
                        input.value = '';
                    } catch (e) {
                        alert('Invalid JSON format!');
                    }
                } else {
                    alert('WebSocket not connected or JSON is empty!');
                }
            }
            
            function clearWSMessages() {
                document.getElementById('wsMessages').innerHTML = '';
            }
            
            // HTTP functions
            function startHTTPPolling() {
                if (httpPolling || !authToken) return;
                
                httpPolling = true;
                document.getElementById('httpStatus').innerHTML = '🟢 HTTP Polling: Active';
                document.getElementById('httpStatus').className = 'status status-connected';
                
                log('🔄 Started HTTP polling...', 'http', 'info');
                pollForMessages();
            }
            
            function stopHTTPPolling() {
                httpPolling = false;
                if (httpPollTimeout) {
                    clearTimeout(httpPollTimeout);
                    httpPollTimeout = null;
                }
                
                document.getElementById('httpStatus').innerHTML = '🔴 HTTP Polling: Stopped';
                document.getElementById('httpStatus').className = 'status status-disconnected';
                log('⏹️ Stopped HTTP polling', 'http', 'warning');
            }
            
            async function pollForMessages() {
                if (!httpPolling || !authToken) return;
                
                try {
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 35000);
                    
                    const response = await fetch('/api/receive?poll=true', {
                        headers: getAuthHeaders(),
                        signal: controller.signal
                    });
                    clearTimeout(timeoutId);
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.status === 'success' && data.messages.length > 0) {
                        data.messages.forEach(msg => {
                            log(`📨 From WebSocket: ${JSON.stringify(msg, null, 2)}`, 'http', 'success');
                        });
                    } else if (data.status === 'error') {
                        log(`❌ Server error: ${data.error}`, 'http', 'error');
                        if (data.error.includes('Authentication')) {
                            // Token expired, logout
                            logout();
                            return;
                        }
                    }
                    
                    if (httpPolling) {
                        httpPollTimeout = setTimeout(pollForMessages, 500);
                    }
                    
                } catch (error) {
                    if (error.name === 'AbortError') {
                        log('⏱️ Poll timeout, retrying...', 'http', 'warning');
                    } else {
                        log(`❌ Polling error: ${error.message}`, 'http', 'error');
                    }
                    
                    if (httpPolling) {
                        httpPollTimeout = setTimeout(pollForMessages, 3000);
                    }
                }
            }
            
            async function sendHTTPMessage() {
                const input = document.getElementById('httpMessageInput');
                const targetSelect = document.getElementById('httpTargetUser');
                
                if (!input.value.trim()) {
                    alert('Message is empty!');
                    return;
                }
                
                try {
                    const message = {
                        type: 'http_text_message',
                        message: input.value.trim(),
                        target_user_id: targetSelect.value ? parseInt(targetSelect.value) : null,
                        timestamp: Date.now()
                    };
                    
                    const response = await fetch('/api/send', {
                        method: 'POST',
                        headers: getAuthHeaders(),
                        body: JSON.stringify(message)
                    });
                    
                    const data = await response.json();
                    log(`📤 Sent via HTTP: ${JSON.stringify(message)}`, 'http', 'info');
                    log(`✅ Server response: ${JSON.stringify(data)}`, 'http', 'success');
                    
                    input.value = '';
                } catch (error) {
                    log(`❌ Send error: ${error.message}`, 'http', 'error');
                }
            }
            
            async function sendHTTPJSON() {
                const input = document.getElementById('httpJsonInput');
                if (!input.value.trim()) {
                    alert('JSON is empty!');
                    return;
                }
                
                try {
                    const message = JSON.parse(input.value.trim());
                    
                    const response = await fetch('/api/send', {
                        method: 'POST',
                        headers: getAuthHeaders(),
                        body: JSON.stringify(message)
                    });
                    
                    const data = await response.json();
                    log(`📤 Sent JSON via HTTP: ${JSON.stringify(message)}`, 'http', 'info');
                    log(`✅ Server response: ${JSON.stringify(data)}`, 'http', 'success');
                    
                    input.value = '';
                } catch (error) {
                    if (error instanceof SyntaxError) {
                        alert('Invalid JSON format!');
                    } else {
                        log(`❌ Send error: ${error.message}`, 'http', 'error');
                    }
                }
            }
            
            function clearHTTPMessages() {
                document.getElementById('httpMessages').innerHTML = '';
            }
            
            // User and statistics functions
            async function refreshUsers() {
                if (!authToken) return;
                
                try {
                    const response = await fetch('/api/users', {
                        headers: getAuthHeaders()
                    });
                    
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        const wsSelect = document.getElementById('wsTargetUser');
                        const httpSelect = document.getElementById('httpTargetUser');
                        
                        // Clear existing options except first one
                        wsSelect.innerHTML = '<option value="">Broadcast to all users</option>';
                        httpSelect.innerHTML = '<option value="">Broadcast to all users</option>';
                        
                        data.users.forEach(user => {
                            if (user.user_id !== currentUser.user_id) {
                                const option = `<option value="${user.user_id}">${user.username} (ID: ${user.user_id})</option>`;
                                wsSelect.innerHTML += option;
                                httpSelect.innerHTML += option;
                            }
                        });
                    }
                } catch (error) {
                    console.error('Error refreshing users:', error);
                }
            }
            
            async function refreshStats() {
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        document.getElementById('statTotalMessages').textContent = data.stats.total_messages;
                        document.getElementById('statWSClients').textContent = data.stats.active_websocket_clients;
                        document.getElementById('statHTTPPolls').textContent = data.stats.active_http_polls;
                        document.getElementById('statRegisteredUsers').textContent = data.stats.registered_users;
                        document.getElementById('statActiveSessions').textContent = data.stats.active_sessions;
                    }
                } catch (error) {
                    console.error('Stats refresh error:', error);
                }
            }

            async function addFriend() {
                const username = document.getElementById('friendUsername').value.trim();
                
                if (!username) {
                    alert('Please enter username');
                    return;
                }
                
                try {
                    const response = await fetch('/api/add_friend', {
                        method: 'POST',
                        headers: getAuthHeaders(),
                        body: JSON.stringify({ username: username })
                    });
                    
                    const data = await response.json();
                    alert(data.message);
                    
                    if (data.status === 'success') {
                        document.getElementById('friendUsername').value = '';
                    }
                    
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
            
            async function loadFriendRequests() {
                try {
                    const response = await fetch('/api/friend_requests', {
                        headers: getAuthHeaders()
                    });
                    
                    const data = await response.json();
                    const container = document.getElementById('friendRequests');
                    
                    if (data.status === 'success') {
                        if (data.friend_requests.length === 0) {
                            container.innerHTML = '<p>No pending friend requests</p>';
                        } else {
                            let html = '<h4>Pending Friend Requests:</h4>';
                            data.friend_requests.forEach(req => {
                                html += `
                                    <div style="margin: 5px 0; padding: 5px; border: 1px solid #ddd;">
                                        <strong>${req.username}</strong> wants to be your friend
                                        <button class="btn-success" onclick="acceptFriend(${req.user_id}, '${req.username}')" style="margin-left: 10px;">Accept</button>
                                    </div>
                                `;
                            });
                            container.innerHTML = html;
                        }
                    }
                } catch (error) {
                    alert('Error loading friend requests: ' + error.message);
                }
            }                                       

            async function acceptFriend(userId, username) {
                try {
                    const response = await fetch('/api/accept_friend', {
                        method: 'POST',
                        headers: getAuthHeaders(),
                        body: JSON.stringify({ user_id: userId })
                    });
                    
                    const data = await response.json();
                    alert(data.message);
                    
                    if (data.status === 'success') {
                        loadFriendRequests(); // Refresh the list
                    }
                    
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }

            // Enter key support
            document.getElementById('authPassword').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    login();
                }
            });

            // Enter key support
            document.getElementById('addFriend').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    login();
                }
            });

            // Enter key support
            document.getElementById('loadFriendRequests').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    login();
                }
            });
            
            document.getElementById('wsMessageInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendWSMessage();
                }
            });
            
            document.getElementById('httpMessageInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendHTTPMessage();
                }
            });
            
            // Auto-refresh stats every 10 seconds
            setInterval(refreshStats, 10000);
            
            // Initialize
            log('🌐 Page loaded. Please authenticate to continue.', 'both', 'info');
            refreshStats();
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

async def create_app():
    """Create and configure the web application"""
    app = web.Application()
    
    # Setup CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    # --- FIX: Add a static route to serve the uploaded files ---
    # This makes files in the 'uploads' folder accessible via a URL
    # e.g., https://localhost:8443/uploads/images/some_image.jpg
    os.makedirs('uploads', exist_ok=True)
    app.router.add_static('/uploads', path='./uploads', name='uploads')
    
    # Authentication routes
    app.router.add_post('/api/auth', auth_login_register)
    app.router.add_post('/api/logout', auth_logout)
    
    # WebSocket route
    app.router.add_get('/', websocket_handler)
    
    # Authenticated API routes
    app.router.add_post('/api/send', api_send_authenticated_message)
    app.router.add_get('/api/receive', api_receive_authenticated_messages)
    app.router.add_get('/api/users', api_get_users)
    app.router.add_get('/api/stats', api_get_stats)
    app.router.add_post('/api/add_friend', api_add_friend)
    app.router.add_get('/api/friends', api_get_friends)
    app.router.add_get('/api/available_friends', api_get_available_friends)
    app.router.add_post('/api/send_message', api_send_message)
    # app.router.add_get('/api/messages/{contact}', api_get_messages)
    app.router.add_post('/api/rooms/find-or-create', api_find_or_create_private_room) # BARU
    app.router.add_post('/api/send_message', api_send_message) # Sudah diubah
    app.router.add_get('/api/messages/{room_id}', api_get_messages) # URL diubah dari {contact}
    # app.router.add_post('/api/accept_friend', api_accept_friend)
    
    # Web interface
    app.router.add_get('/', serve_auth_interface)
    
    # Add CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app

def create_ssl_context():
    """Create SSL context for HTTPS"""
    import os
    
    possible_paths = [
        ('cert.pem', 'key.pem'),
        ('./cert.pem', './key.pem'),
        (os.path.join(os.getcwd(), 'cert.pem'), os.path.join(os.getcwd(), 'key.pem')),
        (os.path.join(os.path.dirname(__file__), 'cert.pem'), os.path.join(os.path.dirname(__file__), 'key.pem'))
    ]
    
    print(f"🔍 Looking for SSL certificates...")
    
    for cert_path, key_path in possible_paths:
        if os.path.exists(cert_path) and os.path.exists(key_path):
            try:
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_context.load_cert_chain(cert_path, key_path)
                print(f"✅ SSL certificates loaded from {cert_path}")
                return ssl_context
            except Exception as e:
                print(f"❌ Error loading certificates: {e}")
                continue
    
    print("❌ SSL certificates not found!")
    return None

def main():
    """Main function to start the server"""
    print("🔐 Authenticated Cross-Protocol Message Bridge Server")
    print("=" * 60)
    
    # Initialize database
    init_database()
    
    # Create SSL context
    ssl_context = create_ssl_context()
    if not ssl_context:
        print("\n⚠️  Starting HTTP server instead (port 8080)...")
        print("🌐 Auth interface: http://localhost:8080")
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            app = loop.run_until_complete(create_app())
            
            print("\n✅ HTTP Authenticated Bridge Server starting...")
            print("🧪 Login/Register: http://localhost:8080/")
            print("📡 WebSocket: ws://localhost:8080/websocket")
            print("🔑 Auth: POST http://localhost:8080/api/auth")
            print("🌐 Send: POST http://localhost:8080/api/send")
            print("📨 Receive: GET http://localhost:8080/api/receive")
            print("👥 Users: GET http://localhost:8080/api/users")
            print("📊 Stats: GET http://localhost:8080/api/stats")
            print("🛑 Press Ctrl+C to stop\n")
            
            web.run_app(app, host='localhost', port=8080, access_log_format='%r %s %b')
        except Exception as e:
            print(f"❌ Error starting HTTP server: {e}")
        return
    
    print("\n🔐 Starting HTTPS + WebSocket Authenticated Bridge server")
    print("🌐 Auth interface: https://localhost:8443")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        app = loop.run_until_complete(create_app())
        
        print("\n✅ HTTPS Authenticated Bridge Server starting...")
        print("🧪 Login/Register: https://localhost:8443/")
        print("📡 WebSocket: wss://localhost:8443/websocket")
        print("🔑 Auth: POST https://localhost:8443/api/auth")
        print("🌐 Send: POST https://localhost:8443/api/send")
        print("📨 Receive: GET https://localhost:8443/api/receive")
        print("👥 Users: GET https://localhost:8443/api/users")
        print("📊 Stats: GET https://localhost:8443/api/stats")
        print("⚠️  Note: Accept self-signed certificate warning in browser")
        print("🛑 Press Ctrl+C to stop\n")
        
        web.run_app(
            app, 
            host='localhost', 
            port=8443, 
            ssl_context=ssl_context,
            access_log_format='%t %r %s %b'
        )
        
    except Exception as e:
        print(f"❌ Error starting HTTPS server: {e}")

if __name__ == '__main__':
    # Install dependencies:
    # pip install aiohttp aiohttp-cors PyJWT
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Authenticated bridge server stopped by user")
        print("📊 Final statistics:")
        print(f"   Total messages: {auth_bridge.stats['total_messages']}")
        print(f"   Registered users: {auth_bridge.stats['registered_users']}")
        print(f"   Active sessions: {auth_bridge.stats['active_sessions']}")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Install dependencies: pip install aiohttp aiohttp-cors PyJWT")
        print("   2. Make sure cert.pem and key.pem are in the script directory")
        print("   3. Check if ports 8080/8443 are available")