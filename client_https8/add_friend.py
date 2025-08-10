from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
import requests


class AddFriendModal(QDialog):
    """Modal dialog for adding friends"""
    
    friend_added = pyqtSignal(str)  # Emit friend username when successfully added
    
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend  # HttpClient instance
        self.setModal(True)
        self.setFixedSize(500, 300)
        self.setWindowTitle("Add Friend")
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(0, 0, 0, 150);
            }
        """)
        
        # State variables
        self.search_result_username = None
        self.is_username_found = False
        self.available_friends = []  # Store available friends from server
        
        self.setup_ui()
        self.center_on_parent()
        
        # Load available friends when modal opens
        self.load_available_friends()
    
    def load_available_friends(self):
        """Load available friends from server"""
        if not self.backend or not hasattr(self.backend, 'token'):
            print("❌ No authentication token available")
            return
        
        try:
            headers = {
                'Authorization': f'Bearer {self.backend.token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.backend.base_url}/api/available_friends",
                headers=headers,
                verify=False  # For self-signed certificates
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    self.available_friends = [friend['username'] for friend in data.get('available_friends', [])]
                    print(f"✅ Loaded {len(self.available_friends)} available friends")
                else:
                    print(f"❌ Server error: {data.get('message', 'Unknown error')}")
            else:
                print(f"❌ HTTP error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error loading available friends: {e}")
    
    def setup_ui(self):
        """Setup the modal UI"""
        # Main container
        container = QFrame(self)
        container.setGeometry(50, 50, 400, 200)
        container.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border: 2px solid #B0C4C6;
                border-radius: 15px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header with close button
        self.setup_header(layout)
        
        # Search section
        self.setup_search_section(layout)
        
        # Result section
        self.setup_result_section(layout)
        
        # Buttons section
        self.setup_buttons_section(layout)
    
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
        close_btn.clicked.connect(self.reject)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        parent_layout.addLayout(header_layout)
    
    def setup_search_section(self, parent_layout):
        """Setup search input section"""
        search_layout = QHBoxLayout()
        
        # Search icon
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 18px;
                padding: 10px;
            }
        """)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter username...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #B0C4C6;
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 16px;
                color: #2C2C2C;
            }
            QLineEdit:focus {
                border: 2px solid #7A9499;
            }
        """)
        self.search_input.setFixedHeight(45)
        
        # Connect input change to search
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.search_username)
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        
        parent_layout.addLayout(search_layout)
    
    def setup_result_section(self, parent_layout):
        """Setup result display section"""
        # Result container
        self.result_container = QFrame()
        self.result_container.setFixedHeight(60)
        self.result_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        
        result_layout = QVBoxLayout(self.result_container)
        result_layout.setContentsMargins(0, 10, 0, 10)
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
                padding: 5px;
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
                padding: 5px;
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
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #BDC3C7;
                color: #2C2C2C;
                border: none;
                border-radius: 8px;
                padding: 12px 25px;
                font-size: 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #A8B2B6;
            }
            QPushButton:pressed {
                background-color: #95A5AA;
            }
        """)
        self.cancel_btn.setFixedHeight(45)
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.cancel_btn)
        
        parent_layout.addLayout(buttons_layout)
    
    def center_on_parent(self):
        """Center the modal on the parent window"""
        if self.parent():
            parent_rect = self.parent().geometry()
            modal_rect = self.geometry()
            
            x = parent_rect.x() + (parent_rect.width() - modal_rect.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - modal_rect.height()) // 2
            
            self.move(x, y)
    
    def on_search_text_changed(self, text):
        """Handle search input text changes"""
        if not text.strip():
            self.clear_result()
        else:
            # Auto-search after a short delay (debouncing)
            if hasattr(self, 'search_timer'):
                self.search_timer.stop()
            
            self.search_timer = QTimer()
            self.search_timer.singleShot(500, self.search_username)  # 500ms delay
    
    def search_username(self):
        """Search for username (check against server data)"""
        username = self.search_input.text().strip()
        
        if not username:
            self.clear_result()
            return
        
        # Check against available friends from server
        self.simulate_username_search(username)
    
    def simulate_username_search(self, username):
        """Check if username exists in available friends from server"""
        if username in self.available_friends:
            self.show_username_found(username)
        else:
            self.show_username_not_found()
    
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
                padding: 5px;
            }
        """)
        self.status_message.show()
        
        self.add_btn.hide()
    
    def clear_result(self):
        """Clear search results"""
        self.search_result_username = None
        self.is_username_found = False
        
        self.username_display.hide()
        self.status_message.hide()
        self.add_btn.hide()
    
    def add_friend(self):
        """Add the found friend via server API"""
        if not self.is_username_found or not self.search_result_username:
            return
        
        if not self.backend or not hasattr(self.backend, 'token'):
            print("❌ No authentication token available")
            return
        
        try:
            headers = {
                'Authorization': f'Bearer {self.backend.token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'username': self.search_result_username
            }
            
            response = requests.post(
                f"{self.backend.base_url}/api/add_friend",
                headers=headers,
                json=data,
                verify=False
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    print(f"✅ Friend added successfully: {self.search_result_username}")
                    
                    # Emit signal to refresh friend list
                    self.friend_added.emit(self.search_result_username)
                    
                    # Close the modal
                    self.accept()
                else:
                    print(f"❌ Failed to add friend: {result.get('message')}")
            else:
                print(f"❌ Server error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error adding friend: {e}")
    
    def reset_modal(self):
        """Reset modal to initial state"""
        self.search_input.clear()
        self.clear_result()
        self.search_input.setFocus()
        
        # Reload available friends in case list changed
        self.load_available_friends()