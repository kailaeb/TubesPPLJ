import json
import hashlib
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from auth_page import AuthPage


class LoginPage(AuthPage):
    switch_to_register = pyqtSignal()
    login_attempted = pyqtSignal(str)  # Signal to emit JSON data
    
    def __init__(self):
        super().__init__()
        self.error_popup = None
        self.setup_form()
    
    def setup_form(self):
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(40, 40, 40, 50)
        form_layout.setSpacing(0)  # We'll control spacing manually
        
        # Add some top spacing
        form_layout.addSpacing(20)
        
        # Title
        title = QLabel("Login")
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
        """)
        self.password_input.setFixedHeight(45)
        
        form_layout.addWidget(password_label)
        form_layout.addSpacing(5)  # Small gap between label and input
        form_layout.addWidget(self.password_input)
        
        # Login button
        form_layout.addSpacing(20)  # Space before login button
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
        login_btn.clicked.connect(self.handle_login)
        
        form_layout.addWidget(login_btn)
        
        # Don't have account text
        no_account_label = QLabel("Don't have an account?")
        no_account_label.setAlignment(Qt.AlignCenter)
        no_account_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2C2C2C;
                font-style: italic;
                padding-top: 7px;
                margin-bottom: 5px;
            }
        """)
        
        # Register button
        register_btn = QPushButton("Register")
        register_btn.setStyleSheet("""
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
        register_btn.setFixedHeight(45)
        register_btn.clicked.connect(self.switch_to_register.emit)
        
        form_layout.addWidget(no_account_label)
        form_layout.addWidget(register_btn)
        
        # Connect Enter key to login
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
    
    def hash_password(self, password):
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if username and password:
            # Hash the password before sending to server
            hashed_password = self.hash_password(password)
            
            login_data = {
                "action": "login",
                "username": username,
                "password": hashed_password  # Send hashed password
            }
            json_data = json.dumps(login_data, indent=2)
            self.login_attempted.emit(json_data)
            # print("Login JSON Data (with hashed password):")
            # print(json_data)
            # print(f"Original password: {password}")
            # print(f"SHA256 hash: {hashed_password}")
            
            # Simulate server response (you'll replace this with actual server communication)
            self.simulate_server_response(username)
    
    def simulate_server_response(self, username):
        """Simulate different server responses - replace this with actual server communication"""
        # Simulate some usernames that don't exist
        non_existent_users = ["test123", "baduser", "notfound", "fake"]
        
        if username.lower() in non_existent_users:
            # Simulate server error response
            error_response = {
                "status": "error",
                "message": "Username not Found!",
                "code": 404
            }
            self.handle_server_response(error_response)
        else:
            # Simulate successful response
            success_response = {
                "status": "success", 
                "message": "Login successful",
                "token": "abc123xyz"
            }
            self.handle_server_response(success_response)
    
    def handle_server_response(self, response):
        """Handle server response and show appropriate messages"""
        if response["status"] == "error":
            self.show_error_message(response["message"])
        elif response["status"] == "success":
            self.show_success_message(response["message"])
            # Here you would typically navigate to the main app
    
    def show_error_message(self, message):
        """Display error popup message"""
        self.hide_error_message()  # Hide any existing error message
        
        # Create error popup
        self.error_popup = QFrame(self)
        self.error_popup.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border: 2px solid #E74C3C;
                border-radius: 10px;
                padding: 0px 0px;
                margin: 0px;
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
                background-color: transparent;
                border: none;
                color: #C0392B;
                font-size: 14px;
                font-weight: bold;
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
        
        # Add widgets to popup
        popup_layout.addWidget(error_label)
        
        # Position the popup relative to the main window, not just the form
        self.error_popup.setFixedSize(350, 45)
        
        # Get the main window geometry
        main_window = self.window()
        window_rect = main_window.geometry()
        
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
        """Display success message (optional)"""
        print(f"✅ {message}")
        # You can implement a success popup similar to error popup if needed
    
    def hide_error_message(self):
        """Hide the error popup"""
        if self.error_popup:
            self.error_popup.hide()
            self.error_popup.deleteLater()
            self.error_popup = None