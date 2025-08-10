#!/usr/bin/env python3
"""
Test script to view FriendListPage frontend without logging in
Run this to check if the design matches your expectations
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt

# Create a mock backend class to avoid import errors
class MockFriendListBackend:
    def __init__(self):
        self.auth_token = None
        self.is_connected = False
    
    def set_auth_token(self, token):
        self.auth_token = token
        print(f"🔑 Mock: Would set auth token")
    
    def connect_to_server(self):
        print("🔌 Mock: Would connect to server")
    
    def load_friends_list(self):
        print("📋 Mock: Would load friends from server")
    
    def disconnect_from_server(self):
        print("🔌 Mock: Would disconnect from server")

# Mock the backend module to avoid import errors
sys.modules['friend_list_backend'] = type('MockModule', (), {
    'FriendListBackend': MockFriendListBackend
})()

# Mock the add friend modal to avoid import errors  
sys.modules['add_friend'] = type('MockModule', (), {
    'AddFriendModal': type('MockAddFriendModal', (), {
        '__init__': lambda self, parent: None,
        'friend_added': type('MockSignal', (), {'connect': lambda self, slot: None})(),
        'reset_modal': lambda self: None,
        'exec_': lambda self: None
    })
})()

# Import your friend list page AFTER mocking
from friend_list_page import FriendListPage


class TestFriendListWindow(QMainWindow):
    """Test window to display friend list page"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Friend List Page - Frontend Test")
        self.setGeometry(100, 100, 1200, 800)  # Width, Height similar to your main app
        
        # Create the friend list page
        self.friend_list_page = TestableFriendListPage()
        self.setCentralWidget(self.friend_list_page)
        
        # Add some test friends to see how it looks
        self.add_test_friends()
    
    def add_test_friends(self):
        """Add some test friends to see the UI"""
        test_friends = ["Alice", "Bob", "Luffy", "Muhammad_Ilman", "john_doe"]
        
        for friend in test_friends:
            self.friend_list_page.add_friend(friend)
        
        print("✅ Added test friends - you should see grey containers")
        print("🔍 Try using the search box to filter friends")
        print("➕ Try clicking 'Add Friend' button (will add test friend)")


class TestableFriendListPage(FriendListPage):
    """Modified FriendListPage that works without real backend"""
    
    def setup_backend_connections(self):
        """Override - no backend connections needed for testing"""
        pass
    
    def show_add_friend_modal(self):
        """Show add friend modal without backend"""
        print("➕ Add Friend button clicked")
        
        # Add a test friend instead of showing modal
        test_username = f"TestUser_{len(self.friends_list) + 1}"
        self.add_friend(test_username)
        print(f"✅ Added test friend: {test_username}")
    
    def on_friend_added(self, username):
        """Handle friend added (no backend needed)"""
        self.add_friend(username)
        print(f"✅ Friend added: {username}")
    
    def on_backend_connected(self):
        """Mock backend connected"""
        print("🔗 Mock: Backend connected")
    
    def on_backend_connection_failed(self, reason):
        """Mock backend connection failed"""
        print(f"❌ Mock: Backend connection failed - {reason}")
    
    def on_friends_loaded(self, friends_list):
        """Mock friends loaded"""
        print(f"📋 Mock: Friends loaded: {friends_list}")
        self.friends_list = friends_list.copy()
        self.update_friends_display()
    
    def on_backend_error(self, error_message):
        """Mock backend error"""
        print(f"❌ Mock: Backend error - {error_message}")


def main():
    """Main function to run the test"""
    app = QApplication(sys.argv)
    
    # Set application style (optional)
    app.setStyle('Fusion')  # Modern look
    
    # Create and show the test window
    window = TestFriendListWindow()
    window.show()
    
    print("\n🎨 Friend List Frontend Test Running...")
    print("=" * 50)
    print("✅ Window should display with test friends")
    print("🔍 Try searching for friends in the search box")
    print("➕ Click 'Add Friend' to add test friends")
    print("🖱️ Click on friend containers to test selection")
    print("❌ Close window or press Ctrl+C to exit")
    print("=" * 50)
    
    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()