import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QStackedWidget)
from PyQt5.QtCore import Qt, pyqtSlot
from login_page import LoginPage
from register_page import RegisterPage
from friend_list_page import FriendListPage
from home_page import HomePage


class MessengerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_user = None  # Store logged in user info
        self.auth_token = None    # Store authentication token
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Messenger")
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)  # Larger default size for friend list
        
        # Central widget with stacked layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Stacked widget to switch between pages
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        
        # Create pages
        self.login_page = LoginPage()
        self.register_page = RegisterPage()
        self.home_page = HomePage()
        self.friend_list_page = FriendListPage()
        
        # Connect authentication page signals
        self.login_page.switch_to_register.connect(self.show_register)
        self.register_page.switch_to_login.connect(self.show_login)
        
        # Connect login success signal
        self.login_page.backend.login_response.connect(self.handle_login_success)
        self.register_page.register_attempted.connect(self.handle_register_data)
        
        # Connect page navigation signals
        self.home_page.friend_list_requested.connect(self.show_friend_list)
        self.friend_list_page.home_requested.connect(self.show_home)
        self.friend_list_page.logout_requested.connect(self.logout_user)
        
        # Connect start chat signal - KEY CONNECTION
        self.friend_list_page.start_chat_requested.connect(self.start_chat_with_friend)
        
        # Add pages to stack
        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.addWidget(self.register_page)
        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.friend_list_page)
        
        # Start with login page
        self.stacked_widget.setCurrentWidget(self.login_page)
    
    @pyqtSlot(dict)
    def handle_login_success(self, login_response):
        """Handle successful login and set up pages"""
        if login_response.get('status') == 'success':
            # Store user information
            self.auth_token = login_response.get('token')
            username = login_response.get('user', {}).get('username') or login_response.get('username')
            user_id = login_response.get('user', {}).get('user_id')
            
            self.current_user = {
                "username": username,
                "user_id": user_id,
                "token": self.auth_token,
                "login_time": login_response.get("timestamp")
            }
            
            print(f"✅ User logged in: {username} (ID: {user_id})")
            print(f"🔑 Auth token: {self.auth_token[:20] if self.auth_token else 'None'}...")
            
            # Set auth token and user info in all pages
            self.home_page.set_auth_token(self.auth_token)
            self.home_page.set_current_user(self.current_user)
            self.friend_list_page.set_auth_token(self.auth_token)
            self.friend_list_page.backend.conversations_received.connect(self.forward_conversations_to_home)

            # Connect friend list backend signals AFTER successful login (only once)
            if not hasattr(self, '_backend_signals_connected'):
                self.friend_list_page.backend.connection_established.connect(self.on_friend_backend_connected)
                self.friend_list_page.backend.friends_loaded.connect(self.on_friends_loaded)
                self.friend_list_page.backend.error_occurred.connect(self.on_friend_backend_error)
                self._backend_signals_connected = True
            
            # Navigate to friend list page (changed from home page)
            self.show_friend_list()
        else:
            print(f"❌ Login failed: {login_response.get('message', 'Unknown error')}")
    
    @pyqtSlot()
    def on_friend_backend_connected(self):
        """Handle when friend list backend connects successfully"""
        print("✅ Friend list backend connected - friends loading...")
    
    @pyqtSlot(list)
    def on_friends_loaded(self, friends_list):
        """Handle when friends are loaded from server"""
        print(f"✅ Friends loaded in main app: {len(friends_list)} friends")
        
        # Update window title to show friend count
        if self.current_user:
            username = self.current_user['username']
            count = len(friends_list)
            self.setWindowTitle(f"Messenger - {username} ({count} friends)")
    
    @pyqtSlot(str)
    def on_friend_backend_error(self, error_message):
        """Handle friend backend errors"""
        print(f"❌ Friend backend error: {error_message}")
        
        # If authentication error, logout user
        if "authentication" in error_message.lower() or "token" in error_message.lower():
            print("🔓 Authentication error detected, logging out...")
            self.logout_user()
    
    @pyqtSlot(dict)
    def forward_conversations_to_home(self, friend_conversations):
        """Forward conversations from friend list backend to home page"""
        print(f"📚 [MAIN] Forwarding {len(friend_conversations)} conversations to home page...")
    
    # Forward to home page
        if hasattr(self, 'home_page'):
            self.home_page.handle_chat_history(friend_conversations)
            print("✅ [MAIN] Conversations forwarded to home page")
        else:
            print("❌ [MAIN] Home page not found")
    
    @pyqtSlot(str)
    def start_chat_with_friend(self, friend_username):
        """Start a chat with the selected friend and switch to home page"""
        print(f"🗨️ Main App: Starting chat with {friend_username}")
        
        # Debug: Check if home_page exists and has required methods
        print(f"🔍 DEBUG: home_page exists: {hasattr(self, 'home_page')}")
        print(f"🔍 DEBUG: start_chat_with_friend method exists: {hasattr(self.home_page, 'start_chat_with_friend')}")
        print(f"🔍 DEBUG: add_chat_to_list method exists: {hasattr(self.home_page, 'add_chat_to_list')}")
        
        try:
            # IMPORTANT: Switch to home page FIRST
            print("🏠 Switching to home page first...")
            self.show_home()
            
            # Then add the friend to chat list
            print(f"📝 Adding {friend_username} to chat list...")
            self.home_page.add_chat_to_list(friend_username)
            
            # Finally start the chat interface
            print(f"💬 Starting chat interface with {friend_username}...")
            self.home_page.start_chat_with_friend(friend_username)
            
            print(f"✅ Chat with {friend_username} started successfully!")
            
        except Exception as e:
            print(f"❌ Error starting chat with {friend_username}: {e}")
            import traceback
            traceback.print_exc()
    
    def show_register(self):
        """Switch to register page"""
        self.stacked_widget.setCurrentWidget(self.register_page)
        # Clear register form
        self.register_page.username_input.clear()
        self.register_page.password_input.clear()
        self.register_page.username_input.setFocus()
    
    def show_login(self):
        """Switch to login page"""
        self.stacked_widget.setCurrentWidget(self.login_page)
        # Clear login form
        self.login_page.username_input.clear()
        self.login_page.password_input.clear()
        self.login_page.username_input.setFocus()
    
    def show_home(self):
        """Navigate to home page"""
        print("🏠 Switching to home page...")
        self.stacked_widget.setCurrentWidget(self.home_page)
        
        self.home_page.show_page() 
        # Update sidebar states
        self.home_page.sidebar.set_active_page("home")
        self.friend_list_page.sidebar.set_active_page("home")
    
        
        # Update window title
        if self.current_user:
            username = self.current_user['username']
            self.setWindowTitle(f"Messenger - {username}")
    
    def show_friend_list(self):
        """Navigate to friend list page"""
        print("👥 Switching to friend list page...")
        self.stacked_widget.setCurrentWidget(self.friend_list_page)
        
        # Update sidebar states
        self.home_page.sidebar.set_active_page("friend_list")
        self.friend_list_page.sidebar.set_active_page("friend_list")
        
        # Update window title to include username
        if self.current_user:
            username = self.current_user['username']
            self.setWindowTitle(f"Messenger - {username}")
        
        # Clear any search text
        self.friend_list_page.clear_search()
        
        # Focus on search input for better UX
        self.friend_list_page.search_input.setFocus()
    
    def refresh_friends_list(self):
        """Manually refresh the friends list"""
        if self.auth_token and self.friend_list_page.backend and self.friend_list_page.backend.is_connected:
            print("🔄 Manually refreshing friends list...")
            self.friend_list_page.backend.load_friends_list()
        else:
            print("❌ Cannot refresh friends: not connected to server")
    
    def logout_user(self):
        """Logout current user and return to login page"""
        username = self.current_user['username'] if self.current_user else 'Unknown'
        print(f"🔓 Logging out user: {username}")
        
        # Disconnect friend list backend first
        if hasattr(self.friend_list_page, 'backend') and self.friend_list_page.backend:
            print("🔌 Disconnecting friend list backend...")
            self.friend_list_page.backend.disconnect_from_server()
        
        # Disconnect login backend
        if hasattr(self.login_page, 'backend') and self.login_page.backend:
            print("🔌 Disconnecting login backend...")
            self.login_page.backend.disconnect_from_server()
        
        # Clear user data
        self.current_user = None
        self.auth_token = None
        
        # Reset window title
        self.setWindowTitle("Messenger")
        
        # Clear friend list display
        self.friend_list_page.friends_list = []
        self.friend_list_page.update_friends_display()
        
        # Reset home page
        self.home_page.set_current_user(None)
        self.home_page.set_auth_token(None)
        
        # Return to login page
        self.show_login()
    
    @pyqtSlot(str)
    def handle_register_data(self, json_data):
        """Handle register JSON data - you can send this to your server"""
        print("=== REGISTER DATA READY FOR SERVER ===")
        print(json_data)
        print("=" * 40)
        # Here you would typically send the JSON data to your server
        # For example: send_to_server(json_data)
    
    def closeEvent(self, event):
        """Handle application close event"""
        print("🔄 Application closing, cleaning up...")
        
        # Cleanup all backend connections
        if hasattr(self.friend_list_page, 'backend') and self.friend_list_page.backend:
            print("🧹 Cleaning up friend list backend...")
            self.friend_list_page.backend.disconnect_from_server()
        
        if hasattr(self.login_page, 'backend') and self.login_page.backend:
            print("🧹 Cleaning up login backend...")
            self.login_page.backend.disconnect_from_server()
        
        event.accept()
        print("✅ Application closed cleanly")


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = MessengerApp()
    window.show()
    
    print("🚀 Messenger application started")
    print("📋 Navigation flow:")
    print("   1. Login/Register")
    print("   2. Friend list page (default after login)")
    print("   3. Add friends using + Add Friend button")
    print("   4. Click friend → Start Chat modal → Start Chat → Switch to Home with that friend")
    print("   5. Home page shows friend in chat list and chat interface")
    print("   6. Logout returns to login screen")
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()