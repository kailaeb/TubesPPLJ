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

# Database setup
DATABASE_FILE = 'auth_bridge.db'
JWT_SECRET = 'your-secret-key-change-in-production'  # Change this in production!

def get_db_connection():
    """Get database connection"""
    # try:
    #     # Coba PostgreSQL dulu
    conn = psycopg2.connect(
        host="aws-0-ap-southeast-1.pooler.supabase.com",  # Dari screenshot
        port=6543,                                        # Bukan 5432!
        database="postgres",                              # Dari screenshot
        user="postgres.ziymoatadswbppsrsanr",            # Dari screenshot
        password="Oriorion21!",              # Ganti dengan password asli
        sslmode='require'
    )
    return conn # , 'postgresql'
    # except:
    #     # Fallback ke SQLite
    #     conn = sqlite3.connect(DATABASE_FILE)
    #     conn.row_factory = sqlite3.Row
    #     return conn, 'sqlite'


# def hash_password(password):
#     """Hash password using SHA-256"""
#     return hashlib.sha256(password.encode()).hexdigest()

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

    # Create friends table
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
    """Handle login and registration requests"""
    try:
        data = await request.json()
        action_type = data.get('type')  # 'login' or 'register'
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
        
        # conn = sqlite3.connect(DATABASE_FILE)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if action_type == 'register':
            # Registration logic
            try:
                # password_hash = hash_password(password)
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, password)
                )
                user_id = cursor.lastrowid
                conn.commit()
                
                print(f"✅ [Auth] New user registered: {username} (ID: {user_id})")
                
                # Create session
                token = create_jwt_token(user_id, username)
                session_id = str(uuid.uuid4())
                expires_at = datetime.now(pytz.UTC) + timedelta(hours=24)
                
                response_data = {
                    'status': 'success',
                    'message': 'Registration successful',
                    'user': {
                        'user_id': user_id,
                        'username': username
                    },
                    'token': token,
                    'session_id': session_id
                }
                
            except psycopg2.IntegrityError:
                response_data = {
                    'status': 'error',
                    'message': 'Username already exists'
                }
                
        else:  # login
            # Login logic
            cursor.execute(
                "SELECT user_id, username, password_hash FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()
            
            if user and verify_password(password, user[2]):
                user_id, db_username, _ = user
                
                print(f"✅ [Auth] User logged in: {username} (ID: {user_id})")
                
                # Create session
                token = create_jwt_token(user_id, username)
                session_id = str(uuid.uuid4())
                expires_at = datetime.now(pytz.UTC) + timedelta(hours=24)
                
                # cursor.execute(
                #     "INSERT INTO user_sessions (session_id, user_id, username, expires_at) VALUES (%s, %s, %s, %s)",
                #     (session_id, user_id, username, expires_at)
                # )
                # conn.commit()
                
                print(f"✅ [Auth] User logged in: {username} (ID: {user_id})")
                
                response_data = {
                    'status': 'success',
                    'message': 'Login successful',
                    'user': {
                        'user_id': user_id,
                        'username': db_username
                    },
                    'token': token,
                    'session_id': session_id
                }
                
            else:
                response_data = {
                    'status': 'error',
                    'message': 'Invalid username or password'
                }
        
        conn.close()
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
    
# In friend_bridge_server_2.py, REPLACE the api_add_friend function

async def api_add_friend(request):
    """Add friend by username, creating a bidirectional friendship."""
    user_info = get_user_from_token(request)
    if not user_info:
        return web.json_response({'status': 'error', 'message': 'Authentication required'}, status=401)
   
    try:
        data = await request.json()
        friend_username = data.get('username', '').strip()
       
        if not friend_username:
            return web.json_response({'status': 'error', 'message': 'Friend username is required'}, status=400)
       
        conn = get_db_connection()
        cursor = conn.cursor()
       
        cursor.execute("SELECT user_id FROM users WHERE username = %s", (friend_username,))
        friend = cursor.fetchone()
       
        if not friend:
            conn.close()
            return web.json_response({'status': 'error', 'message': 'User not found'})
       
        friend_id = friend[0]
        user_id = user_info['user_id']
       
        if friend_id == user_id:
            conn.close()
            return web.json_response({'status': 'error', 'message': 'Cannot add yourself as friend'})
       
        cursor.execute("SELECT status FROM friendships WHERE user_id = %s AND friend_id = %s", (user_id, friend_id))
        existing = cursor.fetchone()
       
        if existing:
            conn.close()
            return web.json_response({'status': 'error', 'message': f'Friend request already exists with status: {existing[0]}'})
       
        # --- FIX: Insert two records for a mutual friendship ---
        # Record: You added them
        cursor.execute(
            "INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, %s)",
            (user_id, friend_id, 'accepted')
        )
        # Record: They added you
        cursor.execute(
            "INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, %s)",
            (friend_id, user_id, 'accepted')
        )
       
        conn.commit()
        conn.close()
       
        print(f"✅ [Friend] {user_info['username']} and {friend_username} are now friends.")
       
        return web.json_response({
            'status': 'success',
            'message': f'You are now friends with {friend_username}'
        })
       
    except Exception as e:
        print(f"❌ [Friend] Error: {e}")
        return web.json_response({'status': 'error', 'message': 'Internal server error'}, status=500)
    


async def api_get_friends(request):
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
            SELECT f.user_id, u.username, f.created_at 
            FROM friendships f 
            JOIN users u ON f.user_id = u.user_id 
            WHERE f.friend_id = %s AND f.status = 'accepted'
        """, (user_info['user_id'],))
        
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
    
# Add these functions to your server code:


async def handle_get_friends_websocket(ws, user_info):
    """Handle get friends list via WebSocket"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all friends where current user is the one who has friends
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
                'created_at': str(row[2])
            })
        
        conn.close()
        
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Search for user by username
        cursor.execute(
            "SELECT user_id, username FROM users WHERE username = %s",
            (search_username,)
        )
        user = cursor.fetchone()
        
        conn.close()
        
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

# Update your handle_friend_websocket_message function:

async def handle_friend_websocket_message(ws, user_info, data):
    """Handle friend-related WebSocket messages"""
    message_type = data.get('type')
    
    try:
        # if message_type == 'get_friends_list':
        #     await handle_get_friends_websocket(ws, user_info)
        if message_type == 'add_friend':
            await handle_add_friend_websocket(ws, user_info, data)
        elif message_type == 'search_user':
            await handle_search_user_websocket(ws, user_info, data)
        else:
            # Return unhandled message
            return False
        return True
    except Exception as e:
        error_response = {
            'type': 'error',
            'message': f'Error handling {message_type}: {str(e)}',
            'timestamp': time.time()
        }
        await ws.send_str(json.dumps(error_response))
        return True
    

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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
            conn.close()
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
            conn.close()
            return
        
        # Check if friendship already exists (either direction)
        cursor.execute(
            "SELECT status FROM friendships WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)",
            (user_info['user_id'], friend_id, friend_id, user_info['user_id'])
        )
        existing = cursor.fetchone()
        
        if existing:
            error_response = {
                'type': 'add_friend_response',
                'status': 'error',
                'message': f'Already friends with {friend_username}',
                'timestamp': time.time()
            }
            await ws.send_str(json.dumps(error_response))
            conn.close()
            return
        
        # Add bidirectional friendship with accepted status (auto-accept)
        # User -> Friend
        cursor.execute(
            "INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, %s)",
            (user_info['user_id'], friend_id, 'accepted')
        )
        
        # Friend -> User (bidirectional)
        cursor.execute(
            "INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, %s)",
            (friend_id, user_info['user_id'], 'accepted')
        )
        
        conn.commit()
        conn.close()
        
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
        await ws.send_str(json.
        dumps(error_response))

# Add this function to your server code:

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
        
        # Use the same login logic as your HTTP endpoint
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Find user by username
            cursor.execute(
                "SELECT user_id, username, password_hash FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()
            
            if user and verify_password(password, user[2]):
                user_id, db_username, _ = user
                
                print(f"✅ [WS-Auth] User logged in: {username} (ID: {user_id})")
                
                # Create JWT token
                token = create_jwt_token(user_id, username)
                session_id = str(uuid.uuid4())
                
                # Send success response
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
                # Invalid credentials
                error_response = {
                    'type': 'login_response',
                    'status': 'error',
                    'message': 'Invalid username or password'
                }
                await ws.send_str(json.dumps(error_response))
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ [WS-Auth] Login error: {e}")
        error_response = {
            'type': 'login_response',
            'status': 'error',
            'message': 'Internal server error'
        }
        await ws.send_str(json.dumps(error_response))

# Update your websocket_handler function to handle login requests:

# Add this function to your server code:

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
        
        # Use the same login logic as your HTTP endpoint
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Find user by username
            cursor.execute(
                "SELECT user_id, username, password_hash FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()
            
            if user and verify_password(password, user[2]):
                user_id, db_username, _ = user
                
                print(f"✅ [WS-Auth] User logged in: {username} (ID: {user_id})")
                
                # Create JWT token
                token = create_jwt_token(user_id, username)
                session_id = str(uuid.uuid4())
                
                # Send success response
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
                # Invalid credentials
                error_response = {
                    'type': 'login_response',
                    'status': 'error',
                    'message': 'Invalid username or password'
                }
                await ws.send_str(json.dumps(error_response))
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ [WS-Auth] Login error: {e}")
        error_response = {
            'type': 'login_response',
            'status': 'error',
            'message': 'Internal server error'
        }
        await ws.send_str(json.dumps(error_response))

# Update your websocket_handler function to handle login requests:

# 

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
            is_friends_connection = 'auto_friends' in session_id.lower() or 'friends' in session_id.lower()
            
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
            
        except json.JSONDecodeError:
            await ws.send_str(json.dumps({'error': 'Invalid message format'}))
            return ws
        
        # Handle messages after authentication (only if user is authenticated)
        if user_info:
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
                        
                        # Handle as regular message
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
                        
                elif msg.type == WSMsgType.ERROR:
                    print(f'❌ [WS] Error from {user_info["username"] if user_info else "unauthenticated"}: {ws.exception()}')
                    break
    
    except asyncio.TimeoutError:
        print(f"⏰ WebSocket timeout from {client_ip}")
        await ws.send_str(json.dumps({'error': 'Message timeout'}))
    except Exception as e:
        print(f"❌ [WS] Exception: {e}")
    finally:
        if user_info and ws in auth_bridge.websocket_clients:
            auth_bridge.remove_websocket_client(ws)
    
    return ws

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
            conn = get_db_connection()
            cursor = conn.cursor()
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
                    'created_at': str(row[2])
                })
            conn.close()
            
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
        
        # Use the same registration logic as your HTTP endpoint
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Insert new user
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password)
            )
            user_id = cursor.lastrowid
            conn.commit()
            
            print(f"✅ [WS-Auth] New user registered: {username} (ID: {user_id})")
            
            # Create JWT token
            token = create_jwt_token(user_id, username)
            session_id = str(uuid.uuid4())
            
            # Send success response
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
            # Username already exists
            error_response = {
                'type': 'register_response',
                'status': 'error',
                'message': 'Username already exists'
            }
            await ws.send_str(json.dumps(error_response))
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ [WS-Auth] Registration error: {e}")
        error_response = {
            'type': 'register_response',
            'status': 'error',
            'message': 'Internal server error'
        }
        await ws.send_str(json.dumps(error_response))


async def api_get_stats(request):
    """Get enhanced statistics"""
    auth_bridge.update_user_stats()
    
    response_data = {
        "status": "success",
        "stats": auth_bridge.stats,
        "timestamp": time.time()
    }
    
    return web.json_response(response_data)

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
        print("📡 WebSocket: wss://localhost:8443/")
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