# http_add_friend_modal.py
# This file is a modified version of your add_friend.py

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot
import requests

class AddFriendModal(QDialog):
    """Modal dialog for adding friends, using HttpClient."""
    friend_successfully_added = pyqtSignal()
    
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.available_friends = [] 
        self.search_result_username = None
        self.is_username_found = False
        self.search_result_username = None
        
        # --- FIX: Set window properties correctly ---
        self.setWindowTitle("Add Friend")
        self.setModal(True) # This ensures it behaves like a proper modal popup
        self.setStyleSheet("background-color: #F0F0F0;") # A neutral background

        self.setup_ui()
        # self.center_on_parent() # Layouts will handle centering better
        self.setup_backend_connections()
        
        # Pre-fetch users when modal is created
        self.backend.get_users()

        # self.load_available_friends()

    def setup_backend_connections(self):
        self.backend.users_fetched.connect(self.on_users_fetched)
        self.backend.friend_added_response.connect(self.on_friend_added_response)
        self.backend.error_occurred.connect(self.on_backend_error)

    def on_users_fetched(self, users):
        print("✅ Users list fetched for searching.")
        self.all_users = [user['username'] for user in users]
        # If user was typing while we were fetching, re-run the search
        if self.search_input.text().strip():
            self.search_username()

    def on_friend_added_response(self, response):
        if response.get("status") == "success":
            print(f"✅ Friend request sent to {self.search_result_username}")
            # --- NEW: Emit the signal on success ---
            self.friend_successfully_added.emit()
            self.accept() # Close the modal
        else:
            self.show_status_message(response.get("message", "Failed to add friend"), is_error=True)
            
    def on_backend_error(self, message):
        self.show_status_message(f"Error: {message}", is_error=True)

    def on_search_text_changed(self, text):
        """Handle search input text changes with debouncing."""
        if not text.strip():
            self.clear_result()
        else:
            if hasattr(self, 'search_timer'):
                self.search_timer.stop()
            self.search_timer = QTimer()
            self.search_timer.setSingleShot(True)
            self.search_timer.timeout.connect(self.search_username)
            self.search_timer.start(500) # 500ms delay

    def search_username(self):
        """Search for username from the cached list."""
        username_to_find = self.search_input.text().strip().lower()
        if not username_to_find:
            self.clear_result()
            return

        # Search in the pre-fetched user list
        found_user = next((u for u in self.all_users if u.lower() == username_to_find), None)

        if found_user:
            self.show_username_found(found_user)
        else:
            self.show_username_not_found()

    def add_friend(self):
        """Send friend request via the backend."""
        if self.is_username_found and self.search_result_username:
            self.backend.add_friend(self.search_result_username)
            self.add_btn.setEnabled(False)
            self.add_btn.setText("Sending...")

    # --- UI and State methods (mostly copied from original, with small updates) ---
    def setup_ui(self):
        """Setup the modal UI using layouts for proper sizing."""
        # --- FIX: Use a main layout instead of fixed geometry ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        # Main container
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border: 2px solid #B0C4C6;
                border-radius: 15px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Add container to the main layout
        main_layout.addWidget(container)

        # Header with close button
        self.setup_header(layout)
        
        # Search section
        self.setup_search_section(layout)
        
        # Result section
        self.setup_result_section(layout)
        
        # Buttons section
        self.setup_buttons_section(layout)

        # --- FIX: Let the layout determine the optimal size ---
        self.adjustSize()
        # self.setFixedSize(self.size()) # Lock the size after calculating it
    
    def setup_header(self, parent_layout):
        header_layout = QHBoxLayout()
        title = QLabel("Search Username")
        title.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; color: #2C2C2C; background-color: transparent; border: none; }")
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; font-size: 20px; font-weight: bold; color: #7F8C8D; max-width: 30px; max-height: 30px; } QPushButton:hover { color: #C0392B; }")
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        parent_layout.addLayout(header_layout)

    def setup_search_section(self, parent_layout):
        search_layout = QHBoxLayout()
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("QLabel { color: #2C2C2C; font-size: 18px; padding: 10px; }")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter username...")
        self.search_input.setStyleSheet("QLineEdit { background-color: white; border: 1px solid #B0C4C6; border-radius: 8px; padding: 12px 15px; font-size: 16px; color: #2C2C2C; } QLineEdit:focus { border: 2px solid #7A9499; }")
        self.search_input.setFixedHeight(45)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.search_username)
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        parent_layout.addLayout(search_layout)

    def setup_result_section(self, parent_layout):
        """Setup result display section."""
        self.result_container = QFrame()
        # --- FIX: Removed the fixed height to prevent text from being cut ---
        # self.result_container.setFixedHeight(60) 
        self.result_container.setStyleSheet("QFrame { background-color: transparent; border: none; }")
        
        result_layout = QVBoxLayout(self.result_container)
        result_layout.setContentsMargins(0, 10, 0, 10)
        result_layout.setAlignment(Qt.AlignCenter)
        
        self.username_display = QLabel()
        self.username_display.setAlignment(Qt.AlignCenter)
        self.username_display.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #2C2C2C; background-color: transparent; border: none; padding: 5px; }")
        self.username_display.hide()
        
        self.status_message = QLabel()
        self.status_message.setAlignment(Qt.AlignCenter)
        self.status_message.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; background-color: transparent; border: none; padding: 5px; }")
        self.status_message.hide()
        
        result_layout.addWidget(self.username_display)
        result_layout.addWidget(self.status_message)
        
        parent_layout.addWidget(self.result_container)

    def setup_buttons_section(self, parent_layout):
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        self.add_btn = QPushButton("Add")
        self.add_btn.setStyleSheet("QPushButton { background-color: #7A9499; color: white; border: none; border-radius: 8px; padding: 12px 25px; font-size: 16px; font-weight: bold; min-width: 80px; } QPushButton:hover { background-color: #6B8387; } QPushButton:pressed { background-color: #5A7175; }")
        self.add_btn.setFixedHeight(45)
        self.add_btn.clicked.connect(self.add_friend)
        self.add_btn.hide()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("QPushButton { background-color: #BDC3C7; color: #2C2C2C; border: none; border-radius: 8px; padding: 12px 25px; font-size: 16px; font-weight: bold; min-width: 80px; } QPushButton:hover { background-color: #A8B2B6; } QPushButton:pressed { background-color: #95A5AA; }")
        self.cancel_btn.setFixedHeight(45)
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.cancel_btn)
        parent_layout.addLayout(buttons_layout)
        
    def center_on_parent(self):
        if self.parent():
            parent_rect = self.parent().geometry()
            self.move(parent_rect.x() + (parent_rect.width() - self.width()) // 2,
                      parent_rect.y() + (parent_rect.height() - self.height()) // 2)

    def show_username_found(self, username):
        self.search_result_username = username
        self.is_username_found = True
        self.username_display.setText(username)
        self.username_display.show()
        self.show_status_message("Username Found!", is_error=False)
        self.add_btn.show()
        self.add_btn.setEnabled(True)
        self.add_btn.setText("Add")

    def show_username_not_found(self):
        self.clear_result()
        self.show_status_message("Username not Found!", is_error=True)

    def clear_result(self):
        self.search_result_username = None
        self.is_username_found = False
        self.username_display.hide()
        self.status_message.hide()
        self.add_btn.hide()

    def show_status_message(self, text, is_error):
        color = "#E74C3C" if is_error else "#27AE60"
        self.status_message.setText(text)
        self.status_message.setStyleSheet(f"QLabel {{ font-size: 16px; font-weight: bold; color: {color}; background-color: transparent; border: none; padding: 5px; }}")
        self.status_message.show()

    def reset_modal(self):
        self.search_input.clear()
        self.clear_result()
        self.search_input.setFocus()
        self.backend.get_users() # Refresh user list