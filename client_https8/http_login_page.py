# http_login_page.py
# This file is a modified version of your login_page.py to use the HttpClient.

import json
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot
from auth_page import AuthPage # No changes needed to auth_page.py
import hashlib # <--- Add this import

class LoginPage(AuthPage):
    """
    Frontend UI for login page. Connects to HttpClient for network operations.
    """
    switch_to_register = pyqtSignal()
    login_successful = pyqtSignal(dict)

    def __init__(self, backend): # Accepts the shared backend instance
        super().__init__()
        self.error_popup = None
        self.backend = backend
        self.setup_backend_connections()
        self.setup_form()
        self.disable_login_form() # Disabled until we confirm connection

    def setup_backend_connections(self):
        """Connect backend signals to frontend handlers."""
        self.backend.login_response.connect(self.on_login_response)
        self.backend.error_occurred.connect(self.on_backend_error)
        # You can add a connection test if desired, but for HTTP it's less critical
        # than for WSS. We'll just enable the form.
        QTimer.singleShot(100, self.enable_login_form)

    def on_login_response(self, response):
        """Handle login response from backend."""
        self.hide_loading_state()
        status = response.get("status", "unknown")
        message = response.get("message", "Unknown response")

        if status == "success":
            print(f"✅ Frontend: Login successful - {message}")
            self.login_successful.emit(response)
        else:
            print(f"❌ Frontend: Login failed - {message}")
            self.show_error_message(message)

    def on_backend_error(self, error_message):
        """Handle backend errors."""
        print(f"❌ Frontend: Backend error - {error_message}")
        self.hide_loading_state()
        self.show_error_message(error_message)

    '''
    def handle_login(self):
        """Handle login button click - frontend validation + backend request."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.show_error_message("Username and password are required")
            return

        self.show_loading_state()
        self.backend.login(username, password)
    '''
    def hash_password(self, password):
        """Hash password using SHA256."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def handle_login(self):
        """Handle login button click - HASH password before sending."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.show_error_message("Username and password are required")
            return

        # --- HASH THE PASSWORD HERE ---
        hashed_password = self.hash_password(password)

        self.show_loading_state()
        
        # Send the HASHED password to the backend
        self.backend.login(username, hashed_password)
    
    # --- UI Setup and State Management (Copied from your original file, no changes needed) ---
    def setup_form(self):
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(40, 40, 40, 50)
        form_layout.setSpacing(0)
        form_layout.addSpacing(20)
        title = QLabel("Login")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("QLabel { font-size: 36px; font-weight: bold; color: #2C2C2C; background-color: transparent; border: none; padding: 15px 0px; margin: 0px; }")
        title.setFixedHeight(70)
        form_layout.addWidget(title)
        form_layout.addSpacing(10)
        username_label = QLabel("Username")
        username_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #2C2C2C; margin-bottom: 0px; }")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username ...")
        self.username_input.setStyleSheet("QLineEdit { background-color: #E8E1E1; border: 1px solid #B0C4C6; border-radius: 8px; padding: 12px; font-size: 14px; color: #2C2C2C; margin-top: 5px; } QLineEdit:focus { border: 2px solid #7A9499; } QLineEdit:disabled { background-color: #F0F0F0; color: #888888; }")
        self.username_input.setFixedHeight(45)
        form_layout.addWidget(username_label)
        form_layout.addSpacing(5)
        form_layout.addWidget(self.username_input)
        form_layout.addSpacing(15)
        password_label = QLabel("Password")
        password_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #2C2C2C; margin-bottom: 0px; }")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password ...")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("QLineEdit { background-color: #E8E1E1; border: 1px solid #B0C4C6; border-radius: 8px; padding: 12px; font-size: 14px; color: #2C2C2C; margin-top: 5px; } QLineEdit:focus { border: 2px solid #7A9499; } QLineEdit:disabled { background-color: #F0F0F0; color: #888888; }")
        self.password_input.setFixedHeight(45)
        form_layout.addWidget(password_label)
        form_layout.addSpacing(5)
        form_layout.addWidget(self.password_input)
        form_layout.addSpacing(20)
        self.login_btn = QPushButton("Login")
        self.login_btn.setStyleSheet("QPushButton { background-color: #9DB4B8; color: #2C2C2C; border: none; border-radius: 20px; padding: 12px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #8AA5A9; } QPushButton:pressed { background-color: #7A9499; } QPushButton:disabled { background-color: #BDC3C7; color: #7F8C8D; }")
        self.login_btn.setFixedHeight(45)
        self.login_btn.clicked.connect(self.handle_login)
        form_layout.addWidget(self.login_btn)
        no_account_label = QLabel("Don't have an account?")
        no_account_label.setAlignment(Qt.AlignCenter)
        no_account_label.setStyleSheet("QLabel { font-size: 14px; color: #2C2C2C; font-style: italic; padding-top: 7px; margin-bottom: 5px; }")
        register_btn = QPushButton("Register")
        register_btn.setStyleSheet("QPushButton { background-color: #9DB4B8; color: #2C2C2C; border: none; border-radius: 20px; padding: 12px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #8AA5A9; } QPushButton:pressed { background-color: #7A9499; }")
        register_btn.setFixedHeight(45)
        register_btn.clicked.connect(self.switch_to_register.emit)
        form_layout.addWidget(no_account_label)
        form_layout.addWidget(register_btn)
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)

    def show_loading_state(self):
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Logging in...")
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)

    def hide_loading_state(self):
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Login")
        self.username_input.setEnabled(True)
        self.password_input.setEnabled(True)

    def enable_login_form(self):
        self.hide_loading_state()

    def disable_login_form(self):
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Connecting...")
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)

    def show_error_message(self, message):
        self.hide_error_message()
        self.error_popup = QFrame(self)
        self.error_popup.setStyleSheet("QFrame { background-color: #F5F5F5; border: 2px solid #E74C3C; border-radius: 10px; }")
        popup_layout = QVBoxLayout(self.error_popup)
        error_label = QLabel(f"⚠ {message}")
        error_label.setStyleSheet("QLabel { color: #C0392B; font-size: 14px; font-weight: bold; background-color: transparent; border: none; }")
        popup_layout.addWidget(error_label, alignment=Qt.AlignCenter)
        main_window = self.window()
        form_global_pos = self.form_container.mapToGlobal(self.form_container.rect().topLeft())
        form_local_pos = main_window.mapFromGlobal(form_global_pos)
        popup_x = form_local_pos.x() + (self.form_container.width() - 280) // 2
        popup_y = form_local_pos.y() - 55
        self.error_popup.setGeometry(popup_x, popup_y, 280, 45)
        self.error_popup.show()
        QTimer.singleShot(5000, self.hide_error_message)

    def hide_error_message(self):
        if self.error_popup:
            self.error_popup.hide()
            self.error_popup.deleteLater()
            self.error_popup = None