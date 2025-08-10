import json
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot
from PyQt5.QtGui import QFontMetrics
from auth_page import AuthPage
from register_backend import RegisterBackend

class RegisterPage(AuthPage):
    """Frontend UI for registration page - handles only UI logic and user interactions"""
    
    switch_to_login = pyqtSignal()
    register_attempted = pyqtSignal(str)  # Signal for logging purposes
    register_successful = pyqtSignal(dict)  # Signal when registration succeeds
    
    def __init__(self):
        super().__init__()
        self.error_popup = None
        
        # Setup UI FIRST before connecting to backend
        self.setup_form()
        
        # Initialize backend service AFTER UI is ready
        self.backend = RegisterBackend()
        self.setup_backend_connections()
        
        # Auto-connect to server when page initializes
        self.backend.connect_to_server()
    
    def setup_backend_connections(self):
        """Connect backend signals to frontend handlers"""
        self.backend.connection_established.connect(self.on_backend_connected)
        self.backend.connection_failed.connect(self.on_backend_connection_failed)
        self.backend.register_response.connect(self.on_register_response)
        self.backend.error_occurred.connect(self.on_backend_error)
    
    def setup_form(self):
        """Setup the UI form - pure frontend logic"""
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(40, 40, 40, 50)
        form_layout.setSpacing(0)  # We'll control spacing manually
        
        # Add some top spacing
        form_layout.addSpacing(20)
        
        # Title
        title = QLabel("Register")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 36px;
                font-weight: bold;
                color: #2C2C2C;
                background-color: transparent;
                border: none;
                padding: 15px 0px;
                margin: 0px;
            }
        """)
        title.setFixedHeight(70)
        form_layout.addWidget(title)
        
        # Add spacing after title
        form_layout.addSpacing(10)
        
        # Username section
        username_label = QLabel("Username")
        username_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2C2C2C;
                margin-bottom: 0px;
            }
        """)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username ...")
        self.username_input.setStyleSheet("""
            QLineEdit {
                background-color: #E8E1E1;
                border: 1px solid #B0C4C6;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                color: #2C2C2C;
                margin-top: 5px;
            }
            QLineEdit:focus {
                border: 2px solid #7A9499;
            }
            QLineEdit:disabled {
                background-color: #F0F0F0;
                color: #888888;
            }
        """)
        self.username_input.setFixedHeight(45)
        
        form_layout.addWidget(username_label)
        form_layout.addSpacing(5)  # Small gap between label and input
        form_layout.addWidget(self.username_input)
        form_layout.addSpacing(15)  # Medium gap between sections
        
        # Password section
        password_label = QLabel("Password")
        password_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2C2C2C;
                margin-bottom: 0px;
            }
        """)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password ...")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #E8E1E1;
                border: 1px solid #B0C4C6;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                color: #2C2C2C;
                margin-top: 5px;
            }
            QLineEdit:focus {
                border: 2px solid #7A9499;
            }
            QLineEdit:disabled {
                background-color: #F0F0F0;
                color: #888888;
            }
        """)
        self.password_input.setFixedHeight(45)
        
        form_layout.addWidget(password_label)
        form_layout.addSpacing(5)  # Small gap between label and input
        form_layout.addWidget(self.password_input)
        
        # Register button
        form_layout.addSpacing(20)  # Space before register button
        self.register_btn = QPushButton("Register Account")
        self.register_btn.setStyleSheet("""
            QPushButton {
                background-color: #9DB4B8;
                color: #2C2C2C;
                border: none;
                border-radius: 20px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8AA5A9;
            }
            QPushButton:pressed {
                background-color: #7A9499;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
                color: #7F8C8D;
            }
        """)
        self.register_btn.setFixedHeight(45)
        self.register_btn.clicked.connect(self.handle_register)
        
        form_layout.addWidget(self.register_btn)
        
        # Already have account text
        have_account_label = QLabel("Already have an account?")
        have_account_label.setAlignment(Qt.AlignCenter)
        have_account_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2C2C2C;
                font-style: italic;
                padding-top: 7px;
                margin-bottom: 5px;
            }
        """)
        
        # Login button
        login_btn = QPushButton("Login")
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #9DB4B8;
                color: #2C2C2C;
                border: none;
                border-radius: 20px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8AA5A9;
            }
            QPushButton:pressed {
                background-color: #7A9499;
            }
        """)
        login_btn.setFixedHeight(45)
        login_btn.clicked.connect(self.switch_to_login.emit)
        
        form_layout.addWidget(have_account_label)
        form_layout.addWidget(login_btn)
        
        # Connect Enter key to register
        self.username_input.returnPressed.connect(self.handle_register)
        self.password_input.returnPressed.connect(self.handle_register)
    
    def handle_register(self):
        """Handle register button click - frontend validation + backend request"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        # Basic frontend validation (same as original)
        if not username:
            self.show_error_message("Please enter a username")
            return
        
        if not password:
            self.show_error_message("Please enter a password")
            return
        
        if len(password) < 8:
            self.show_error_message("Password must be at least 8 characters")
            return
        
        # Show loading state
        self.show_loading_state()
        
        # Emit signal for logging purposes (same as original)
        register_data = {
            "action": "register",
            "username": username,
            "timestamp": QTimer().interval()
        }
        self.register_attempted.emit(json.dumps(register_data, indent=2))
        
        # Send request via backend
        self.backend.send_register_request(username, password)
    
    @pyqtSlot()
    def on_backend_connected(self):
        """Handle successful backend connection"""
        print("🔗 Frontend: Backend connected to server")
        self.enable_register_form()
    
    @pyqtSlot(str)
    def on_backend_connection_failed(self, reason):
        """Handle backend connection failure"""
        print(f"❌ Frontend: Backend connection failed - {reason}")
        self.disable_register_form()
        self.hide_loading_state()
        self.show_error_message(f"Cannot connect to server: {reason}")
    
    @pyqtSlot(dict)
    def on_register_response(self, response):
        """Handle registration response from backend"""
        self.hide_loading_state()
        
        status = response.get("status", "unknown")
        message = response.get("message", "Unknown response")
        
        if status == "success":
            print(f"✅ Frontend: Registration successful - {message}")
            self.show_success_message(message)
            # Emit success signal for main app to handle redirect
            self.register_successful.emit(response)
            # Clear form
            self.username_input.clear()
            self.password_input.clear()
        elif status == "error":
            print(f"❌ Frontend: Registration failed - {message}")
            self.show_error_message(message)
        else:
            print(f"⚠️ Frontend: Unknown response status - {status}")
            self.show_error_message("Invalid response from server")
    
    @pyqtSlot(str)
    def on_backend_error(self, error_message):
        """Handle backend errors"""
        print(f"❌ Frontend: Backend error - {error_message}")
        self.hide_loading_state()
        self.show_error_message(error_message)
    
    def show_loading_state(self):
        """Show loading state during registration request"""
        self.register_btn.setEnabled(False)
        self.register_btn.setText("Creating Account...")
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)
    
    def hide_loading_state(self):
        """Hide loading state and restore normal UI"""
        self.register_btn.setEnabled(True)
        self.register_btn.setText("Register Account")
        self.username_input.setEnabled(True)
        self.password_input.setEnabled(True)
    
    def enable_register_form(self):
        """Enable register form when backend is connected"""
        if not hasattr(self, 'register_btn'):
            return
        
        self.register_btn.setEnabled(True)
        self.register_btn.setText("Register Account")
        self.username_input.setEnabled(True)
        self.password_input.setEnabled(True)
    
    def disable_register_form(self):
        """Disable register form when backend is not connected"""
        if not hasattr(self, 'register_btn'):
            return
            
        self.register_btn.setEnabled(False)
        self.register_btn.setText("Connecting...")
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)
    
    # Use same error popup from your original code
    def show_error_message(self, message):
        """Display error popup message (same as original)"""
        self.hide_error_message()  # Hide any existing error message
        
        # Create error popup
        self.error_popup = QFrame(self)
        self.error_popup.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border: 2px solid #E74C3C;
                border-radius: 10px;
                margin: 0px 0px;
                padding: 0px;
            }
        """)
        
        # Error popup layout
        popup_layout = QVBoxLayout(self.error_popup)
        popup_layout.setContentsMargins(15, 10, 40, 10)
        popup_layout.setSpacing(0)
        
        # Error message with icon
        error_label = QLabel(f"⚠ {message}")
        error_label.setStyleSheet("""
            QLabel {
                color: #C0392B;
                font-size: 14px;
                font-weight: bold;
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
                font-size: 16px;
                font-weight: bold;
                color: #7F8C8D;
                max-width: 20px;
                max-height: 20px;
            }
            QPushButton:hover {
                color: #C0392B;
            }
        """)
        close_btn.clicked.connect(self.hide_error_message)
        
        popup_layout.addWidget(error_label)
        
        # Position the popup (same as original)
        self.error_popup.setFixedSize(350, 45)
        
        # Get the main window geometry
        main_window = self.window()
        
        # Get form container position relative to main window
        form_global_pos = self.form_container.mapToGlobal(self.form_container.rect().topLeft())
        form_local_pos = main_window.mapFromGlobal(form_global_pos)
        
        # Calculate popup position
        popup_x = form_local_pos.x() + (self.form_container.width() - 350) // 2
        popup_y = form_local_pos.y() - 55
        
        # Ensure the popup stays within window bounds
        header_height = 80  # Approximate header height
        if popup_y < header_height + 10:
            popup_y = form_local_pos.y() + 13  # Position inside the form container
        
        self.error_popup.move(popup_x, popup_y)
        
        # Position close button
        close_btn.setParent(self.error_popup)
        close_btn.move(315, 12)
        
        # Show the popup
        self.error_popup.show()
        
        # Auto-hide after 5 seconds
        QTimer.singleShot(5000, self.hide_error_message)
    
    def show_success_message(self, message):
        """Display success message (same as original)"""
        print(f"✅ {message}")
        # You can implement a success popup similar to error popup if needed
    
    def hide_error_message(self):
        """Hide the error popup (same as original)"""
        if self.error_popup:
            self.error_popup.hide()
            self.error_popup.deleteLater()
            self.error_popup = None
    
    def cleanup(self):
        """Cleanup resources when page is destroyed"""
        if hasattr(self, 'backend'):
            print("🧹 Frontend: Cleaning up backend connection")
            self.backend.disconnect_from_server()