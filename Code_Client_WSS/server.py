# # import asyncio
# # import ssl
# # import json
# # import time
# # import hashlib
# # import sqlite3
# # import os
# # from collections import defaultdict, deque
# # from aiohttp import web, WSMsgType
# # import aiohttp_cors
# # import uuid
# # import weakref
# # from datetime import datetime, timedelta
# # import jwt
# # import psycopg2
# # import pytz
# # import base64

# # # Database setup
# # DATABASE_FILE = 'auth_bridge.db'
# # JWT_SECRET = 'your-secret-key-change-in-production'  # Change this in production!

# # # Chat log setup
# # CHAT_LOG_FILE = 'chat_log.json'
# # chat_log_lock = asyncio.Lock()

# # def load_chat_log():
# #     """Memuat data chat dari file JSON."""
# #     try:
# #         with open(CHAT_LOG_FILE, 'r') as f:
# #             return json.load(f)
# #     except (FileNotFoundError, json.JSONDecodeError):
# #         # Jika file tidak ada atau rusak, kembalikan struktur default
# #         return {"conversations": {}}

# # def save_chat_log(data):
# #     """Menyimpan data chat ke file JSON."""
# #     with open(CHAT_LOG_FILE, 'w') as f:
# #         json.dump(data, f, indent=4)

# # def get_db_connection():
# #     """Get database connection"""
# #     # try:
# #     #     # Coba PostgreSQL dulu
# #     conn = psycopg2.connect(
# #         host="aws-0-ap-southeast-1.pooler.supabase.com",  # Dari screenshot
# #         port=6543,                                        # Bukan 5432!
# #         database="postgres",                              # Dari screenshot
# #         user="postgres.ziymoatadswbppsrsanr",            # Dari screenshot
# #         password="Oriorion21!",              # Ganti dengan password asli
# #         sslmode='require'
# #     )
# #     return conn # , 'postgresql'
# #     # except:
# #     #     # Fallback ke SQLite
# #     #     conn = sqlite3.connect(DATABASE_FILE)
# #     #     conn.row_factory = sqlite3.Row
# #     #     return conn, 'sqlite'

# # # import psycopg2

# # # def get_db_connection():
# # #     """Get local PostgreSQL database connection"""
# # #     try:
# # #         conn = psycopg2.connect(
# # #             host="localhost",       # Localhost for local DB
# # #             port=5432,              # Default PostgreSQL port
# # #             database="postgres",  # Replace with your local DB name
# # #             user="postgres.gacor",      # Replace with your local DB user
# # #             password="indiraalamak"  # Replace with your local DB password
# # #         )
# # #         return conn
# # #     except Exception as e:
# # #         print("Failed to connect to local PostgreSQL:", e)
# # #         return None



# # # def hash_password(password):
# # #     """Hash password using SHA-256"""
# # #     return hashlib.sha256(password.encode()).hexdigest()

# # def init_database():
# #     """Initialize database with all required tables including enhanced messages table"""
# #     conn = get_db_connection()
# #     cursor = conn.cursor()
    
# #     # Create users table matching your schema
# #     cursor.execute('''
# #         CREATE TABLE IF NOT EXISTS users (
# #             user_id SERIAL PRIMARY KEY,
# #             username TEXT UNIQUE NOT NULL,
# #             password_hash TEXT NOT NULL
# #         )
# #     ''')

# #     # Create friends table
# #     cursor.execute('''
# #         CREATE TABLE IF NOT EXISTS friendships (
# #             user_id INTEGER NOT NULL,
# #             friend_id INTEGER NOT NULL,
# #             status TEXT NOT NULL,
# #             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
# #             PRIMARY KEY (user_id, friend_id),
# #             FOREIGN KEY (user_id) REFERENCES users (user_id),
# #             FOREIGN KEY (friend_id) REFERENCES users (user_id)
# #         )
# #     ''')

# #     # Tabel untuk menyimpan informasi room
# #     cursor.execute('''
# #         CREATE TABLE IF NOT EXISTS rooms (
# #             room_id SERIAL PRIMARY KEY,
# #             type VARCHAR(50) NOT NULL, -- 'private' untuk 1-on-1, 'group' untuk grup
# #             room_name VARCHAR(255),
# #             created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
# #         )
# #     ''')

# #     # Tabel untuk menyimpan anggota dari setiap room
# #     cursor.execute('''
# #         CREATE TABLE IF NOT EXISTS room_members (
# #             room_id INTEGER NOT NULL,
# #             user_id INTEGER NOT NULL,
# #             role VARCHAR(50) DEFAULT 'member', -- bisa 'admin' atau 'member'
# #             PRIMARY KEY (room_id, user_id),
# #             FOREIGN KEY (room_id) REFERENCES rooms (room_id) ON DELETE CASCADE,
# #             FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
# #         )
# #     ''')
    
# #     # ENHANCED MESSAGES TABLE - NEW!
# #     cursor.execute('''
# #         CREATE TABLE IF NOT EXISTS messages (
# #             message_id SERIAL PRIMARY KEY,
# #             room_id VARCHAR(255) NOT NULL,
# #             sender_id INTEGER NOT NULL,
# #             sender_username VARCHAR(255) NOT NULL,
# #             recipient_id VARCHAR(255),
# #             content TEXT,
# #             message_type VARCHAR(10) DEFAULT 'text',
# #             file_name VARCHAR(255),
# #             file_data TEXT,  -- Base64 encoded file data
# #             file_size INTEGER,
# #             mime_type VARCHAR(100),
# #             timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
# #             created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
# #             FOREIGN KEY (sender_id) REFERENCES users (user_id)
# #         )
# #     ''')

# #     # Create index for better query performance
# #     cursor.execute('''
# #         CREATE INDEX IF NOT EXISTS idx_messages_room_id ON messages (room_id);
# #     ''')
# #     cursor.execute('''
# #         CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp);
# #     ''')
# #     cursor.execute('''
# #         CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages (sender_id);
# #     ''')
    
# #     conn.commit()
# #     conn.close()

# # def verify_password(password, password_hash):
# #     """Verify password against hash"""
# #     return password == password_hash

# # def create_jwt_token(user_id, username):
# #     """Create JWT token for user session"""
# #     payload = {
# #         'user_id': user_id,
# #         'username': username,
# #         'exp': datetime.now(pytz.UTC) + timedelta(hours=24),  # 24 hour expiry
# #         'iat': datetime.now(pytz.UTC)
# #     }
# #     return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

# # def verify_jwt_token(token):
# #     """Verify JWT token and return user info"""
# #     try:
# #         payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
# #         return payload
# #     except jwt.ExpiredSignatureError:
# #         return None
# #     except jwt.InvalidTokenError:
# #         return None

# # class AuthenticatedMessageBridge:
# #     def __init__(self):
# #         # Store active WebSocket connections with user info
# #         self.websocket_clients = {}  # {ws: {'user_id': int, 'username': str, 'session_id': str}}
        
# #         # Message queues untuk setiap user
# #         self.user_message_queues = defaultdict(lambda: deque(maxlen=100))
        
# #         # HTTP clients yang sedang long-polling per user
# #         self.http_long_poll_clients = {}  # {client_id: {'future': future, 'user_id': int}}
        
# #         # Statistics
# #         self.stats = {
# #             'total_messages': 0,
# #             'active_websocket_clients': 0,
# #             'active_http_polls': 0,
# #             'registered_users': 0,
# #             'active_sessions': 0
# #         }
        
# #         # Update stats on init
# #         self.update_user_stats()
    
# #     def update_user_stats(self):
# #         """Update user statistics from database"""
# #         try:
# #             conn = get_db_connection()
# #             cursor = conn.cursor()
            
# #             # Count registered users
# #             cursor.execute("SELECT COUNT(*) FROM users")
# #             self.stats['registered_users'] = cursor.fetchone()[0]
            
# #             # Count total messages
# #             cursor.execute("SELECT COUNT(*) FROM messages")
# #             self.stats['total_messages'] = cursor.fetchone()[0]
            
# #             conn.close()
# #         except Exception as e:
# #             print(f"❌ Error updating user stats: {e}")
    
# #     def add_websocket_client(self, ws, user_id, username, session_id):
# #         """Add authenticated WebSocket client"""
# #         self.websocket_clients[ws] = {
# #             'user_id': user_id,
# #             'username': username,
# #             'session_id': session_id,
# #             'connected_at': time.time()
# #         }
# #         self.stats['active_websocket_clients'] = len(self.websocket_clients)
# #         print(f"🔌 WebSocket client connected: {username} (ID: {user_id})")
    
# #     def remove_websocket_client(self, ws):
# #         """Remove WebSocket client"""
# #         if ws in self.websocket_clients:
# #             user_info = self.websocket_clients[ws]
# #             del self.websocket_clients[ws]
# #             self.stats['active_websocket_clients'] = len(self.websocket_clients)
# #             print(f"🔌 WebSocket client disconnected: {user_info['username']}")
    
# #     def get_user_from_ws(self, ws):
# #         """Get user info from WebSocket connection"""
# #         return self.websocket_clients.get(ws)
    
# #     async def send_to_user_websockets(self, target_user_id, message, exclude_ws=None):
# #         """Send message to specific user's WebSocket connections"""
# #         sent_count = 0
# #         closed_clients = set()
        
# #         # Convert target_user_id to int for comparison
# #         target_user_id = int(target_user_id) if isinstance(target_user_id, str) and target_user_id.isdigit() else target_user_id
        
# #         for ws, user_info in self.websocket_clients.items():
# #             if user_info['user_id'] == target_user_id and ws != exclude_ws:
# #                 try:
# #                     if ws.closed:
# #                         closed_clients.add(ws)
# #                     else:
# #                         await ws.send_str(json.dumps(message))
# #                         sent_count += 1
# #                         print(f"📤 [WS] Sent to {user_info['username']}: {message}")
# #                 except Exception as e:
# #                     print(f"❌ Error sending to WebSocket {user_info['username']}: {e}")
# #                     closed_clients.add(ws)
        
# #         # Clean up closed connections
# #         for ws in closed_clients:
# #             self.remove_websocket_client(ws)
        
# #         return sent_count
    
# #     async def broadcast_to_all_websockets(self, message, exclude_ws=None):
# #         """Broadcast message to all WebSocket connections"""
# #         sent_count = 0
# #         closed_clients = set()
        
# #         for ws, user_info in self.websocket_clients.items():
# #             if ws != exclude_ws:
# #                 try:
# #                     if ws.closed:
# #                         closed_clients.add(ws)
# #                     else:
# #                         await ws.send_str(json.dumps(message))
# #                         sent_count += 1
# #                 except Exception as e:
# #                     print(f"❌ Error broadcasting to {user_info['username']}: {e}")
# #                     closed_clients.add(ws)
        
# #         # Clean up closed connections
# #         for ws in closed_clients:
# #             self.remove_websocket_client(ws)
        
# #         return sent_count
    
# #     def add_message_for_user(self, target_user_id, message):
# #         """Add message to queue for specific user's HTTP clients"""
# #         enhanced_message = {
# #             **message,
# #             'bridge_id': str(uuid.uuid4()),
# #             'bridge_timestamp': time.time(),
# #             'target_user_id': target_user_id
# #         }
        
# #         self.user_message_queues[target_user_id].append(enhanced_message)
# #         self.stats['total_messages'] += 1
# #         print(f"📦 [Bridge] Queued message for user {target_user_id}: {enhanced_message}")
        
# #         # Notify waiting HTTP clients for this user
# #         self._notify_user_http_clients(target_user_id, enhanced_message)
    
# #     def get_messages_for_user(self, user_id, since_timestamp=None):
# #         """Get messages for specific user"""
# #         messages = list(self.user_message_queues[user_id])
# #         if since_timestamp:
# #             messages = [msg for msg in messages if msg['bridge_timestamp'] > since_timestamp]
# #         return messages
    
# #     def _notify_user_http_clients(self, user_id, message):
# #         """Notify waiting HTTP long-poll clients for specific user"""
# #         for client_id, client_info in list(self.http_long_poll_clients.items()):
# #             if client_info['user_id'] == user_id and not client_info['future'].done():
# #                 client_info['future'].set_result([message])
# #                 del self.http_long_poll_clients[client_id]
    
# #     async def wait_for_user_messages(self, client_id, user_id, timeout=30):
# #         """Long polling untuk HTTP clients untuk specific user"""
# #         future = asyncio.Future()
# #         self.http_long_poll_clients[client_id] = {
# #             'future': future,
# #             'user_id': user_id
# #         }
# #         self.stats['active_http_polls'] = len(self.http_long_poll_clients)
        
# #         try:
# #             messages = await asyncio.wait_for(future, timeout=timeout)
# #             return messages
# #         except asyncio.TimeoutError:
# #             self.http_long_poll_clients.pop(client_id, None)
# #             self.stats['active_http_polls'] = len(self.http_long_poll_clients)
# #             return []
# #         except asyncio.CancelledError:
# #             self.http_long_poll_clients.pop(client_id, None)
# #             self.stats['active_http_polls'] = len(self.http_long_poll_clients)
# #             return []
# #         except Exception as e:
# #             self.http_long_poll_clients.pop(client_id, None)
# #             self.stats['active_http_polls'] = len(self.http_long_poll_clients)
# #             print(f"❌ [Bridge] Error in wait_for_user_messages: {e}")
# #             return []

# # # Global authenticated bridge instance
# # auth_bridge = AuthenticatedMessageBridge()

# # def get_user_from_token(request):
# #     """Extract user info from JWT token in request"""
# #     auth_header = request.headers.get('Authorization', '')
# #     if not auth_header.startswith('Bearer '):
# #         return None
    
# #     token = auth_header[7:]  # Remove 'Bearer ' prefix
# #     return verify_jwt_token(token)


# # async def auth_login_register(request):
# #     """Handle login and registration requests"""
# #     try:
# #         data = await request.json()
# #         action_type = data.get('type')  # 'login' or 'register'
# #         username = data.get('username', '').strip()
# #         password = data.get('password', '')
        
# #         if not username or not password:
# #             return web.json_response({
# #                 'status': 'error',
# #                 'message': 'Username and password are required'
# #             }, status=400)
        
# #         if action_type not in ['login', 'register']:
# #             return web.json_response({
# #                 'status': 'error',
# #                 'message': 'Type must be "login" or "register"'
# #             }, status=400)
        
# #         # conn = sqlite3.connect(DATABASE_FILE)
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
        
# #         if action_type == 'register':
# #             # Registration logic
# #             try:
# #                 # password_hash = hash_password(password)
# #                 cursor.execute(
# #                     "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
# #                     (username, password)
# #                 )
# #                 user_id = cursor.lastrowid
# #                 conn.commit()
                
# #                 print(f"✅ [Auth] New user registered: {username} (ID: {user_id})")
                
# #                 # Create session
# #                 token = create_jwt_token(user_id, username)
# #                 session_id = str(uuid.uuid4())
# #                 expires_at = datetime.now(pytz.UTC) + timedelta(hours=24)
                
# #                 response_data = {
# #                     'status': 'success',
# #                     'message': 'Registration successful',
# #                     'user': {
# #                         'user_id': user_id,
# #                         'username': username
# #                     },
# #                     'token': token,
# #                     'session_id': session_id
# #                 }
                
# #             except psycopg2.IntegrityError:
# #                 response_data = {
# #                     'status': 'error',
# #                     'message': 'Username already exists'
# #                 }
                
# #         else:  # login
# #             # Login logic
# #             cursor.execute(
# #                 "SELECT user_id, username, password_hash FROM users WHERE username = %s",
# #                 (username,)
# #             )
# #             user = cursor.fetchone()
            
# #             if user and verify_password(password, user[2]):
# #                 user_id, db_username, _ = user
                
# #                 print(f"✅ [Auth] User logged in: {username} (ID: {user_id})")
                
# #                 # Create session
# #                 token = create_jwt_token(user_id, username)
# #                 session_id = str(uuid.uuid4())
# #                 expires_at = datetime.now(pytz.UTC) + timedelta(hours=24)
        
                
# #                 print(f"✅ [Auth] User logged in: {username} (ID: {user_id})")
                
# #                 response_data = {
# #                     'status': 'success',
# #                     'message': 'Login successful',
# #                     'user': {
# #                         'user_id': user_id,
# #                         'username': db_username
# #                     },
# #                     'token': token,
# #                     'session_id': session_id
# #                 }
                
# #             else:
# #                 response_data = {
# #                     'status': 'error',
# #                     'message': 'Invalid username or password'
# #                 }
        
# #         conn.close()
# #         auth_bridge.update_user_stats()
        
# #         print(f"📨 [Auth] {action_type.title()} request from {request.remote}: {response_data['status']}")
# #         return web.json_response(response_data)
        
# #     except Exception as e:
# #         print(f"❌ [Auth] Error in {action_type}: {e}")
# #         return web.json_response({
# #             'status': 'error',
# #             'message': 'Internal server error'
# #         }, status=500)

# # async def auth_logout(request):
# #     """Handle logout requests"""
# #     user_info = get_user_from_token(request)
# #     if not user_info:
# #         return web.json_response({
# #             'status': 'error',
# #             'message': 'Not authenticated'
# #         }, status=401)
    
# #     try:
# #         # Mark session as inactive
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
# #         # cursor.execute(
# #         #     "UPDATE user_sessions SET is_active = FALSE WHERE user_id = ? AND is_active = TRUE",
# #         #     (user_info['user_id'],)
# #         # )
# #         conn.commit()
# #         conn.close()
        
# #         print(f"✅ [Auth] User logged out: {user_info['username']}")
        
# #         return web.json_response({
# #             'status': 'success',
# #             'message': 'Logout successful'
# #         })
        
# #     except Exception as e:
# #         print(f"❌ [Auth] Logout error: {e}")
# #         return web.json_response({
# #             'status': 'error',
# #             'message': 'Logout failed'
# #         }, status=500)

# # # ENHANCED MESSAGE SAVING - NEW!
# # async def save_message_to_database(user_info, message_data):
# #     """Save message to database with file support"""
# #     try:
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
        
# #         # Extract message info
# #         recipient_id = str(message_data.get("recipient_id"))  # Ensure string consistency
# #         room_id = message_data.get("room_id")
# #         content = message_data.get("message", "")
# #         message_type = message_data.get("message_type", "text")
        
# #         # File-specific fields
# #         file_name = message_data.get("file_name")
# #         file_data = message_data.get("file_data")  # Base64 encoded
# #         file_size = message_data.get("file_size")
# #         mime_type = message_data.get("mime_type")
        
# #         # Insert message into database
# #         cursor.execute("""
# #             INSERT INTO messages (
# #                 room_id, sender_id, sender_username, recipient_id, 
# #                 content, message_type, file_name, file_data, file_size, mime_type
# #             ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
# #             RETURNING message_id, timestamp
# #         """, (
# #             room_id, user_info['user_id'], user_info['username'], recipient_id,
# #             content, message_type, file_name, file_data, file_size, mime_type
# #         ))
        
# #         result = cursor.fetchone()
# #         message_id, timestamp = result
        
# #         conn.commit()
# #         conn.close()
        
# #         # Create enhanced message object
# #         enhanced_message = {
# #             "message_id": message_id,
# #             "sender_id": user_info['user_id'],
# #             "sender_username": user_info['username'],
# #             "timestamp": timestamp.isoformat(),
# #             "content": content,
# #             "message_type": message_type,
# #             "room_id": room_id,
# #             "recipient_id": recipient_id
# #         }
        
# #         # Add file info if present
# #         if message_type in ['image', 'file']:
# #             enhanced_message.update({
# #                 "file_name": file_name,
# #                 "file_data": file_data,
# #                 "file_size": file_size,
# #                 "mime_type": mime_type
# #             })
        
# #         print(f"✅ [DB] Saved {message_type} message to database: ID {message_id}")
# #         if message_type in ['image', 'file']:
# #             size_mb = file_size / (1024 * 1024) if file_size else 0
# #             print(f"✅ [DB] File details: {file_name} ({size_mb:.2f} MB, {mime_type})")
        
# #         return enhanced_message
        
# #     except Exception as e:
# #         print(f"❌ [DB] Error saving message to database: {e}")
# #         import traceback
# #         traceback.print_exc()
# #         return None

# # async def get_messages_from_database(room_id, limit=100):
# #     """Get messages from database for a specific room"""
# #     try:
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
        
# #         cursor.execute("""
# #             SELECT message_id, sender_id, sender_username, recipient_id, content, 
# #                    message_type, file_name, file_data, file_size, mime_type, timestamp
# #             FROM messages 
# #             WHERE room_id = %s 
# #             ORDER BY timestamp ASC 
# #             LIMIT %s
# #         """, (room_id, limit))
        
# #         messages = []
# #         for row in cursor.fetchall():
# #             message = {
# #                 "message_id": row[0],
# #                 "sender_id": row[1],
# #                 "sender_username": row[2],
# #                 "recipient_id": row[3],
# #                 "content": row[4],
# #                 "message_type": row[5],
# #                 "timestamp": row[10].isoformat(),
# #                 "room_id": room_id
# #             }
            
# #             # Add file data if present
# #             if row[5] in ['image', 'file']:  # message_type
# #                 message.update({
# #                     "file_name": row[6],
# #                     "file_data": row[7],
# #                     "file_size": row[8],
# #                     "mime_type": row[9]
# #                 })
            
# #             messages.append(message)
        
# #         conn.close()
# #         print(f"📚 [DB] Retrieved {len(messages)} messages from room {room_id}")
# #         return messages
        
# #     except Exception as e:
# #         print(f"❌ [DB] Error getting messages from database: {e}")
# #         return []




# # # --- NEW CHAT MESSAGING API ENDPOINTS ---
# # async def api_send_message(request):
# #     """Sends a message, creating a new room if needed."""
# #     user_info = get_user_from_token(request)
# #     if not user_info:
# #         return web.json_response({'status': 'error', 'message': 'Authentication required'}, status=401)
    
# #     try:
# #         data = await request.json()
# #         room_id = data.get('room_id')
# #         message_content = data.get('message', '').strip()
# #         recipient_id = data.get('recipient_id')  # The friend you're sending to

# #         if not message_content or not recipient_id:
# #             return web.json_response({'status': 'error', 'message': 'Message and recipient are required'}, status=400)

# #         # If room_id is not provided, create a new one
# #         if not room_id:
# #             room_id = str(uuid.uuid4())  # Generate a new roomId

# #         new_message = {
# #             "sender_id": user_info['user_id'],
# #             "sender_username": user_info['username'],
# #             "timestamp": datetime.now(pytz.UTC).isoformat(),  # Store in UTC
# #             "type": "text",
# #             "content": message_content,
# #             "room_id": room_id,
# #             "recipient_id": recipient_id
# #         }

# #         async with chat_log_lock:
# #             chat_data = load_chat_log()
# #             conversations = chat_data.setdefault("conversations", {})

# #             if room_id not in conversations:
# #                 conversations[room_id] = []

# #             conversations[room_id].append(new_message)
# #             save_chat_log(chat_data)

# #         print(f"✅ [Message to Room {room_id}] from {user_info['username']}")

# #         # Broadcast the new message to both participants
# #         websocket_message = {
# #             'type': 'new_message',
# #             'room_id': room_id,
# #             'message': new_message
# #         }
# #         await auth_bridge.broadcast_to_all_websockets(websocket_message)
           
# #         return web.json_response({'status': 'success', 'room_id': room_id, 'message': new_message})

# #     except Exception as e:
# #         print(f"❌ [API Send Message] Error: {e}")
# #         return web.json_response({'status': 'error', 'message': 'Internal server error'}, status=500)

       
# # async def api_get_messages(request):
# #     """Get message history from database for a room"""
# #     user_info = get_user_from_token(request)
# #     if not user_info:
# #         return web.json_response({'status': 'error', 'message': 'Authentication required'}, status=401)
    
# #     try:
# #         room_id = request.match_info.get('room_id', '').strip()
# #         if not room_id:
# #             return web.json_response({'status': 'error', 'message': 'room_id is required in URL'}, status=400)
        
# #         # Get messages from database first (new system)
# #         messages_from_db = await get_messages_from_database(room_id)
        
# #         # Fallback to JSON file if no database messages (backward compatibility)
# #         if not messages_from_db:
# #             async with chat_log_lock:
# #                 chat_data = load_chat_log()
# #                 messages_from_json = chat_data.get("conversations", {}).get(room_id, [])
            
# #             # Format JSON messages to match database format
# #             messages_to_return = []
# #             for msg in messages_from_json:
# #                 formatted_msg = {
# #                     "sender_id": msg.get("sender_id"),
# #                     "sender_username": msg.get("sender_username"),
# #                     "content": msg.get("content"),
# #                     "message_type": msg.get("type", "text"),
# #                     "timestamp": msg.get("timestamp"),
# #                     "room_id": room_id,
# #                     "recipient_id": msg.get("recipient_id")
# #                 }
# #                 messages_to_return.append(formatted_msg)
# #         else:
# #             messages_to_return = messages_from_db
        
# #         # Format timestamps for display
# #         for msg in messages_to_return:
# #             try:
# #                 if isinstance(msg["timestamp"], str):
# #                     iso_timestamp = datetime.fromisoformat(msg["timestamp"].replace('Z', '+00:00'))
# #                     msg["timestamp"] = iso_timestamp.strftime("%I:%M %p").lower()
# #             except:
# #                 pass
        
# #         return web.json_response({
# #             'status': 'success',
# #             'room_id': room_id,
# #             'messages': messages_to_return,
# #             'source': 'database' if messages_from_db else 'json_file'
# #         })
        
# #     except Exception as e:
# #         print(f"❌ [API Get Messages] Error: {e}")
# #         return web.json_response({'status': 'error', 'message': 'Internal server error'}, status=500)

# # async def api_send_authenticated_message(request):
# #     """HTTP endpoint untuk mengirim message dengan authentication"""
# #     user_info = get_user_from_token(request)
# #     if not user_info:
# #         return web.json_response({
# #             'status': 'error',
# #             'message': 'Authentication required'
# #         }, status=401)
    
# #     try:
# #         data = await request.json()
# #         print(f"📨 [HTTP] Authenticated message from {user_info['username']}: {data}")
        
# #         # Enhanced message with sender info
# #         enhanced_data = {
# #             **data,
# #             "sender": {
# #                 "user_id": user_info['user_id'],
# #                 "username": user_info['username']
# #             },
# #             "timestamp": time.time(),
# #             "protocol": "http"
# #         }
        
# #         # Determine target
# #         target_user_id = data.get('target_user_id')
        
# #         if target_user_id:
# #             # Send to specific user
# #             auth_bridge.add_message_for_user(target_user_id, enhanced_data)
# #             sent_count = await auth_bridge.send_to_user_websockets(target_user_id, enhanced_data)
# #         else:
# #             # Broadcast to all
# #             sent_count = await auth_bridge.broadcast_to_all_websockets(enhanced_data)
        
# #         response_data = {
# #             "status": "success",
# #             "message": "Message sent successfully",
# #             "sent_to_websocket_clients": sent_count,
# #             "bridged_message": enhanced_data,
# #             "timestamp": time.time()
# #         }
        
# #         return web.json_response(response_data)
        
# #     except Exception as e:
# #         print(f"❌ [HTTP] Error: {e}")
# #         return web.json_response({
# #             "status": "error",
# #             "error": str(e)
# #         }, status=500)

# # async def api_receive_authenticated_messages(request):
# #     """HTTP endpoint untuk menerima messages dengan authentication"""
# #     user_info = get_user_from_token(request)
# #     if not user_info:
# #         return web.json_response({
# #             'status': 'error',
# #             'message': 'Authentication required'
# #         }, status=401)
    
# #     client_id = f"http_{uuid.uuid4().hex[:8]}"
# #     user_id = user_info['user_id']
    
# #     try:
# #         since_param = request.query.get('since')
# #         since_timestamp = float(since_param) if since_param else None
# #     except (ValueError, TypeError):
# #         since_timestamp = None
    
# #     poll = request.query.get('poll', 'false').lower() == 'true'
    
# #     print(f"📡 [HTTP] User {user_info['username']} requesting messages (poll={poll})")
    
# #     try:
# #         if poll:
# #             messages = await auth_bridge.wait_for_user_messages(client_id, user_id, timeout=30)
# #         else:
# #             messages = auth_bridge.get_messages_for_user(user_id, since_timestamp)
        
# #         response_data = {
# #             "status": "success",
# #             "messages": messages,
# #             "count": len(messages),
# #             "user_id": user_id,
# #             "timestamp": time.time()
# #         }
        
# #         if messages:
# #             print(f"📤 [HTTP] Sending {len(messages)} messages to {user_info['username']}")
        
# #         return web.json_response(response_data)
        
# #     except Exception as e:
# #         print(f"❌ [HTTP] Error for {user_info['username']}: {e}")
# #         return web.json_response({
# #             "status": "error",
# #             "error": str(e)
# #         }, status=500)

# # async def api_get_users(request):
# #     """Get list of registered users (for targeting messages)"""
# #     user_info = get_user_from_token(request)
# #     if not user_info:
# #         return web.json_response({
# #             'status': 'error',
# #             'message': 'Authentication required'
# #         }, status=401)
    
# #     try:
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
# #         cursor.execute("SELECT user_id, username FROM users ORDER BY username")
# #         users = [{'user_id': row[0], 'username': row[1]} for row in cursor.fetchall()]
# #         conn.close()
        
# #         return web.json_response({
# #             'status': 'success',
# #             'users': users,
# #             'current_user': user_info
# #         })
        
# #     except Exception as e:
# #         return web.json_response({
# #             'status': 'error',
# #             'error': str(e)
# #         }, status=500)

# # async def api_add_friend(request):
# #     """Add friend by username, creating a bidirectional friendship."""
# #     user_info = get_user_from_token(request)
# #     if not user_info:
# #         return web.json_response({'status': 'error', 'message': 'Authentication required'}, status=401)
   
# #     try:
# #         data = await request.json()
# #         friend_username = data.get('username', '').strip()
       
# #         if not friend_username:
# #             return web.json_response({'status': 'error', 'message': 'Friend username is required'}, status=400)
       
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
       
# #         cursor.execute("SELECT user_id FROM users WHERE username = %s", (friend_username,))
# #         friend = cursor.fetchone()
       
# #         if not friend:
# #             conn.close()
# #             return web.json_response({'status': 'error', 'message': 'User not found'})
       
# #         friend_id = friend[0]
# #         user_id = user_info['user_id']
       
# #         if friend_id == user_id:
# #             conn.close()
# #             return web.json_response({'status': 'error', 'message': 'Cannot add yourself as friend'})
       
# #         cursor.execute("SELECT status FROM friendships WHERE user_id = %s AND friend_id = %s", (user_id, friend_id))
# #         existing = cursor.fetchone()
       
# #         if existing:
# #             conn.close()
# #             return web.json_response({'status': 'error', 'message': f'Friend request already exists with status: {existing[0]}'})
       
# #         # --- FIX: Insert two records for a mutual friendship ---
# #         # Record: You added them
# #         cursor.execute(
# #             "INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, %s)",
# #             (user_id, friend_id, 'accepted')
# #         )
# #         # Record: They added you
# #         cursor.execute(
# #             "INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, %s)",
# #             (friend_id, user_id, 'accepted')
# #         )
       
# #         conn.commit()
# #         conn.close()
       
# #         print(f"✅ [Friend] {user_info['username']} and {friend_username} are now friends.")
       
# #         return web.json_response({
# #             'status': 'success',
# #             'message': f'You are now friends with {friend_username}'
# #         })
       
# #     except Exception as e:
# #         print(f"❌ [Friend] Error: {e}")
# #         return web.json_response({'status': 'error', 'message': 'Internal server error'}, status=500)

# # async def api_get_friends(request):
# #     """Get list of friend"""
# #     user_info = get_user_from_token(request)
# #     if not user_info:
# #         return web.json_response({
# #             'status': 'error',
# #             'message': 'Authentication required'
# #         }, status=401)
    
# #     try:
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
        
# #         # Get accepted friend
# #         cursor.execute("""
# #             SELECT f.user_id, u.username, f.created_at 
# #             FROM friendships f 
# #             JOIN users u ON f.user_id = u.user_id 
# #             WHERE f.friend_id = %s AND f.status = 'accepted'
# #         """, (user_info['user_id'],))
        
# #         friends = []
# #         for row in cursor.fetchall():
# #             friends.append({
# #                 'user_id': row[0],
# #                 'username': row[1],
# #                 'created_at': str(row[2])
# #             })
        
# #         conn.close()
        
# #         return web.json_response({
# #             'status': 'success',
# #             'friends': friends,
# #             'count': len(friends)
# #         })
        
# #     except Exception as e:
# #         return web.json_response({
# #             'status': 'error',
# #             'error': str(e)
# #         }, status=500)

# # async def handle_get_friends_websocket(ws, user_info):
# #     """Handle get friends list via WebSocket"""
# #     try:
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
        
# #         # Get all friends where current user is the one who has friends
# #         cursor.execute("""
# #             SELECT f.friend_id, u.username, f.created_at 
# #             FROM friendships f 
# #             JOIN users u ON f.friend_id = u.user_id 
# #             WHERE f.user_id = %s AND f.status = 'accepted'
# #             ORDER BY u.username
# #         """, (user_info['user_id'],))
        
# #         friends = []
# #         for row in cursor.fetchall():
# #             friends.append({
# #                 'user_id': row[0],
# #                 'username': row[1],
# #                 'created_at': str(row[2])
# #             })
        
# #         conn.close()
        
# #         response = {
# #             'type': 'friends_list_response',
# #             'status': 'success',
# #             'friends': friends,
# #             'count': len(friends),
# #             'timestamp': time.time()
# #         }
        
# #         await ws.send_str(json.dumps(response))
# #         print(f"📋 [WS] Sent friends list to {user_info['username']}: {len(friends)} friends")
        
# #     except Exception as e:
# #         error_response = {
# #             'type': 'friends_list_response',
# #             'status': 'error',
# #             'message': f'Failed to load friends: {str(e)}',
# #             'timestamp': time.time()
# #         }
# #         await ws.send_str(json.dumps(error_response))

# # async def handle_search_user_websocket(ws, user_info, data):
# #     """Handle user search via WebSocket"""
# #     try:
# #         search_username = data.get('username', '').strip()
        
# #         if not search_username:
# #             error_response = {
# #                 'type': 'search_user_response',
# #                 'status': 'error',
# #                 'message': 'Username is required for search',
# #                 'timestamp': time.time()
# #             }
# #             await ws.send_str(json.dumps(error_response))
# #             return
        
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
        
# #         # Search for user by username
# #         cursor.execute(
# #             "SELECT user_id, username FROM users WHERE username = %s",
# #             (search_username,)
# #         )
# #         user = cursor.fetchone()
        
# #         conn.close()
        
# #         if user:
# #             user_id, username = user
# #             success_response = {
# #                 'type': 'search_user_response',
# #                 'status': 'success',
# #                 'user': {
# #                     'user_id': user_id,
# #                     'username': username
# #                 },
# #                 'timestamp': time.time()
# #             }
# #             await ws.send_str(json.dumps(success_response))
# #             print(f"✅ [WS] User search: Found {username} for {user_info['username']}")
# #         else:
# #             error_response = {
# #                 'type': 'search_user_response',
# #                 'status': 'error',
# #                 'message': f'User "{search_username}" not found',
# #                 'timestamp': time.time()
# #             }
# #             await ws.send_str(json.dumps(error_response))
# #             print(f"❌ [WS] User search: {search_username} not found")
        
# #     except Exception as e:
# #         print(f"❌ [WS] User search error: {e}")
# #         error_response = {
# #             'type': 'search_user_response',
# #             'status': 'error',
# #             'message': f'Search failed: {str(e)}',
# #             'timestamp': time.time()
# #         }
# #         await ws.send_str(json.dumps(error_response))

# # async def handle_friend_websocket_message(ws, user_info, data):
# #     """Handle friend-related WebSocket messages"""
# #     message_type = data.get('type')
    
# #     try:
# #         if message_type == 'add_friend':
# #             await handle_add_friend_websocket(ws, user_info, data)
# #         elif message_type == 'search_user':
# #             await handle_search_user_websocket(ws, user_info, data)
# #         else:
# #             # Return unhandled message
# #             return False
# #         return True
# #     except Exception as e:
# #         error_response = {
# #             'type': 'error',
# #             'message': f'Error handling {message_type}: {str(e)}',
# #             'timestamp': time.time()
# #         }
# #         await ws.send_str(json.dumps(error_response))
# #         return True

# # async def handle_add_friend_websocket(ws, user_info, data):
# #     """Handle add friend via WebSocket"""
# #     try:
# #         friend_username = data.get('username', '').strip()
        
# #         if not friend_username:
# #             error_response = {
# #                 'type': 'add_friend_response',
# #                 'status': 'error',
# #                 'message': 'Friend username is required',
# #                 'timestamp': time.time()
# #             }
# #             await ws.send_str(json.dumps(error_response))
# #             return
        
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
        
# #         # Find friend by username
# #         cursor.execute(
# #             "SELECT user_id FROM users WHERE username = %s",
# #             (friend_username,)
# #         )
# #         friend = cursor.fetchone()
        
# #         if not friend:
# #             error_response = {
# #                 'type': 'add_friend_response',
# #                 'status': 'error',
# #                 'message': 'User not found',
# #                 'timestamp': time.time()
# #             }
# #             await ws.send_str(json.dumps(error_response))
# #             conn.close()
# #             return
        
# #         friend_id = friend[0]
        
# #         if friend_id == user_info['user_id']:
# #             error_response = {
# #                 'type': 'add_friend_response',
# #                 'status': 'error',
# #                 'message': 'Cannot add yourself as friend',
# #                 'timestamp': time.time()
# #             }
# #             await ws.send_str(json.dumps(error_response))
# #             conn.close()
# #             return
        
# #         # Check if friendship already exists (either direction)
# #         cursor.execute(
# #             "SELECT status FROM friendships WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)",
# #             (user_info['user_id'], friend_id, friend_id, user_info['user_id'])
# #         )
# #         existing = cursor.fetchone()
        
# #         if existing:
# #             error_response = {
# #                 'type': 'add_friend_response',
# #                 'status': 'error',
# #                 'message': f'Already friends with {friend_username}',
# #                 'timestamp': time.time()
# #             }
# #             await ws.send_str(json.dumps(error_response))
# #             conn.close()
# #             return
        
# #         # Add bidirectional friendship with accepted status (auto-accept)
# #         # User -> Friend
# #         cursor.execute(
# #             "INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, %s)",
# #             (user_info['user_id'], friend_id, 'accepted')
# #         )
        
# #         # Friend -> User (bidirectional)
# #         cursor.execute(
# #             "INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, %s)",
# #             (friend_id, user_info['user_id'], 'accepted')
# #         )
        
# #         conn.commit()
# #         conn.close()
        
# #         success_response = {
# #             'type': 'add_friend_response',
# #             'status': 'success',
# #             'message': f'Successfully added {friend_username} as friend',
# #             'username': friend_username,
# #             'timestamp': time.time()
# #         }
        
# #         await ws.send_str(json.dumps(success_response))
# #         print(f"✅ [WS] {user_info['username']} added {friend_username} as friend (bidirectional)")
        
# #     except Exception as e:
# #         error_response = {
# #             'type': 'add_friend_response',
# #             'status': 'error',
# #             'message': f'Internal server error: {str(e)}',
# #             'timestamp': time.time()
# #         }
# #         await ws.send_str(json.dumps(error_response))


# # async def handle_websocket_login(ws, data):
# #     """Handle login request via WebSocket (before authentication)"""
# #     try:
# #         username = data.get('username', '').strip()
# #         password = data.get('password', '')
        
# #         if not username or not password:
# #             error_response = {
# #                 'type': 'login_response',
# #                 'status': 'error',
# #                 'message': 'Username and password are required'
# #             }
# #             await ws.send_str(json.dumps(error_response))
# #             return
        
# #         # Use the same login logic as your HTTP endpoint
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
        
# #         try:
# #             # Find user by username
# #             cursor.execute(
# #                 "SELECT user_id, username, password_hash FROM users WHERE username = %s",
# #                 (username,)
# #             )
# #             user = cursor.fetchone()
            
# #             if user and verify_password(password, user[2]):
# #                 user_id, db_username, _ = user
                
# #                 print(f"✅ [WS-Auth] User logged in: {username} (ID: {user_id})")
                
# #                 # Create JWT token
# #                 token = create_jwt_token(user_id, username)
# #                 session_id = str(uuid.uuid4())
                
# #                 # Send success response
# #                 success_response = {
# #                     'type': 'login_response',
# #                     'status': 'success',
# #                     'message': 'Login successful',
# #                     'user': {
# #                         'user_id': user_id,
# #                         'username': db_username
# #                     },
# #                     'token': token,
# #                     'session_id': session_id
# #                 }
                
# #                 await ws.send_str(json.dumps(success_response))
# #                 print(f"📤 [WS-Auth] Login success sent to {username}")
                
# #             else:
# #                 # Invalid credentials
# #                 error_response = {
# #                     'type': 'login_response',
# #                     'status': 'error',
# #                     'message': 'Invalid username or password'
# #                 }
# #                 await ws.send_str(json.dumps(error_response))
                
# #         finally:
# #             conn.close()
            
# #     except Exception as e:
# #         print(f"❌ [WS-Auth] Login error: {e}")
# #         error_response = {
# #             'type': 'login_response',
# #             'status': 'error',
# #             'message': 'Internal server error'
# #         }
# #         await ws.send_str(json.dumps(error_response))

# # # ENHANCED CONVERSATION LOADING - NEW!
# # async def get_user_previous_conversations(user_id):
# #     """Load all conversations (sent & received) with proper room metadata"""
# #     try:
# #         print(f"📚 [SERVER] Getting ALL conversations for user_id: {user_id}")
        
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
        
# #         # Get all room_ids where user is sender or recipient
# #         cursor.execute("""
# #             SELECT DISTINCT room_id FROM messages 
# #             WHERE sender_id = %s OR recipient_id = %s
# #             ORDER BY room_id
# #         """, (user_id, str(user_id)))
        
# #         room_ids = [row[0] for row in cursor.fetchall()]
# #         print(f"📚 [SERVER] Found {len(room_ids)} rooms involving user {user_id}")
        
# #         if not room_ids:
# #             conn.close()
# #             return []
        
# #         user_conversations = {}
        
# #         for room_id in room_ids:
# #             print(f"📚 [SERVER] *** Processing room {room_id} ***")
            
# #             # Fetch all messages in this room
# #             cursor.execute("""
# #                 SELECT sender_id, sender_username, recipient_id, content, 
# #                        message_type, file_name, file_data, file_size, mime_type, timestamp
# #                 FROM messages 
# #                 WHERE room_id = %s 
# #                 ORDER BY timestamp ASC
# #             """, (room_id,))
            
# #             room_messages = cursor.fetchall()
# #             if not room_messages:
# #                 continue
            
# #             # Determine the other participant
# #             partner_id = None
# #             partner_username = None
            
# #             for row in room_messages:
# #                 sender_id, sender_username, recipient_id = row[0], row[1], row[2]
# #                 if str(sender_id) != str(user_id):
# #                     partner_id = sender_id
# #                     partner_username = sender_username
# #                     break
# #                 elif str(recipient_id) != str(user_id):
# #                     if recipient_id.isdigit():
# #                         cursor.execute("SELECT username FROM users WHERE user_id = %s", (int(recipient_id),))
# #                         partner_user = cursor.fetchone()
# #                         if partner_user:
# #                             partner_id = int(recipient_id)
# #                             partner_username = partner_user[0]
# #                     else:
# #                         partner_id = recipient_id
# #                         partner_username = recipient_id
# #                     break
            
# #             if not partner_username:
# #                 print(f"⚠️ [SERVER] Could not determine partner in room {room_id}")
# #                 continue
            
# #             if room_id not in user_conversations:
# #                 user_conversations[room_id] = {
# #                     "friend_id": partner_id,
# #                     "friend_username": partner_username,
# #                     "room_id": room_id,
# #                     "messages": []
# #                 }
            
# #             for row in room_messages:
# #                 sender_id, sender_username, recipient_id, content, message_type, file_name, file_data, file_size, mime_type, timestamp = row
                
# #                 message_data = {
# #                     "message_id": f"{room_id}_{timestamp.timestamp()}",
# #                     "sender_id": sender_id,
# #                     "sender_username": sender_username,
# #                     "recipient_id": recipient_id,
# #                     "content": content,
# #                     "message_type": message_type,
# #                     "timestamp": timestamp.isoformat(),
# #                     "room_id": room_id
# #                 }
                
# #                 if message_type in ['image', 'file']:
# #                     message_data.update({
# #                         "file_name": file_name,
# #                         "file_data": file_data,
# #                         "file_size": file_size,
# #                         "mime_type": mime_type
# #                     })
                
# #                 user_conversations[room_id]["messages"].append(message_data)
            
# #             print(f"📚 [SERVER] ✅ Room {room_id}: {len(user_conversations[room_id]['messages'])} messages with {partner_username}")
        
# #         conn.close()
        
# #         return list(user_conversations.values())
    
# #     except Exception as e:
# #         print(f"❌ [SERVER] Error loading conversations: {e}")
# #         import traceback
# #         traceback.print_exc()
# #         return []


# # def get_or_create_room_id(sender_id, recipient_id):
# #     """FIXED: Always same room regardless of who sends first"""
# #     try:
# #         # Convert to integers for proper sorting
# #         user1_id = int(sender_id) if isinstance(sender_id, str) else sender_id
# #         user2_id = int(recipient_id) if isinstance(recipient_id, str) else recipient_id
        
# #         # Sort IDs to ensure consistent room name
# #         min_id = min(user1_id, user2_id)
# #         max_id = max(user1_id, user2_id)
        
# #         # Create deterministic room name
# #         room_id = f"room_{min_id}_{max_id}"
        
# #         print(f"🏠 [ROOM] Deterministic room for users {user1_id} ↔ {user2_id}: {room_id}")
        
# #         return room_id
        
# #     except Exception as e:
# #         print(f"❌ [ROOM] Error: {e}")
# #         # Fallback with sorted IDs
# #         try:
# #             sorted_ids = sorted([str(sender_id), str(recipient_id)])
# #             return f"fallback_{sorted_ids[0]}_{sorted_ids[1]}"
# #         except:
# #             return str(uuid.uuid4())


# # # Add this debug function to your server.py
# # def debug_all_rooms_for_user(user_id):
# #     """Debug: Find ALL rooms that mention this user - FIXED PostgreSQL version"""
# #     try:
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
        
# #         print(f"🔍 [DEBUG] Searching for ALL rooms containing user {user_id}...")
        
# #         # FIXED: Only use string comparison for recipient_id (VARCHAR column)
# #         cursor.execute("""
# #             SELECT DISTINCT room_id, sender_username, recipient_id, content, timestamp
# #             FROM messages 
# #             WHERE sender_id = %s OR recipient_id = %s
# #             ORDER BY timestamp DESC
# #             LIMIT 50
# #         """, (user_id, str(user_id)))
        
# #         all_messages = cursor.fetchall()
# #         print(f"🔍 [DEBUG] Found {len(all_messages)} messages involving user {user_id}")
        
# #         # NOW CHECK: Are there messages FROM friends TO indira?
# #         cursor.execute("""
# #             SELECT DISTINCT room_id, sender_username, sender_id, content
# #             FROM messages 
# #             WHERE recipient_id = %s AND sender_id != %s
# #             ORDER BY timestamp DESC
# #             LIMIT 20
# #         """, (str(user_id), user_id))
        
# #         friend_replies = cursor.fetchall()
# #         print(f"🔍 [DEBUG] Found {len(friend_replies)} REPLIES from friends to user {user_id}")
        
# #         if friend_replies:
# #             print("📥 [DEBUG] FRIEND REPLIES FOUND:")
# #             for room_id, sender_username, sender_id, content in friend_replies:
# #                 print(f"  Room {room_id}: '{content}' from {sender_username} (ID: {sender_id})")
# #         else:
# #             print("❌ [DEBUG] NO FRIEND REPLIES FOUND - Friends never replied!")
        
# #         conn.close()
        
# #     except Exception as e:
# #         print(f"❌ [DEBUG] Error: {e}")

# # # Call this debug function in get_user_previous_conversations
# # # Add this line RIGHT at the start of get_user_previous_conversations:


# # # ENHANCED MESSAGE HANDLING - NEW!
# # async def handle_new_message_save(user_info, data):
# #     """Save new message to database with support for text, images, and files"""
# #     try:
# #         recipient_id = data.get("recipient_id")
# #         message_content = data.get("message")
# #         message_type = data.get("message_type", "text")
        
# #         if not recipient_id:
# #             print(f"❌ Missing recipient_id")
# #             return None
        
# #         # Convert recipient_id to int if it's a string
# #         if isinstance(recipient_id, str) and recipient_id.isdigit():
# #             recipient_id = int(recipient_id)
        
# #         print(f"💬 [MESSAGE] Processing message from user {user_info['user_id']} to recipient {recipient_id}")
        
# #         # Get existing room or create new one - FIXED VERSION
# #         room_id = get_or_create_room_id(user_info['user_id'], recipient_id)
        
# #         # Set room_id in data for database save
# #         data["room_id"] = room_id
        
# #         print(f"🏠 [MESSAGE] Using room_id: {room_id}")
        
# #         # Save to database first (new system)
# #         enhanced_message = await save_message_to_database(user_info, data)
        
# #         if not enhanced_message:
# #             print(f"❌ Failed to save message to database")
# #             return None
        
# #         # Also save to JSON file for backward compatibility
# #         try:
# #             json_message = {
# #                 "sender_id": user_info['user_id'],
# #                 "sender_username": user_info['username'],
# #                 "timestamp": enhanced_message["timestamp"],
# #                 "type": message_type,
# #                 "content": message_content or enhanced_message.get("file_name", ""),
# #                 "room_id": room_id,
# #                 "recipient_id": str(recipient_id)  # Store as string for consistency
# #             }
            
# #             async with chat_log_lock:
# #                 chat_data = load_chat_log()
# #                 conversations = chat_data.setdefault("conversations", {})

# #                 if room_id not in conversations:
# #                     conversations[room_id] = []

# #                 conversations[room_id].append(json_message)
# #                 save_chat_log(chat_data)
            
# #             print(f"✅ [JSON] Also saved to JSON file for compatibility")
            
# #         except Exception as json_error:
# #             print(f"⚠️ [JSON] Failed to save to JSON file: {json_error}")
        
# #         print(f"✅ [MESSAGE to Room {room_id}] from {user_info['username']} to recipient {recipient_id}")
        
# #         # Broadcast the new message to both participants
# #         websocket_message = {
# #             'type': 'new_message',
# #             'room_id': room_id,
# #             'message': enhanced_message
# #         }
# #         await auth_bridge.broadcast_to_all_websockets(websocket_message)
        
# #         return enhanced_message
        
# #     except Exception as e:
# #         print(f"❌ Error saving message: {e}")
# #         import traceback
# #         traceback.print_exc()
# #         return None

# # async def websocket_handler(request):
# #     """Enhanced WebSocket handler with login, registration, and authentication support"""
# #     ws = web.WebSocketResponse()
# #     await ws.prepare(request)
    
# #     client_ip = request.remote
# #     user_info = None
    
# #     print(f"🔌 WebSocket connection attempt from {client_ip}")
    
# #     try:
# #         # Wait for first message (could be login, registration, OR authentication)
# #         first_msg_timeout = 10  # 10 seconds for first message
# #         first_msg = await asyncio.wait_for(ws.receive(), timeout=first_msg_timeout)
        
# #         if first_msg.type != WSMsgType.TEXT:
# #             await ws.send_str(json.dumps({'error': 'Authentication, login, or registration required'}))
# #             return ws
        
# #         try:
# #             first_data = json.loads(first_msg.data)
# #             message_type = first_data.get('type')
            
# #             # Handle login request (no auth needed)
# #             if message_type == 'login':
# #                 await handle_websocket_login(ws, first_data)
# #                 return ws  # Close connection after login (client gets token and reconnects)
            
# #             # Handle registration request (no auth needed)
# #             elif message_type == 'register':
# #                 await handle_websocket_registration(ws, first_data)
# #                 return ws  # Close connection after registration
            
# #             # Handle authentication with token (existing logic)
# #             token = first_data.get('token')
            
# #             if not token:
# #                 await ws.send_str(json.dumps({'error': 'Token required for authentication'}))
# #                 return ws
            
# #             user_info = verify_jwt_token(token)
# #             if not user_info:
# #                 await ws.send_str(json.dumps({'error': 'Invalid or expired token'}))
# #                 return ws
            
# #             # Add authenticated client
# #             session_id = first_data.get('session_id', 'unknown')
# #             auth_bridge.add_websocket_client(ws, user_info['user_id'], user_info['username'], session_id)
            
# #             # Send authentication success
# #             welcome_msg = {
# #                 "type": "auth_success",
# #                 "message": f"Welcome {user_info['username']}!",
# #                 "user": {
# #                     "user_id": user_info['user_id'],
# #                     "username": user_info['username']
# #                 },
# #                 "timestamp": time.time()
# #             }
# #             await ws.send_str(json.dumps(welcome_msg))
            
# #             # Determine connection type and handle accordingly
# #             is_search_connection = 'search' in session_id.lower()
# #             is_friends_connection = 'auto_friends' in session_id.lower() or 'friends' in session_id.lower()
            
# #             if is_search_connection:
# #                 print(f"🔍 [WS] Search connection detected for {user_info['username']} - waiting for search request")
# #                 # Don't auto-send friends for search connections
# #             elif is_friends_connection or session_id == 'unknown':
# #                 # Auto-send friends for main friend list connections
                
# #                 print(f"📤 [WS] Auto-sending friends list to {user_info['username']}...")
# #                 try:
# #                     await handle_get_friends_websocket(ws, user_info)
# #                     print(f"✅ [WS] Auto-sent friends to {user_info['username']}")
# #                 except Exception as friends_error:
# #                     print(f"❌ [WS] Error auto-sending friends: {friends_error}")
# #                     friends_error_response = {
# #                         "type": "friends_list_response",
# #                         "status": "error",
# #                         "message": "Failed to load friends",
# #                         "timestamp": time.time()
# #                     }
# #                     await ws.send_str(json.dumps(friends_error_response))
# #             else:
# #                 print(f"❓ [WS] Unknown connection type for {user_info['username']} - session: {session_id}")
            
# #             # Send previous conversations (now with file support)
# #             if not is_search_connection and not is_friends_connection:
# #                 print(f"📤 [WS] Fetching previous conversations for {user_info['username']}")
# #                 previous_conversations = await get_user_previous_conversations(user_info['user_id'])
# #                 if previous_conversations:
# #                     conversations_msg = {
# #                         "type": "previous_conversations",
# #                         "conversations": previous_conversations,
# #                         "timestamp": time.time()
# #                     }
# #                     await ws.send_str(json.dumps(conversations_msg))
# #                     print(f"✅ [WS] Sent {len(previous_conversations)} previous conversations to {user_info['username']}")

            
# #         except json.JSONDecodeError:
# #             await ws.send_str(json.dumps({'error': 'Invalid message format'}))
# #             return ws
        
# #         # MAIN MESSAGE HANDLING LOOP - AUTHENTICATION ALREADY VERIFIED
# #         print(f"🔄 [WS] Starting message loop for authenticated user: {user_info['username']}")
# #         async for msg in ws:
# #             if msg.type == WSMsgType.TEXT:
# #                 try:
# #                     data = json.loads(msg.data)
# #                     print(f"📨 [WS] Received from {user_info['username']}: {data}")
                    
# #                     # Handle friend-related messages (search, add friend, get friends)
# #                     if await handle_friend_websocket_message(ws, user_info, data):
# #                         # Message was handled by friend system
# #                         if data.get('type') == 'add_friend':
# #                             await broadcast_friends_update_to_user(user_info['user_id'])
# #                         elif data.get('type') == 'search_user':
# #                             await handle_search_user_websocket(ws, user_info, data)
# #                         continue
                        
# #                     # Handle chat messages (enhanced with file support)
# #                     recipient_id = data.get("recipient_id")
# #                     message_content = data.get("message")
# #                     message_type = data.get("message_type", "text")

# #                     if recipient_id and (message_content or message_type in ['image', 'file']):
# #                         print(f"💬 [WS] Processing {message_type} message from {user_info['username']} to recipient_id {recipient_id}")
                        
# #                         # Log file details if it's a file/image
# #                         if message_type in ['image', 'file']:
# #                             file_name = data.get("file_name", "unknown")
# #                             file_size = data.get("file_size", 0)
# #                             print(f"📎 [WS] File details: {file_name} ({file_size} bytes, type: {message_type})")
                        
# #                         try:
# #                             new_message = await handle_new_message_save(user_info, data)
# #                             if new_message: 
# #                                 print(f"✅ [WS] Message saved to database: {new_message}")
# #                                 # Confirm back to sender
# #                                 echo_response = {
# #                                     "type": "message_sent",
# #                                     "original": new_message,
# #                                     "status": "delivered",
# #                                     "server_timestamp": time.time()
# #                                 }
# #                                 await ws.send_str(json.dumps(echo_response))
                                
# #                                 # Forward message to recipient if they're online
# #                                 await auth_bridge.send_to_user_websockets(recipient_id, {
# #                                     "type": "new_message",
# #                                     "message": new_message,
# #                                     "sender": {
# #                                         "user_id": user_info['user_id'],
# #                                         "username": user_info['username']
# #                                     },
# #                                     "timestamp": time.time()
# #                                 }, exclude_ws=ws)
                                
# #                             else:
# #                                 print(f"❌ [WS] Failed to save message to database")
# #                                 await ws.send_str(json.dumps({"error": "Failed to save message"}))
                                
# #                         except Exception as e:
# #                             print(f"❌ [WS] Error handling message: {e}")
# #                             await ws.send_str(json.dumps({"error": str(e)}))
# #                         continue
                    
# #                     # Handle as regular message (fallback)
# #                     enhanced_data = {
# #                         **data,
# #                         "sender": {
# #                             "user_id": user_info['user_id'],
# #                             "username": user_info['username']
# #                         },
# #                         "timestamp": time.time(),
# #                         "protocol": "websocket"
# #                     }
                    
# #                     # Determine message target
# #                     target_user_id = data.get('target_user_id')
                    
# #                     if target_user_id:
# #                         # Send to specific user
# #                         auth_bridge.add_message_for_user(target_user_id, enhanced_data)
# #                         await auth_bridge.send_to_user_websockets(target_user_id, enhanced_data, exclude_ws=ws)
# #                     else:
# #                         # Broadcast to all users
# #                         await auth_bridge.broadcast_to_all_websockets(enhanced_data, exclude_ws=ws)
# #                         auth_bridge.add_message_for_user(user_info['user_id'], enhanced_data)
                    
# #                     # Echo back to sender
# #                     echo_response = {
# #                         "type": "message_sent",
# #                         "original": enhanced_data,
# #                         "server_timestamp": time.time(),
# #                         "status": "delivered"
# #                     }
# #                     await ws.send_str(json.dumps(echo_response))
                    
# #                 except json.JSONDecodeError as e:
# #                     error_msg = {"error": "Invalid JSON", "details": str(e)}
# #                     await ws.send_str(json.dumps(error_msg))
                    
# #             elif msg.type == WSMsgType.ERROR:
# #                 print(f'❌ [WS] Error from {user_info["username"]}: {ws.exception()}')
# #                 break
    
# #     except asyncio.TimeoutError:
# #         print(f"⏰ WebSocket timeout from {client_ip}")
# #         await ws.send_str(json.dumps({'error': 'Message timeout'}))
# #     except Exception as e:
# #         print(f"❌ [WS] Exception: {e}")
# #         import traceback
# #         traceback.print_exc()
# #     finally:
# #         if user_info and ws in auth_bridge.websocket_clients:
# #             auth_bridge.remove_websocket_client(ws)
# #             print(f"🔌 [WS] Disconnected: {user_info['username']}")
    
# #     return ws

# # async def broadcast_friends_update_to_user(user_id):
# #     """Send updated friends list to all of user's friend list connections"""
# #     try:
# #         # Find all friend list connections for this user
# #         user_connections = []
# #         for ws_client in auth_bridge.websocket_clients:
# #             client_info = auth_bridge.websocket_clients[ws_client]
# #             if (client_info['user_id'] == user_id and 
# #                 ('auto_friends' in client_info.get('session_id', '') or 
# #                  'friends' in client_info.get('session_id', '') or
# #                  client_info.get('session_id', '') == 'unknown')):
# #                 user_connections.append((ws_client, client_info))
        
# #         if user_connections:
# #             print(f"📤 [WS] Broadcasting friends update to {len(user_connections)} connections for user {user_id}")
            
# #             # Get updated friends list
# #             conn = get_db_connection()
# #             cursor = conn.cursor()
# #             cursor.execute("""
# #                 SELECT f.friend_id, u.username, f.created_at
# #                 FROM friendships f
# #                 JOIN users u ON f.friend_id = u.user_id
# #                 WHERE f.user_id = %s AND f.status = 'accepted'
# #                 ORDER BY u.username
# #             """, (user_id,))
            
# #             friends = []
# #             for row in cursor.fetchall():
# #                 friends.append({
# #                     'user_id': row[0],
# #                     'username': row[1],
# #                     'created_at': str(row[2])
# #                 })
# #             conn.close()
            
# #             # Send updated friends list to all friend list connections
# #             friends_update = {
# #                 'type': 'friends_list_response',
# #                 'status': 'success',
# #                 'friends': friends,
# #                 'count': len(friends),
# #                 'timestamp': time.time(),
# #                 'update_reason': 'friend_added'
# #             }
            
# #             for ws_client, client_info in user_connections:
# #                 try:
# #                     await ws_client.send_str(json.dumps(friends_update))
# #                     print(f"✅ [WS] Sent friends update to session {client_info.get('session_id', 'unknown')}")
# #                 except Exception as e:
# #                     print(f"❌ [WS] Failed to send friends update: {e}")
                    
# #     except Exception as e:
# #         print(f"❌ [WS] Error broadcasting friends update: {e}")

# # async def handle_websocket_registration(ws, data):
# #     """Handle registration request via WebSocket (before authentication)"""
# #     try:
# #         username = data.get('username', '').strip()
# #         password = data.get('password', '')
        
# #         if not username or not password:
# #             error_response = {
# #                 'type': 'register_response',
# #                 'status': 'error',
# #                 'message': 'Username and password are required'
# #             }
# #             await ws.send_str(json.dumps(error_response))
# #             return
        
# #         # Use the same registration logic as your HTTP endpoint
# #         conn = get_db_connection()
# #         cursor = conn.cursor()
        
# #         try:
# #             # Insert new user
# #             cursor.execute(
# #                 "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
# #                 (username, password)
# #             )
# #             user_id = cursor.lastrowid
# #             conn.commit()
            
# #             print(f"✅ [WS-Auth] New user registered: {username} (ID: {user_id})")
            
# #             # Create JWT token
# #             token = create_jwt_token(user_id, username)
# #             session_id = str(uuid.uuid4())
            
# #             # Send success response
# #             success_response = {
# #                 'type': 'register_response',
# #                 'status': 'success',
# #                 'message': 'Registration successful',
# #                 'user': {
# #                     'user_id': user_id,
# #                     'username': username
# #                 },
# #                 'token': token,
# #                 'session_id': session_id
# #             }
            
# #             await ws.send_str(json.dumps(success_response))
# #             print(f"📤 [WS-Auth] Registration success sent to {username}")
            
# #         except psycopg2.IntegrityError:
# #             # Username already exists
# #             error_response = {
# #                 'type': 'register_response',
# #                 'status': 'error',
# #                 'message': 'Username already exists'
# #             }
# #             await ws.send_str(json.dumps(error_response))
            
# #         finally:
# #             conn.close()
            
# #     except Exception as e:
# #         print(f"❌ [WS-Auth] Registration error: {e}")
# #         error_response = {
# #             'type': 'register_response',
# #             'status': 'error',
# #             'message': 'Internal server error'
# #         }
# #         await ws.send_str(json.dumps(error_response))

# # async def api_get_stats(request):
# #     """Get enhanced statistics"""
# #     auth_bridge.update_user_stats()
    
# #     response_data = {
# #         "status": "success",
# #         "stats": auth_bridge.stats,
# #         "timestamp": time.time()
# #     }
    
# #     return web.json_response(response_data)

# # async def send_previous_conversations(self, username: str, user_id: int):
# #     """Send list of users who have chat history with current user"""
# #     conn = sqlite3.connect(self.db.db_path)
# #     cursor = conn.cursor()
    
# #     # Get all users who have exchanged messages with current user
# #     cursor.execute("""
# #         SELECT DISTINCT u.username, MAX(m.timestamp) as last_message_time
# #         FROM messages m
# #         JOIN users u ON (u.id = m.from_user_id OR u.id = m.to_user_id)
# #         WHERE (m.from_user_id = ? OR m.to_user_id = ?) 
# #         AND u.id != ?
# #         GROUP BY u.username
# #         ORDER BY last_message_time DESC
# #     """, (user_id, user_id, user_id))
    
# #     previous_chats = [row[0] for row in cursor.fetchall()]
# #     conn.close()
    
# #     # Send previous conversations to frontend
# #     if previous_chats:
# #         await self.send_to_user(username, {
# #             "type": "previous_conversations",
# #             "conversations": previous_chats
# #         })


# # async def create_app():
# #     """Create and configure the web application"""
# #     app = web.Application()
    
# #     # Setup CORS
# #     cors = aiohttp_cors.setup(app, defaults={
# #         "*": aiohttp_cors.ResourceOptions(
# #             allow_credentials=True,
# #             expose_headers="*",
# #             allow_headers="*",
# #             allow_methods="*"
# #         )
# #     })
    
# #     # Authentication routes
# #     app.router.add_post('/api/auth', auth_login_register)
# #     app.router.add_post('/api/logout', auth_logout)
    
# #     # WebSocket route
# #     app.router.add_get('/', websocket_handler)
    
# #     # Authenticated API routes
# #     app.router.add_post('/api/send', api_send_authenticated_message)
# #     app.router.add_get('/api/receive', api_receive_authenticated_messages)
# #     app.router.add_get('/api/users', api_get_users)
# #     app.router.add_get('/api/stats', api_get_stats)
# #     app.router.add_post('/api/add_friend', api_add_friend)
# #     app.router.add_get('/api/friends', api_get_friends)
    
# #     # NEW: Chat messaging routes
# #     app.router.add_post('/api/chat/send', api_send_message)
# #     app.router.add_get('/api/chat/messages/{room_id}', api_get_messages)
    
# #     # Web interface
# #     #app.router.add_get('/', serve_auth_interface)
    
# #     # Add CORS to all routes
# #     for route in list(app.router.routes()):
# #         cors.add(route)
    
# #     return app

# # def create_ssl_context():
# #     """Create SSL context for HTTPS"""
# #     import os
    
# #     possible_paths = [
# #         ('cert.pem', 'key.pem'),
# #         ('./cert.pem', './key.pem'),
# #         (os.path.join(os.getcwd(), 'cert.pem'), os.path.join(os.getcwd(), 'key.pem')),
# #         (os.path.join(os.path.dirname(__file__), 'cert.pem'), os.path.join(os.path.dirname(__file__), 'key.pem'))
# #     ]
    
# #     print(f"🔍 Looking for SSL certificates...")
    
# #     for cert_path, key_path in possible_paths:
# #         if os.path.exists(cert_path) and os.path.exists(key_path):
# #             try:
# #                 ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
# #                 ssl_context.load_cert_chain(cert_path, key_path)
# #                 print(f"✅ SSL certificates loaded from {cert_path}")
# #                 return ssl_context
# #             except Exception as e:
# #                 print(f"❌ Error loading certificates: {e}")
# #                 continue
    
# #     print("❌ SSL certificates not found!")
# #     return None

# # def main():
# #     """Main function to start the server"""
# #     print("🔐 Enhanced Authenticated Message Bridge Server with File/Image Support")
# #     print("=" * 80)
    
# #     # Initialize database
# #     init_database()
    
# #     # Create SSL context
# #     ssl_context = create_ssl_context()
# #     if not ssl_context:
# #         print("\n⚠️  Starting HTTP server instead (port 8080)...")
# #         print("🌐 Auth interface: http://localhost:8080")
        
# #         try:
# #             loop = asyncio.new_event_loop()
# #             asyncio.set_event_loop(loop)
# #             app = loop.run_until_complete(create_app())
            
# #             print("\n✅ HTTP Enhanced Message Bridge Server starting...")
# #             print("🧪 Login/Register: http://localhost:8080/")
# #             print("📡 WebSocket: ws://localhost:8080/")
# #             print("🔑 Auth: POST http://localhost:8080/api/auth")
# #             print("🌐 Send: POST http://localhost:8080/api/send")
# #             print("📨 Receive: GET http://localhost:8080/api/receive")
# #             print("👥 Users: GET http://localhost:8080/api/users")
# #             print("📊 Stats: GET http://localhost:8080/api/stats")
# #             print("💬 Send Chat: POST http://localhost:8080/api/chat/send")
# #             print("📜 Get Messages: GET http://localhost:8080/api/chat/messages/{room_id}")
# #             print("📎 Supports: Text, Images, and Files via WebSocket")
# #             print("🛑 Press Ctrl+C to stop\n")
            
# #             web.run_app(app, host='localhost', port=8080, access_log_format='%r %s %b')
# #         except Exception as e:
# #             print(f"❌ Error starting HTTP server: {e}")
# #         return
    
# #     print("\n🔐 Starting HTTPS + WebSocket Enhanced Message Bridge server")
# #     print("🌐 Auth interface: https://localhost:8443")
    
# #     try:
# #         loop = asyncio.new_event_loop()
# #         asyncio.set_event_loop(loop)
# #         app = loop.run_until_complete(create_app())
        
# #         print("\n✅ HTTPS Enhanced Message Bridge Server starting...")
# #         print("🧪 Login/Register: https://localhost:8443/")
# #         print("📡 WebSocket: wss://localhost:8443/")
# #         print("🔑 Auth: POST https://localhost:8443/api/auth")
# #         print("🌐 Send: POST https://localhost:8443/api/send")
# #         print("📨 Receive: GET https://localhost:8443/api/receive")
# #         print("👥 Users: GET https://localhost:8443/api/users")
# #         print("📊 Stats: GET https://localhost:8443/api/stats")
# #         print("💬 Send Chat: POST https://localhost:8443/api/chat/send")
# #         print("📜 Get Messages: GET https://localhost:8443/api/chat/messages/{room_id}")
# #         print("📎 Supports: Text, Images, and Files via WebSocket & Database")
# #         print("⚠️  Note: Accept self-signed certificate warning in browser")
# #         print("🛑 Press Ctrl+C to stop\n")
        
# #         web.run_app(
# #             app, 
# #             host='localhost', 
# #             port=8443, 
# #             ssl_context=ssl_context,
# #             access_log_format='%t %r %s %b'
# #         )
        
# #     except Exception as e:
# #         print(f"❌ Error starting HTTPS server: {e}")

# # if __name__ == '__main__':
# #     # Install dependencies:
# #     # pip install aiohttp aiohttp-cors PyJWT psycopg2-binary pytz
# #     try:
# #         main()
# #     except KeyboardInterrupt:
# #         print("\n🛑 Enhanced message bridge server stopped by user")
# #         print("📊 Final statistics:")
# #         print(f"   Total messages: {auth_bridge.stats['total_messages']}")
# #         print(f"   Registered users: {auth_bridge.stats['registered_users']}")
# #         print(f"   Active sessions: {auth_bridge.stats['active_sessions']}")
# #     except Exception as e:
# #         print(f"❌ Error: {e}")
# #         print("\n💡 Troubleshooting:")
# #         print("   1. Install dependencies: pip install aiohttp aiohttp-cors PyJWT psycopg2-binary pytz")
# #         print("   2. Make sure cert.pem and key.pem are in the script directory")
# #         print("   3. Check if ports 8080/8443 are available")
# #         print("   4. Verify PostgreSQL connection settings")


# import asyncio
# import ssl
# import json
# import time
# import hashlib
# import sqlite3
# import os
# from collections import defaultdict
# from aiohttp import web, WSMsgType
# import aiohttp_cors
# import uuid
# from datetime import datetime, timedelta
# import jwt
# import psycopg2
# import pytz
# import base64

# # --- Constants ---
# JWT_SECRET = 'your-secret-key-change-in-production'
# UPLOAD_DIR = 'uploads'

# # --- Database Functions ---
# def get_db_connection():
#     try:
#         conn = psycopg2.connect(
#             host="aws-0-ap-southeast-1.pooler.supabase.com", port=6543,
#             database="postgres", user="postgres.ziymoatadswbppsrsanr",
#             password="Oriorion21!", sslmode='require'
#         )
#         return conn
#     except Exception as e:
#         print(f"❌ CRITICAL: Could not connect to PostgreSQL database: {e}")
#         return None

# def init_database():
#     conn = get_db_connection()
#     if not conn: return
#     try:
#         with conn.cursor() as cursor:
#             cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)")
#             cursor.execute("CREATE TABLE IF NOT EXISTS friendships (user_id INTEGER NOT NULL, friend_id INTEGER NOT NULL, status TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, friend_id), FOREIGN KEY (user_id) REFERENCES users (user_id), FOREIGN KEY (friend_id) REFERENCES users (user_id))")
#             cursor.execute("CREATE TABLE IF NOT EXISTS messages (message_id SERIAL PRIMARY KEY, room_id VARCHAR(255) NOT NULL, sender_id INTEGER NOT NULL, sender_username VARCHAR(255) NOT NULL, recipient_id INTEGER, content TEXT, message_type VARCHAR(10) DEFAULT 'text', file_name VARCHAR(255), file_path TEXT, file_size INTEGER, mime_type VARCHAR(100), timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (sender_id) REFERENCES users (user_id))")
#             cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_room_id ON messages (room_id);')
#             cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages (sender_id);')
#             cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_recipient_id ON messages (recipient_id);')
#         conn.commit()
#     finally:
#         conn.close()

# # --- Auth & Helper Functions ---
# def hash_password(password):
#     return hashlib.sha256(password.encode('utf-8')).hexdigest()

# def verify_password(client_hashed_password, db_hashed_password):
#     return client_hashed_password == db_hashed_password

# def create_jwt_token(user_id, username):
#     payload = {'user_id': user_id, 'username': username, 'exp': datetime.now(pytz.UTC) + timedelta(hours=24), 'iat': datetime.now(pytz.UTC)}
#     return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

# def verify_jwt_token(token):
#     try:
#         return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
#     except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
#         return None

# def get_user_id_from_username(username):
#     conn = get_db_connection()
#     if not conn: return None
#     try:
#         with conn.cursor() as cursor:
#             cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
#             user = cursor.fetchone()
#         return user[0] if user else None
#     finally:
#         conn.close()

# def get_or_create_room_id(sender_id, recipient_username):
#     recipient_id = get_user_id_from_username(recipient_username)
#     if not recipient_id: return None, None
#     min_id, max_id = min(sender_id, recipient_id), max(sender_id, recipient_id)
#     return f"room_{min_id}_{max_id}", recipient_id

# # --- Main Bridge Class ---
# class AuthBridge:
#     def __init__(self):
#         self.websocket_clients = {}
#     def add_websocket_client(self, ws, user_id, username, session_id):
#         self.websocket_clients[ws] = {'user_id': user_id, 'username': username, 'session_id': session_id}
#         print(f"🔌 WebSocket client connected: {username} (ID: {user_id})")
#     def remove_websocket_client(self, ws):
#         if ws in self.websocket_clients:
#             user_info = self.websocket_clients.pop(ws)
#             print(f"🔌 WebSocket client disconnected: {user_info['username']}")
#     async def send_to_user_websockets(self, target_user_id, message):
#         if not isinstance(target_user_id, int):
#             target_user_id = int(target_user_id)
#         closed_clients = []
#         for ws, info in self.websocket_clients.items():
#             if info['user_id'] == target_user_id:
#                 try:
#                     await ws.send_json(message)
#                 except ConnectionResetError:
#                     closed_clients.append(ws)
#         for ws in closed_clients:
#             self.remove_websocket_client(ws)

# # --- CHAT & MESSAGE HANDLING ---
# async def save_message_to_database(user_info, room_id, recipient_id, message_data):
#     conn = get_db_connection()
#     if not conn: return None
    
#     message_type = message_data.get("message_type", "text")
#     content = message_data.get("message", "")
#     file_name, file_path, file_size, mime_type = None, None, None, None

#     if message_type in ['image', 'file'] and "file_data" in message_data:
#         file_data_b64 = message_data["file_data"]
#         file_name = message_data.get("file_name", "uploaded_file")
#         file_size = message_data.get("file_size")
#         mime_type = message_data.get("mime_type")
        
#         file_ext = os.path.splitext(file_name)[1]
#         server_filename = f"{uuid.uuid4()}{file_ext}"
#         file_path = os.path.join(UPLOAD_DIR, server_filename)
        
#         with open(file_path, "wb") as f:
#             f.write(base64.b64decode(file_data_b64))
#         print(f"💾 Saved uploaded file to: {file_path}")

#     try:
#         with conn.cursor() as cursor:
#             cursor.execute("""
#                 INSERT INTO messages (room_id, sender_id, sender_username, recipient_id, content, message_type, file_name, file_path, file_size, mime_type)
#                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING message_id, timestamp
#             """, (room_id, user_info['user_id'], user_info['username'], recipient_id, content, message_type, file_name, file_path, file_size, mime_type))
#             message_id, timestamp = cursor.fetchone()
#         conn.commit()
#     finally:
#         conn.close()

#     enhanced_message = {
#         "message_id": message_id, "room_id": room_id, "sender_id": user_info['user_id'],
#         "sender_username": user_info['username'], "recipient_id": recipient_id,
#         "content": content, "message_type": message_type, "timestamp": timestamp.isoformat(),
#         "file_name": file_name, "file_path": file_path, "file_size": file_size, "mime_type": mime_type
#     }
#     print(f"✅ [DB] Saved {message_type} message to DB: ID {message_id}")
#     return enhanced_message

# async def get_user_previous_conversations(user_id, username):
#     print(f"📚 [SERVER] Getting ALL conversations for user_id: {user_id}")
#     conn = get_db_connection()
#     if not conn: return {}

#     query = "SELECT DISTINCT room_id FROM messages WHERE sender_id = %s OR recipient_id = %s;"
#     try:
#         with conn.cursor() as cursor:
#             cursor.execute(query, (user_id, user_id))
#             room_ids = [row[0] for row in cursor.fetchall()]
        
#         print(f"📚 [SERVER] Found {len(room_ids)} rooms involving user {user_id}: {room_ids}")
#         if not room_ids: return {}

#         conversations = {}
#         with conn.cursor() as cursor:
#             for room_id in room_ids:
#                 cursor.execute("SELECT u.username, m.sender_username, m.content, m.message_type, m.timestamp, m.file_name, m.file_path, m.file_size FROM messages m LEFT JOIN users u ON m.recipient_id = u.user_id WHERE m.room_id = %s ORDER BY m.timestamp ASC", (room_id,))
                
#                 messages, friend_username = [], None
#                 for row in cursor.fetchall():
#                     recipient_username, sender, content, msg_type, ts, file_name, file_path, file_size = row
                    
#                     if friend_username is None:
#                         if sender != username: friend_username = sender
#                         elif recipient_username != username: friend_username = recipient_username

#                     messages.append({
#                         "sender_username": sender, "content": content, "message_type": msg_type,
#                         "timestamp": ts.isoformat(), "file_name": file_name, "file_path": file_path,
#                         "file_size": file_size
#                     })
                
#                 if friend_username:
#                     conversations[friend_username] = messages
#                 elif messages: # Self-chat
#                     conversations[username] = messages
#         return conversations
#     finally:
#         conn.close()

# # --- HTTP HANDLERS ---
# async def handle_http_auth(request):
#     # This function can remain as is for HTTP-based clients
#     pass

# # --- WEBSOCKET HANDLER ---
# async def websocket_handler(request):
#     ws = web.WebSocketResponse()
#     await ws.prepare(request)
    
#     auth_bridge = request.app['auth_bridge']
#     user_info = None
    
#     try:
#         # The first message determines the connection's purpose
#         first_msg_json = await ws.receive_str(timeout=15)
#         data = json.loads(first_msg_json)
#         action = data.get('type')

#         # --- Handle Unauthenticated Initial Actions ---
#         # These actions will respond and then close the connection,
#         # as the client is expected to reconnect with a token.
#         if action == 'register' or action == 'login':
#             username = data.get('username')
#             client_hashed_password = data.get('password')
            
#             conn = get_db_connection()
#             if not conn:
#                 await ws.send_json({'status': 'error', 'message': 'Database connection failed.'})
#                 await ws.close()
#                 return ws

#             try:
#                 with conn.cursor() as cursor:
#                     if action == 'register':
#                         cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
#                         if cursor.fetchone():
#                             await ws.send_json({'status': 'error', 'message': 'Username already exists.'})
#                             return ws # Return here to let finally block close the connection
                        
#                         cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING user_id", (username, client_hashed_password))
#                         user_id = cursor.fetchone()[0]
#                         conn.commit()
                        
#                         token = create_jwt_token(user_id, username)
#                         await ws.send_json({'status': 'success', 'message': 'Registration successful.', 'token': token, 'user': {'user_id': user_id, 'username': username}})
#                         print(f"✅ Registered new user '{username}' via WebSocket.")
                    
#                     elif action == 'login':
#                         print(f"--- WebSocket Login Attempt for: {username} ---")
#                         cursor.execute("SELECT user_id, username, password_hash FROM users WHERE username = %s", (username,))
#                         user_record = cursor.fetchone()

#                         if not user_record:
#                             print(f"❌ LOGIN FAILED: User '{username}' not found in database.")
#                             await ws.send_json({'status': 'error', 'message': 'Invalid username or password.'})
#                             return ws

#                         print(f"✅ LOGIN INFO: User '{username}' found in database.")
#                         user_id, db_username, db_hashed_password = user_record
                        
#                         print(f"  > Client Hash: {client_hashed_password[:10]}...")
#                         print(f"  > DB Hash    : {db_hashed_password[:10]}...")

#                         if verify_password(client_hashed_password, db_hashed_password):
#                             print("✅ LOGIN SUCCESS: Passwords match.")
#                             token = create_jwt_token(user_id, db_username)
#                             await ws.send_json({'status': 'success', 'message': 'Login successful.', 'token': token, 'user': {'user_id': user_id, 'username': db_username}})
#                             print(f"✅ User '{username}' logged in via WebSocket.")
#                         else:
#                             print("❌ LOGIN FAILED: Password hash mismatch.")
#                             await ws.send_json({'status': 'error', 'message': 'Invalid username or password.'})
#             finally:
#                 conn.close()
#                 await ws.close() # Explicitly close after login/register attempt
#             return ws

#         # --- If not register/login, it must be an authentication attempt with a token ---
#         # This is for a persistent connection for an already logged-in user.
#         token = data.get('token')
#         user_info = verify_jwt_token(token)
#         if not user_info:
#             await ws.send_json({'error': 'Authentication failed', 'type': 'auth_fail'})
#             await ws.close()
#             return ws

#         # --- Authenticated State: Add client and start listening loop ---
#         session_id = data.get('session_id', 'unknown')
#         auth_bridge.add_websocket_client(ws, user_info['user_id'], user_info['username'], session_id)
#         await ws.send_json({'type': 'auth_success', 'message': f"Welcome {user_info['username']}!", 'user': user_info})

#         # --- This is the main loop for an authenticated, open connection ---
#         async for msg in ws:
#             if msg.type == WSMsgType.TEXT:
#                 data = json.loads(msg.data)
#                 action = data.get('type')
                
#                 if action == 'get_previous_conversations':
#                     conversations = await get_user_previous_conversations(user_info['user_id'], user_info['username'])
#                     await ws.send_json({"type": "previous_conversations", "conversations": conversations})

#                 elif action == 'chat_message':
#                     recipient_username = data.get("recipient_id")
#                     if not recipient_username: continue

#                     room_id, recipient_id = get_or_create_room_id(user_info['user_id'], recipient_username)
#                     if not room_id:
#                         await ws.send_json({'error': f"User '{recipient_username}' not found."})
#                         continue

#                     new_message = await save_message_to_database(user_info, room_id, recipient_id, data)
#                     if not new_message:
#                         await ws.send_json({'error': 'Failed to save message.'})
#                         continue
                    
#                     await ws.send_json({'type': 'message_sent_confirmation', 'message': new_message})
#                     await auth_bridge.send_to_user_websockets(recipient_id, {'type': 'new_message', 'message': new_message})

#                 # ... other authenticated actions like file download requests ...

#     except Exception as e:
#         print(f"WebSocket Error for {user_info['username'] if user_info else 'Initial Connection'}: {e}")
#     finally:
#         if user_info:
#             auth_bridge.remove_websocket_client(ws)
#         print(f"WebSocket connection closed for {user_info['username'] if user_info else 'Initial Connection'}")

#     return ws

# # --- MAIN APPLICATION SETUP ---
# def main():
#     if not os.path.exists(UPLOAD_DIR):
#         os.makedirs(UPLOAD_DIR)
    
#     init_database()
    
#     app = web.Application()
#     app['auth_bridge'] = AuthBridge()
    
#     cors = aiohttp_cors.setup(app, defaults={
#         "*": aiohttp_cors.ResourceOptions(allow_credentials=True, expose_headers="*", allow_headers="*")
#     })
    
#     app.router.add_get('/', websocket_handler) 
#     app.router.add_post('/api/auth', handle_http_auth) # Keep for other clients
    
#     for route in list(app.router.routes()):
#         cors.add(route)

#     ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
#     ssl_context.load_cert_chain('cert.pem', 'key.pem')

#     web.run_app(app, host='localhost', port=8443, ssl_context=ssl_context)

# if __name__ == '__main__':
#     main()

import asyncio
import ssl
import json
import time
import hashlib
import os
import uuid
from datetime import datetime, timedelta
import aiohttp_cors
from aiohttp import web, WSMsgType
import jwt
import psycopg2
import pytz
import base64

# --- Constants ---
JWT_SECRET = 'your-secret-key-change-in-production'
UPLOAD_DIR = 'uploads'

# --- Database Functions ---
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host="aws-0-ap-southeast-1.pooler.supabase.com", port=6543,
            database="postgres", user="postgres.ziymoatadswbppsrsanr",
            password="Oriorion21!", sslmode='require'
        )
        return conn
    except Exception as e:
        print(f"❌ CRITICAL: Could not connect to PostgreSQL database: {e}")
        return None

def init_database():
    conn = get_db_connection()
    if not conn: return
    try:
        with conn.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS friendships (user_id INTEGER NOT NULL, friend_id INTEGER NOT NULL, status TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, friend_id), FOREIGN KEY (user_id) REFERENCES users (user_id), FOREIGN KEY (friend_id) REFERENCES users (user_id))")
            # --- FIX: recipient_id is now consistently VARCHAR to prevent type errors with old data ---
            cursor.execute("CREATE TABLE IF NOT EXISTS messages (message_id SERIAL PRIMARY KEY, room_id VARCHAR(255) NOT NULL, sender_id INTEGER NOT NULL, sender_username VARCHAR(255) NOT NULL, recipient_id VARCHAR(255), content TEXT, message_type VARCHAR(10) DEFAULT 'text', file_name VARCHAR(255), file_path TEXT, file_size INTEGER, mime_type VARCHAR(100), timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (sender_id) REFERENCES users (user_id))")
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_room_id ON messages (room_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages (sender_id);')
        conn.commit()
    finally:
        conn.close()

# --- Auth & Helper Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(client_hashed_password, db_hashed_password):
    return client_hashed_password == db_hashed_password

def create_jwt_token(user_id, username):
    payload = {'user_id': user_id, 'username': username, 'exp': datetime.now(pytz.UTC) + timedelta(hours=24), 'iat': datetime.now(pytz.UTC)}
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def get_user_id_from_username(username):
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
        return user[0] if user else None
    finally:
        conn.close()

def get_or_create_room_id(sender_id, recipient_username):
    recipient_id = get_user_id_from_username(recipient_username)
    if not recipient_id: return None, None
    min_id, max_id = min(sender_id, recipient_id), max(sender_id, recipient_id)
    return f"room_{min_id}_{max_id}", recipient_id

# --- Main Bridge Class ---
class AuthBridge:
    def __init__(self):
        self.websocket_clients = {}
    def add_websocket_client(self, ws, user_id, username, session_id):
        self.websocket_clients[ws] = {'user_id': user_id, 'username': username, 'session_id': session_id}
        print(f"🔌 WebSocket client connected: {username} (ID: {user_id})")
    def remove_websocket_client(self, ws):
        if ws in self.websocket_clients:
            user_info = self.websocket_clients.pop(ws)
            print(f"🔌 WebSocket client disconnected: {user_info['username']}")
    async def send_to_user_websockets(self, target_user_id, message):
        if not isinstance(target_user_id, int):
            target_user_id = int(target_user_id)
        closed_clients = []
        for ws, info in self.websocket_clients.items():
            if info['user_id'] == target_user_id:
                try:
                    await ws.send_json(message)
                except ConnectionResetError:
                    closed_clients.append(ws)
        for ws in closed_clients:
            self.remove_websocket_client(ws)

# --- Database Interaction Functions ---
async def db_save_message(user_info, room_id, recipient_username, message_data):
    conn = get_db_connection()
    if not conn: return None
    
    message_type = message_data.get("message_type", "text")
    content = message_data.get("message", "")
    file_name, file_path, file_size, mime_type = None, None, None, None

    if message_type in ['image', 'file'] and "file_data" in message_data:
        file_data_b64 = message_data["file_data"]
        file_name = message_data.get("file_name", "uploaded_file")
        file_size = message_data.get("file_size")
        mime_type = message_data.get("mime_type")
        file_ext = os.path.splitext(file_name)[1]
        server_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, server_filename)
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(file_data_b64))
        print(f"💾 Saved uploaded file to: {file_path}")

    try:
        with conn.cursor() as cursor:
            # --- FIX: Now saves the recipient's USERNAME string, not their ID ---
            cursor.execute("""
                INSERT INTO messages (room_id, sender_id, sender_username, recipient_id, content, message_type, file_name, file_path, file_size, mime_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING message_id, timestamp
            """, (room_id, user_info['user_id'], user_info['username'], recipient_username, content, message_type, file_name, file_path, file_size, mime_type))
            message_id, timestamp = cursor.fetchone()
        conn.commit()
    finally:
        conn.close()

    full_message = {
        "message_id": message_id, "room_id": room_id, "sender_id": user_info['user_id'],
        "sender_username": user_info['username'], "recipient_id": recipient_username,
        "content": content, "message_type": message_type, "timestamp": timestamp.isoformat(),
        "file_name": file_name, "file_path": file_path, "file_size": file_size, "mime_type": mime_type
    }
    print(f"✅ [DB] Saved {message_type} message to DB: ID {message_id}")
    return full_message

async def db_get_conversations(user_id, username):
    print(f"📚 [DB] Getting all conversations for user_id: {user_id}")
    conn = get_db_connection()
    if not conn: return {}

    # --- FIX: This query now correctly compares sender ID (int) and recipient ID (text) ---
    query = "SELECT DISTINCT room_id FROM messages WHERE sender_id = %s OR recipient_id = %s;"
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (user_id, username))
            room_ids = [row[0] for row in cursor.fetchall()]
        
        print(f"📚 [DB] Found {len(room_ids)} rooms involving user {username}: {room_ids}")
        if not room_ids: return {}

        conversations = {}
        with conn.cursor() as cursor:
            for room_id in room_ids:
                cursor.execute("SELECT recipient_id, sender_username, content, message_type, timestamp, file_name, file_path, file_size FROM messages WHERE room_id = %s ORDER BY timestamp ASC", (room_id,))
                
                messages, friend_username = [], None
                for row in cursor.fetchall():
                    recipient_name, sender, content, msg_type, ts, file_name, file_path, file_size = row
                    
                    if friend_username is None:
                        if sender != username: friend_username = sender
                        elif recipient_name != username: friend_username = recipient_name

                    messages.append({
                        "sender_username": sender, "content": content, "message_type": msg_type,
                        "timestamp": ts.isoformat(), "file_name": file_name, "file_path": file_path,
                        "file_size": file_size
                    })
                
                if friend_username:
                    conversations[friend_username] = messages
                elif messages:
                    conversations[username] = messages
        return conversations
    finally:
        conn.close()

async def db_get_friends(user_id):
    print(f"👥 [DB] Getting friend list for user_id: {user_id}")
    conn = get_db_connection()
    if not conn: return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT u.user_id, u.username, f.created_at 
                FROM friendships f 
                JOIN users u ON f.friend_id = u.user_id 
                WHERE f.user_id = %s AND f.status = 'accepted'
                ORDER BY u.username
            """, (user_id,))
            friends = [{'user_id': row[0], 'username': row[1], 'created_at': str(row[2])} for row in cursor.fetchall()]
        return friends
    finally:
        conn.close()

# --- WEBSOCKET HANDLER ---
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    auth_bridge = request.app['auth_bridge']
    user_info = None
    
    try:
        first_msg_json = await ws.receive_str(timeout=15)
        data = json.loads(first_msg_json)
        action = data.get('type')

        if action in ['register', 'login']:
            username = data.get('username')
            client_hashed_password = data.get('password')
            conn = get_db_connection()
            if not conn:
                await ws.send_json({'status': 'error', 'message': 'Database connection failed.'})
            else:
                try:
                    with conn.cursor() as cursor:
                        if action == 'register':
                            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
                            if cursor.fetchone():
                                await ws.send_json({'status': 'error', 'message': 'Username already exists.'})
                            else:
                                cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING user_id", (username, client_hashed_password))
                                user_id = cursor.fetchone()[0]
                                conn.commit()
                                token = create_jwt_token(user_id, username)
                                await ws.send_json({'status': 'success', 'message': 'Registration successful.', 'token': token, 'user': {'user_id': user_id, 'username': username}})
                        elif action == 'login':
                            cursor.execute("SELECT user_id, username, password_hash FROM users WHERE username = %s", (username,))
                            user_record = cursor.fetchone()
                            if user_record and verify_password(client_hashed_password, user_record[2]):
                                user_id, db_username, _ = user_record
                                token = create_jwt_token(user_id, db_username)
                                await ws.send_json({'status': 'success', 'message': 'Login successful.', 'token': token, 'user': {'user_id': user_id, 'username': db_username}})
                            else:
                                await ws.send_json({'status': 'error', 'message': 'Invalid username or password.'})
                finally:
                    conn.close()
            await ws.close()
            return ws

        token = data.get('token')
        user_info = verify_jwt_token(token)
        if not user_info:
            await ws.send_json({'error': 'Authentication failed', 'type': 'auth_fail'})
            await ws.close()
            return ws

        session_id = data.get('session_id', 'unknown')
        auth_bridge.add_websocket_client(ws, user_info['user_id'], user_info['username'], session_id)
        await ws.send_json({'type': 'auth_success', 'message': f"Welcome {user_info['username']}!", 'user': user_info})

        print(f"✅ [WS] Pushing initial state to {user_info['username']}...")
        
        friends = await db_get_friends(user_info['user_id'])
        await ws.send_json({'type': 'friends_list_response', 'status': 'success', 'friends': friends, 'count': len(friends)})
        print(f"  -> Sent {len(friends)} friends.")

        conversations = await db_get_conversations(user_info['user_id'], user_info['username'])
        await ws.send_json({"type": "previous_conversations", "conversations": conversations})
        print(f"  -> Sent {len(conversations)} conversations.")

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                action = data.get('type')
                
                if action == 'chat_message':
                    recipient_username = data.get("recipient_id")
                    if not recipient_username: continue
                    room_id, _ = get_or_create_room_id(user_info['user_id'], recipient_username)
                    if not room_id: continue
                    # --- FIX: Pass the recipient's USERNAME to the save function ---
                    new_message = await db_save_message(user_info, room_id, recipient_username, data)
                    if not new_message: continue
                    await ws.send_json({'type': 'message_sent_confirmation', 'message': new_message})
                    
                    # Send to recipient if they are online
                    recipient_id_int = get_user_id_from_username(recipient_username)
                    if recipient_id_int:
                        await auth_bridge.send_to_user_websockets(recipient_id_int, {'type': 'new_message', 'message': new_message})

    except Exception as e:
        print(f"WebSocket Error for {user_info['username'] if user_info else 'Initial Connection'}: {e}")
    finally:
        if user_info:
            auth_bridge.remove_websocket_client(ws)
        print(f"WebSocket connection closed for {user_info['username'] if user_info else 'Initial Connection'}")
    return ws

# --- MAIN APPLICATION SETUP ---
def main():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    init_database()
    app = web.Application()
    app['auth_bridge'] = AuthBridge()
    cors = aiohttp_cors.setup(app, defaults={"*": aiohttp_cors.ResourceOptions(allow_credentials=True, expose_headers="*", allow_headers="*")})
    app.router.add_get('/', websocket_handler)
    for route in list(app.router.routes()):
        cors.add(route)
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain('cert.pem', 'key.pem')
    web.run_app(app, host='localhost', port=8443, ssl_context=ssl_context)

if __name__ == '__main__':
    main()