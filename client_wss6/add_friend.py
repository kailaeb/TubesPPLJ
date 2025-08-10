from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot
from PyQt5.QtGui import QPainter, QColor
from add_friend_backend import AddFriendBackend


class AddFriendModal(QWidget):
    """Modal overlay for adding friends - appears on top of main window"""
    
    friend_added = pyqtSignal(str)  # Emit friend username when successfully added
    modal_closed = pyqtSignal()     # Emit when modal is closed
    
    def __init__(self, parent=None, auth_token=None):
        super().__init__(parent)
        
        # Make this widget cover the entire parent
        self.setParent(parent)
        if parent:
            self.resize(parent.size())
        
        # Set up as overlay
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")  # Semi-transparent overlay
        
        # State variables
        self.search_result_username = None
        self.is_username_found = False
        self.search_in_progress = False
        
        # Initialize backend
        self.backend = AddFriendBackend(auth_token)
        self.setup_backend_connections()
        
        self.setup_ui()
        self.hide()  # Initially hidden
    
    def setup_backend_connections(self):
        """Connect backend signals to frontend handlers"""
        self.backend.search_user_response.connect(self.on_search_response)
        self.backend.add_friend_response.connect(self.on_add_friend_response)
        self.backend.error_occurred.connect(self.on_backend_error)
    
    def setup_ui(self):
        """Setup the modal UI as overlay"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignCenter)
        
        # Modal container (the grey box in the center)
        self.modal_container = QFrame()
        self.modal_container.setFixedSize(500, 300)
        self.modal_container.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border: 2px solid #B0C4C6;
                border-radius: 15px;
            }
        """)
        
        # Layout for the modal content
        container_layout = QVBoxLayout(self.modal_container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(20)
        
        # Header with close button
        self.setup_header(container_layout)
        
        # Search section
        self.setup_search_section(container_layout)
        
        # Result section
        self.setup_result_section(container_layout)
        
        # Buttons section
        self.setup_buttons_section(container_layout)
        
        # Add modal to main layout
        main_layout.addWidget(self.modal_container)
    
    def setup_header(self, parent_layout):
        """Setup header with title and close button"""
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel("Search Username")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2C2C2C;
                background-color: transparent;
                border: none;
            }
        """)
        
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
        close_btn.clicked.connect(self.close_modal)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        parent_layout.addLayout(header_layout)
    
    def setup_search_section(self, parent_layout):
        """Setup search input section"""
        # Search container that combines icon and input
        search_container = QFrame()
        search_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #B0C4C6;
                border-radius: 8px;
            }
            QFrame:focus-within {
                border: 2px solid #7A9499;
            }
        """)
        search_container.setFixedHeight(45)
        
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(15, 0, 15, 0)
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
        self.search_input.setPlaceholderText("Enter username...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                font-size: 16px;
                color: #2C2C2C;
            }
        """)
        
        # Connect input change to search
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.search_username)
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        
        parent_layout.addWidget(search_container)
    
    def setup_result_section(self, parent_layout):
        """Setup result display section"""
        # Result container - increased height to prevent cutting
        self.result_container = QFrame()
        self.result_container.setFixedHeight(80)  # Increased from 60 to 80
        self.result_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        
        result_layout = QVBoxLayout(self.result_container)
        result_layout.setContentsMargins(0, 5, 0, 5)  # Reduced margins
        result_layout.setAlignment(Qt.AlignCenter)
        
        # Username display (hidden initially)
        self.username_display = QLabel()
        self.username_display.setAlignment(Qt.AlignCenter)
        self.username_display.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2C2C2C;
                background-color: transparent;
                border: none;
                padding: 2px;
                margin: 0px;
            }
        """)
        self.username_display.hide()
        
        # Status message
        self.status_message = QLabel()
        self.status_message.setAlignment(Qt.AlignCenter)
        self.status_message.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                padding: 2px;
                margin: 0px;
            }
        """)
        self.status_message.hide()
        
        result_layout.addWidget(self.username_display)
        result_layout.addWidget(self.status_message)
        
        parent_layout.addWidget(self.result_container)
    
    def setup_buttons_section(self, parent_layout):
        """Setup action buttons section"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        # Add button (hidden initially)
        self.add_btn = QPushButton("Add")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #7A9499;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 25px;
                font-size: 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #6B8387;
            }
            QPushButton:pressed {
                background-color: #5A7175;
            }
        """)
        self.add_btn.setFixedHeight(45)
        self.add_btn.clicked.connect(self.add_friend)
        self.add_btn.hide()
        
        # Center the Add button
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addStretch()
        
        parent_layout.addLayout(buttons_layout)
    
    def show_modal(self):
        """Show the modal overlay"""
        # Resize to parent size
        if self.parent():
            self.resize(self.parent().size())
        
        # Reset modal state
        self.reset_modal()
        
        # Show and bring to front
        self.show()
        self.raise_()
        self.search_input.setFocus()
    
    def close_modal(self):
        """Close the modal overlay"""
        self.hide()
        self.modal_closed.emit()
    
    def resizeEvent(self, event):
        """Handle parent resize"""
        if self.parent():
            self.resize(self.parent().size())
        super().resizeEvent(event)
    
    def set_auth_token(self, token):
        """Set authentication token"""
        print(f"🔑 Setting auth token in modal: {token[:20] if token else 'None'}...")
        if self.backend:
            self.backend.set_auth_token(token)
    
    # Search functionality
    def on_search_text_changed(self, text):
        """Handle search input text changes - no auto-search"""
        if not text.strip():
            self.clear_result()
        # Removed auto-search - only search when Enter is pressed
    
    def search_username(self):
        """Search for username using backend - only when Enter pressed"""
        username = self.search_input.text().strip()
        
        if not username:
            self.clear_result()
            return
        
        if self.search_in_progress:
            print("🔍 Search already in progress, skipping...")
            return
        
        print(f"🔍 Starting search for username: '{username}'")
        self.search_in_progress = True
        
        # Don't show "Searching..." in UI - keep it clean
        self.clear_result()  # Clear any previous results
        
        # Use backend to search
        if self.backend:
            self.backend.search_user(username)
        else:
            print("❌ No backend available for search")
            self.search_in_progress = False
            self.show_username_not_found()
    
    # Backend signal handlers
    @pyqtSlot(dict)
    def on_search_response(self, response):
        """Handle search response from backend - matches actual backend format"""
        self.search_in_progress = False
        print(f"📨 Frontend received search response: {response}")
        
        if response.get("status") == "success":
            # Backend returns: {"status": "success", "data": {"user": {...}, "username": "...", "user_id": ...}}
            data = response.get("data", {})
            user = data.get("user", {})
            username = data.get("username") or user.get("username", "")
            
            if username:
                print(f"✅ Frontend: User found - {username}")
                self.show_username_found(username)
            else:
                print(f"❌ Frontend: No username in response - {data}")
                self.show_username_not_found()
        else:
            # Backend returns: {"status": "error", "message": "..."}
            error_msg = response.get("message", "Search failed")
            print(f"❌ Frontend: Search error - {error_msg}")
            self.show_username_not_found()
    
    @pyqtSlot(dict)
    def on_add_friend_response(self, response):
        """Handle add friend response from backend"""
        print(f"📨 Frontend received add friend response: {response}")
        
        if response.get("status") == "success":
            print(f"✅ Frontend: Friend added successfully")
            # Emit signal to parent
            if self.search_result_username:
                self.friend_added.emit(self.search_result_username)
            # Close modal
            self.close_modal()
        else:
            error_msg = response.get("message", "Add friend failed")
            print(f"❌ Frontend: Add friend error - {error_msg}")
            # Show error in status message
            self.status_message.setText(f"Error: {error_msg}")
            self.status_message.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #E74C3C;
                    background-color: transparent;
                    border: none;
                    padding: 5px;
                }
            """)
            self.status_message.show()
    
    @pyqtSlot(str)
    def on_backend_error(self, error_message):
        """Handle backend errors"""
        self.search_in_progress = False
        print(f"❌ Frontend: Backend error - {error_message}")
        self.show_username_not_found()
    
    # UI state methods
    def show_username_found(self, username):
        """Show username found result"""
        self.search_result_username = username
        self.is_username_found = True
        
        self.username_display.setText(username)
        self.username_display.show()
        
        self.status_message.setText("Username Found!")
        self.status_message.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #27AE60;
                background-color: transparent;
                border: none;
                padding: 5px;
            }
        """)
        self.status_message.show()
        
        self.add_btn.show()
        print(f"✅ Frontend: Showing username found - {username}")
    
    def show_username_not_found(self):
        """Show username not found result"""
        self.search_result_username = None
        self.is_username_found = False
        
        self.username_display.hide()
        
        self.status_message.setText("Username not Found!")
        self.status_message.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #E74C3C;
                background-color: transparent;
                border: none;
                padding: 2px;
                margin: 0px;
            }
        """)
        self.status_message.show()
        
        self.add_btn.hide()
        print(f"❌ Frontend: Showing username not found")
    
    def clear_result(self):
        """Clear search results"""
        self.search_result_username = None
        self.is_username_found = False
        self.search_in_progress = False
        
        self.username_display.hide()
        self.status_message.hide()
        self.add_btn.hide()
    
    def add_friend(self):
        """Add the found friend using backend"""
        if self.is_username_found and self.search_result_username:
            print(f"➕ Frontend: Adding friend - {self.search_result_username}")
            
            # Don't show "Adding friend..." in UI - keep it clean during the process
            self.add_btn.hide()
            
            # Use backend to add friend
            if self.backend:
                self.backend.add_friend(self.search_result_username)
            else:
                print("❌ Frontend: No backend available for add friend")
                self.show_username_not_found()
    
    def reset_modal(self):
        """Reset modal to initial state"""
        self.search_input.clear()
        self.clear_result()
        self.search_input.setFocus()