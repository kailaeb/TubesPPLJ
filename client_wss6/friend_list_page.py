from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QScrollArea, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont
from add_friend import AddFriendModal
from friend_list_backend import FriendListBackend
from navigation_sidebar import NavigationSidebar


class StartChatModal(QWidget):
    """Modal popup for starting a chat with selected friend"""
    
    start_chat_requested = pyqtSignal(str)  # Emit friend username when start chat is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setParent(parent)
        if parent:
            self.resize(parent.size())
        
        # Set up as overlay
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")  # Semi-transparent overlay
        
        self.selected_friend = None
        self.setup_ui()
        self.hide()
    
    def setup_ui(self):
        """Setup the modal UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignCenter)
        
        # Modal container
        self.modal_container = QFrame()
        self.modal_container.setFixedSize(400, 200)
        self.modal_container.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border: 2px solid #B0C4C6;
                border-radius: 15px;
            }
        """)
        
        # Layout for modal content
        container_layout = QVBoxLayout(self.modal_container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(20)
        container_layout.setAlignment(Qt.AlignCenter)
        
        # Close button
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 20px;
                font-weight: bold;
                color: #7F8C8D;
                max-width: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                color: #C0392B;
            }
        """)
        close_btn.clicked.connect(self.hide)
        
        # Header layout
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        # Friend name label
        self.friend_name_label = QLabel("Friend Name")
        self.friend_name_label.setAlignment(Qt.AlignCenter)
        self.friend_name_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2C2C2C;
                background-color: transparent;
                border: none;
            }
        """)
        
        # Start Chat button
        self.start_chat_btn = QPushButton("Start Chat")
        self.start_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #9DB4B8;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #8BA5A9;
            }
            QPushButton:pressed {
                background-color: #7A9499;
            }
        """)
        self.start_chat_btn.clicked.connect(self.start_chat)
        
        # Add widgets to container
        container_layout.addLayout(header_layout)
        container_layout.addWidget(self.friend_name_label)
        container_layout.addWidget(self.start_chat_btn, 0, Qt.AlignCenter)
        
        # Add modal to main layout
        main_layout.addWidget(self.modal_container)
    
    def show_for_friend(self, friend_username):
        """Show the modal for a specific friend"""
        self.selected_friend = friend_username
        self.friend_name_label.setText(friend_username)
        
        # Resize to parent size
        if self.parent():
            self.resize(self.parent().size())
        
        self.show()
        self.raise_()
    
    def start_chat(self):
        """Handle start chat button click"""
        if self.selected_friend:
            print(f"🗨️ Start chat requested for: {self.selected_friend}")
            self.start_chat_requested.emit(self.selected_friend)
        
        self.hide()
    
    def resizeEvent(self, event):
        """Handle parent resize"""
        if self.parent():
            self.resize(self.parent().size())
        super().resizeEvent(event)


class FriendListPage(QWidget):
    """Friend List page - frontend only, uses backend for server communication"""
    
    friend_selected = pyqtSignal(str)  # Emit friend name when selected
    start_chat_requested = pyqtSignal(str)  # Emit when start chat is requested
    home_requested = pyqtSignal()  # Emit when home navigation is requested
    logout_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.friends_list = []  # Will store friend data
        self.original_friends_list = []  # Store original unfiltered list
        self.auth_token = None  # Store authentication token
        self.add_friend_modal = AddFriendModal(parent=self, auth_token=None)
        self.add_friend_modal.friend_added.connect(self.on_friend_added)
        self.friend_containers = {}  # Store friend UI containers
        
        # Create start chat modal
        self.start_chat_modal = StartChatModal(parent=self)
        self.start_chat_modal.start_chat_requested.connect(self.on_start_chat_requested)
        
        # Create navigation sidebar
        self.sidebar = NavigationSidebar(active_page="friend_list")
        self.sidebar.home_clicked.connect(self.on_home_clicked)
        
        # Setup UI first
        self.setup_ui()
        
        # Initialize backend
        self.backend = FriendListBackend()
        self.setup_backend_connections()
        
        # DON'T connect to server here - wait for auth token
        print("🔧 Friend list page initialized, waiting for auth token...")
    
    def setup_backend_connections(self):
        """Connect backend signals to frontend handlers"""
        print("🔗 Setting up backend signal connections...")
        self.backend.connection_established.connect(self.on_backend_connected)
        self.backend.connection_failed.connect(self.on_backend_connection_failed)
        self.backend.friends_loaded.connect(self.on_friends_loaded)
        self.backend.error_occurred.connect(self.on_backend_error)
        print("✅ Backend signal connections established")
    
    def set_auth_token(self, token):
        """Set authentication token and trigger friend loading"""
        self.auth_token = token
        print(f"🔑 Friend list page received token: {token[:20] if token else 'None'}...")
        
        # Set token in backend
        if self.backend:
            print(f"🔑 Setting token in friend list backend...")
            self.backend.set_auth_token(token)
            print(f"✅ Token set in friend list backend")
        
        # Set token in add friend modal
        if hasattr(self, 'add_friend_modal') and self.add_friend_modal:
            print(f"🔑 Setting token in add friend modal...")
            self.add_friend_modal.set_auth_token(token)
            print(f"✅ Token set in add friend modal")
    
    def setup_ui(self):
        """Setup the friend list page UI"""
        # Main layout - horizontal split
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add navigation sidebar
        main_layout.addWidget(self.sidebar)
        
        # Main content area
        self.setup_main_content(main_layout)
    
    def setup_left_sidebar(self, parent_layout):
        """Setup the left sidebar with navigation - REMOVED (now using NavigationSidebar)"""
        pass
    
    def setup_main_content(self, parent_layout):
        """Setup the main content area"""
        main_content = QFrame()
        main_content.setStyleSheet("""
            QFrame {
                background-color: #9DB4B8;
            }
        """)
        
        content_layout = QVBoxLayout(main_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Top bar with search and add friend
        self.setup_top_bar(content_layout)
        
        # Friends content area
        self.setup_friends_area(content_layout)
        
        parent_layout.addWidget(main_content)
    
    def setup_top_bar(self, parent_layout):
        """Setup the top bar with search and add friend button"""
        top_bar = QFrame()
        top_bar.setFixedHeight(80)
        top_bar.setStyleSheet("""
            QFrame {
                background-color: #9DB4B8;
                border-bottom: 2px solid #7A9499;
            }
        """)
        
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 15, 20, 15)
        top_layout.setSpacing(20)
        
        search_container = QFrame()
        search_container.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;;
                border: 1px solid #B0C4C6;
                border-radius: 8px;
            }
            QFrame:focus-within {
                border: 2px solid #7A9499;
            }
        """)
        
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(15, 0, 0, 0)
        search_layout.setSpacing(10)
        
        # Search icon
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 18px;
                background-color: transparent;
                border: none;
            }
        """)
        
        # Search input (no border since container handles it)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for friends...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                padding: 0px;
                font-size: 16px;
                color: #2C2C2C;
            }
        """)
        
        self.search_input.setFixedHeight(50)
        self.search_input.setMinimumWidth(400)
        
        # Connect search functionality - automatic as you type
        self.search_input.textChanged.connect(self.search_friends_auto)
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        
        # Add Friend button
        add_friend_btn = QPushButton("+ Add Friend")
        add_friend_btn.setStyleSheet("""
            QPushButton {
                background-color: #7A9499;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6B8387;
            }
            QPushButton:pressed {
                background-color: #5A7175;
            }
        """)
        add_friend_btn.setFixedHeight(50)
        add_friend_btn.clicked.connect(self.show_add_friend_modal)
        
        # Add to top layout
        top_layout.addWidget(search_container)
        top_layout.addStretch()
        top_layout.addWidget(add_friend_btn)
        
        parent_layout.addWidget(top_bar)
    
    def setup_friends_area(self, parent_layout):
        """Setup the friends list area"""
        # Create scroll area for friends
        self.friends_scroll_area = QScrollArea()
        self.friends_scroll_area.setWidgetResizable(True)
        self.friends_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.friends_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.friends_scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #9DB4B8;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #7A9499;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #5A7175;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4A6165;
            }
        """)
        
        # Container widget for the scroll area
        self.friends_container_widget = QWidget()
        self.friends_container_widget.setStyleSheet("""
            QWidget {
                background-color: #9DB4B8;
            }
        """)
        
        # Layout for friends
        self.friends_layout = QVBoxLayout(self.friends_container_widget)
        self.friends_layout.setContentsMargins(20, 20, 20, 20)
        self.friends_layout.setSpacing(10)
        self.friends_layout.setAlignment(Qt.AlignTop)
        
        # Set the container widget to the scroll area
        self.friends_scroll_area.setWidget(self.friends_container_widget)
        
        # Initially show "No friends" message
        self.show_no_friends_message()
        
        parent_layout.addWidget(self.friends_scroll_area)
    
    def show_add_friend_modal(self):
        """Show the add friend modal"""
        try:
            # Make sure modal has current auth token
            if self.auth_token:
                print(f"🔑 Setting token in add friend modal: {self.auth_token[:20]}...")
                self.add_friend_modal.set_auth_token(self.auth_token)
            else:
                print("⚠️ No auth token available for add friend modal")
            
            # Show the modal
            self.add_friend_modal.show_modal()
            print("📱 Add friend modal shown")
            
        except Exception as e:
            print(f"❌ Error showing add friend modal: {e}")
    
    def search_friends_auto(self, search_text):
        """Auto-search friends as user types - with stable layout"""
        search_text = search_text.strip().lower()
        
        if not search_text:
            # If empty search, show all friends
            self.friends_list = self.original_friends_list.copy()
            self.update_friends_display()
            return
        
        print(f"🔍 Auto-searching for: '{search_text}' in friends list")
        
        # Filter friends from existing list
        filtered_friends = [
            friend for friend in self.original_friends_list 
            if search_text in friend.get('display_name', '').lower() or 
               search_text in friend.get('username', '').lower()
        ]
        
        if filtered_friends:
            print(f"✅ Found {len(filtered_friends)} matching friends")
            self.friends_list = filtered_friends
            self.update_friends_display()
        else:
            print(f"❌ No friends found matching '{search_text}'")
            # Only show popup if search text is not empty and we have friends to search
            if len(self.original_friends_list) > 0:
                self.show_user_not_found_popup()
            # Keep current display - don't change to "No Friends Added"
            # Just keep showing the current friends list without updating
    
    def show_user_not_found_popup(self):
        """Show 'User not found' popup without changing the main layout"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Search Result")
        msg_box.setText("User not found!")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #E8E1E1;
            }
            QMessageBox QPushButton {
                background-color: #7A9499;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                min-width: 60px;
            }
            QMessageBox QPushButton:hover {
                background-color: #6B8387;
            }
        """)
        msg_box.exec_()
    
    def create_friend_widget(self, friend_info):
        """Create a widget for displaying a friend"""
        print(f"🔍 DEBUG: Creating widget for friend: {friend_info}")
        
        container = QFrame()
        container.setFixedHeight(80)
        
        # Style based on online status
        if friend_info.get('is_online', False):
            border_color = "#4CAF50"  # Green for online
            status_color = "#4CAF50"
        else:
            border_color = "#B0C4C6"  # Gray for offline
            status_color = "#757575"
        
        container.setStyleSheet(f"""
            QFrame {{
                background-color: #E8E1E1;
                border: 2px solid {border_color};
                border-radius: 15px;
                margin: 5px 0px 0px 0px;
                padding: 0px;
            }}
            QFrame:hover {{
                background-color: #D5CECE;
                border: 2px solid #9DB4B8;
            }}
        """)
        container.setCursor(Qt.PointingHandCursor)
        
        # Layout for the container
        layout = QHBoxLayout(container)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Friend name and status
        info_layout = QVBoxLayout()
        
        # Name label
        display_name = friend_info.get('display_name', friend_info.get('username', 'Unknown'))
        name_label = QLabel(display_name)
        name_label.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 18px;
                font-weight: bold;
                background-color: transparent;
                padding: 0px;
                margin: 0px 0px 0px 0px;
                border: none;
            }
        """)
        
        # Status label
        status_text = "🟢 Online" if friend_info.get('is_online', False) else "⚪ Offline"
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"""
            QLabel {{
                color: {status_color};
                font-size: 12px;
                background-color: transparent;
                border: none;
            }}
        """)
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(status_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Make container clickable - show start chat modal instead of direct friend selection
        def on_container_clicked():
            username = friend_info.get('username', 'Unknown')
            print(f"🔗 Friend clicked: {username} - showing start chat modal")
            self.start_chat_modal.show_for_friend(username)
        
        container.mousePressEvent = lambda event: on_container_clicked()
        
        print(f"✅ DEBUG: Widget created for {display_name}")
        return container
    
    @pyqtSlot(str)
    def on_start_chat_requested(self, friend_username):
        """Handle when start chat is requested from the modal"""
        print(f"🗨️ Start chat requested for: {friend_username}")
        self.start_chat_requested.emit(friend_username)
    
    @pyqtSlot()
    def on_home_clicked(self):
        """Handle when home button is clicked"""
        print("🏠 Home navigation requested from friend list")
        self.home_requested.emit()
    
    def show_no_friends_message(self):
        """Show the no friends message"""
        # Clear existing widgets
        self.clear_friends_layout()
        
        # Create no friends message
        no_friends_frame = QFrame()
        no_friends_frame.setFixedSize(400, 120)
        no_friends_frame.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border: 2px solid #B0C4C6;
                border-radius: 15px;
            }
        """)
        
        layout = QVBoxLayout(no_friends_frame)
        layout.setAlignment(Qt.AlignCenter)
        
        label = QLabel("No Friends Added")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 24px;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)
        
        layout.addWidget(label)
        
        # Center the message
        self.friends_layout.addStretch()
        self.friends_layout.addWidget(no_friends_frame, 0, Qt.AlignCenter)
        self.friends_layout.addStretch()
    
    def clear_friends_layout(self):
        """Clear all widgets from friends layout"""
        print(f"🔍 DEBUG: Clearing layout, current count: {self.friends_layout.count()}")
        
        # Remove all widgets
        while self.friends_layout.count():
            child = self.friends_layout.takeAt(0)
            if child.widget():
                print(f"🔍 DEBUG: Deleting widget: {child.widget()}")
                child.widget().deleteLater()
            
        print(f"🔍 DEBUG: Layout cleared, new count: {self.friends_layout.count()}")
    
    def update_friends_display(self):
        """Update the friends display with current friends list"""
        print(f"🔄 DEBUG: update_friends_display called")
        print(f"🔍 DEBUG: self.friends_list has {len(self.friends_list)} friends")
        print(f"🔍 DEBUG: friends_list content: {self.friends_list}")
        
        # Clear current display
        print(f"🔍 DEBUG: Clearing friends layout...")
        self.clear_friends_layout()
        
        if not self.friends_list or len(self.friends_list) == 0:
            print(f"🔍 DEBUG: No friends found, showing no friends message")
            # Show no friends message
            self.show_no_friends_message()
        else:
            print(f"🔍 DEBUG: Adding {len(self.friends_list)} friend widgets...")
            # Add friend widgets
            for i, friend_info in enumerate(self.friends_list):
                print(f"🔍 DEBUG: Creating widget for friend {i+1}: {friend_info}")
                friend_widget = self.create_friend_widget(friend_info)
                self.friends_layout.addWidget(friend_widget)
                print(f"🔍 DEBUG: Added widget for {friend_info.get('username', 'Unknown')}")
            
            # Add stretch to push friends to top
            self.friends_layout.addStretch()
            print(f"✅ DEBUG: All friend widgets added successfully")
        
        print(f"🔄 DEBUG: update_friends_display completed")
    
    # Backend signal handlers
    @pyqtSlot()
    def on_backend_connected(self):
        """Handle successful backend connection"""
        print("✅ Friend list backend connected successfully")
        self.backend.load_friends_list()
    
    @pyqtSlot(str)
    def on_backend_connection_failed(self, reason):
        """Handle backend connection failure"""
        print(f"❌ Friend list: Backend connection failed - {reason}")
    
    @pyqtSlot(list)
    def on_friends_loaded(self, friends_data):
        """Handle friends loaded from server"""
        print(f"📋 Friends loaded from server: {len(friends_data)} friends")
        print(f"🔍 DEBUG: Raw friends data received: {friends_data}")
        
        # IMPORTANT: Clear existing friends list first
        self.friends_list.clear()
        self.original_friends_list.clear()
        print(f"🔍 DEBUG: Cleared existing friends lists")
        
        # Convert friend data to expected format
        for i, friend in enumerate(friends_data):
            print(f"🔍 DEBUG: Processing friend {i+1}: {friend}")
            
            friend_info = {
                'username': friend.get('username', 'Unknown'),
                'display_name': friend.get('display_name') or friend.get('username', 'Unknown'),
                'status': friend.get('status', 'offline'),
                'is_online': friend.get('is_online', False),
                'user_id': friend.get('user_id', 0),
                'created_at': friend.get('created_at', '')
            }
            
            self.friends_list.append(friend_info)
            self.original_friends_list.append(friend_info.copy())  # Keep original copy
            print(f"🔍 DEBUG: Added friend to lists: {friend_info}")
        
        print(f"🔍 DEBUG: Final friends_list length: {len(self.friends_list)}")
        print(f"🔍 DEBUG: Final original_friends_list length: {len(self.original_friends_list)}")
        
        # Clear search input and force UI update
        self.search_input.clear()
        print(f"🔄 DEBUG: Calling update_friends_display()...")
        self.update_friends_display()
        print(f"✅ Friends display updated with {len(self.friends_list)} friends")
    
    @pyqtSlot(str)
    def on_backend_error(self, error_message):
        """Handle backend errors"""
        print(f"❌ Friend list backend error: {error_message}")
    
    def on_friend_added(self, username):
        """Handle when a friend is successfully added via modal"""
        print(f"✅ Friend added via modal: {username}")
        
        # Reload friends list from server to get updated data
        if self.backend and self.auth_token and self.backend.is_connected:
            print("🔄 Reloading friends list after adding friend...")
            self.backend.load_friends_list()
        else:
            print("⚠️ Cannot reload friends list - backend not connected")
    
    # Utility methods
    def clear_search(self):
        """Clear the search input and show all friends"""
        self.search_input.clear()
        self.friends_list = self.original_friends_list.copy()
        self.update_friends_display()
    
    def get_search_text(self):
        """Get current search text"""
        return self.search_input.text().strip()
    
    def get_friends_list(self):
        """Get the current friends list"""
        return self.friends_list.copy()
    
    def set_friends_list(self, friends_list):
        """Set the friends list (useful for loading from backend)"""
        self.friends_list = friends_list.copy()
        self.original_friends_list = friends_list.copy()
        self.update_friends_display()
    
    def cleanup(self):
        """Cleanup resources when page is destroyed"""
        if hasattr(self, 'backend'):
            print("🧹 Friend list: Cleaning up backend connection")
            self.backend.disconnect_from_server()