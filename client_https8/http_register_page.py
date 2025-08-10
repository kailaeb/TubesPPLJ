# http_register_page.py
# This file is a modified version of your register_page.py

import json
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot
from auth_page import AuthPage
import hashlib # <--- Add this import

class RegisterPage(AuthPage):
    switch_to_login = pyqtSignal()
    registration_successful = pyqtSignal() # Emit on success

    def __init__(self, backend): # Accepts the shared backend instance
        super().__init__()
        self.backend = backend
        self.error_popup = None
        self.setup_form()
        self.setup_backend_connections()

    def setup_backend_connections(self):
        self.backend.register_response.connect(self.handle_server_response)
        self.backend.error_occurred.connect(self.on_backend_error)
        
    '''
    def handle_register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.show_error_message("Username and password cannot be empty.")
            return
            
        if len(password) < 4: # Matches server logic (or should)
            self.show_error_message("Password must be at least 4 characters.")
            return

        # The backend now handles the request
        self.backend.register(username, password)
    '''
        
    def hash_password(self, password):
        """Hash password using SHA256."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def handle_register(self):
        """Handle register button click - HASH password before sending."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.show_error_message("Username and password cannot be empty.")
            return
            
        if len(password) < 4:
            self.show_error_message("Password must be at least 4 characters.")
            return

        # --- HASH THE PASSWORD HERE ---
        hashed_password = self.hash_password(password)
        
        # Send the HASHED password to the backend
        self.backend.register(username, hashed_password)
        
    @pyqtSlot(dict)
    def handle_server_response(self, response):
        """Handle server response and show appropriate messages"""
        if response.get("status") == "error":
            self.show_error_message(response.get("message", "An unknown error occurred."))
        elif response.get("status") == "success":
            self.show_success_message(response.get("message", "Success!"))
            self.registration_successful.emit()
            # Optional: automatically switch to login after a delay
            QTimer.singleShot(1500, self.switch_to_login.emit)

    @pyqtSlot(str)
    def on_backend_error(self, error_message):
        self.show_error_message(error_message)

    def show_success_message(self, message):
        # This can be a simple popup or just a print statement
        print(f"✅ Success: {message}")
        self.hide_error_message() # Hide any previous errors
        # You could implement a green success popup similar to the red error one
        
    # --- UI Setup and Error Popup (Copied from your original file, no changes needed) ---
    def setup_form(self):
        # This code is identical to your original UI setup
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(40, 40, 40, 50)
        form_layout.setSpacing(0)
        form_layout.addSpacing(20)
        title = QLabel("Register Page")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("QLabel { font-size: 36px; font-weight: bold; color: #2C2C2C; background-color: transparent; border: none; padding: 15px 0px; margin: 0px; }")
        title.setFixedHeight(70)
        form_layout.addWidget(title)
        form_layout.addSpacing(10)
        username_label = QLabel("Username")
        username_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #2C2C2C; margin-bottom: 0px; }")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username ...")
        self.username_input.setStyleSheet("QLineEdit { background-color: #E8E1E1; border: 1px solid #B0C4C6; border-radius: 8px; padding: 12px; font-size: 14px; color: #2C2C2C; margin-top: 5px; } QLineEdit:focus { border: 2px solid #7A9499; }")
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
        self.password_input.setStyleSheet("QLineEdit { background-color: #E8E1E1; border: 1px solid #B0C4C6; border-radius: 8px; padding: 12px; font-size: 14px; color: #2C2C2C; margin-top: 5px; } QLineEdit:focus { border: 2px solid #7A9499; }")
        self.password_input.setFixedHeight(45)
        form_layout.addWidget(password_label)
        form_layout.addSpacing(5)
        form_layout.addWidget(self.password_input)
        form_layout.addSpacing(20)
        register_btn = QPushButton("Register Account")
        register_btn.setStyleSheet("QPushButton { background-color: #9DB4B8; color: #2C2C2C; border: none; border-radius: 20px; padding: 12px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #8AA5A9; } QPushButton:pressed { background-color: #7A9499; }")
        register_btn.setFixedHeight(45)
        register_btn.clicked.connect(self.handle_register)
        form_layout.addWidget(register_btn)
        have_account_label = QLabel("Already have an account?")
        have_account_label.setAlignment(Qt.AlignCenter)
        have_account_label.setStyleSheet("QLabel { font-size: 14px; color: #2C2C2C; font-style: italic; padding-top: 7px; margin-bottom: 5px; }")
        login_btn = QPushButton("Login")
        login_btn.setStyleSheet("QPushButton { background-color: #9DB4B8; color: #2C2C2C; border: none; border-radius: 20px; padding: 12px; font-size: 16px; font-weight: bold; } QPushButton:hover { background-color: #8AA5A9; } QPushButton:pressed { background-color: #7A9499; }")
        login_btn.setFixedHeight(45)
        login_btn.clicked.connect(self.switch_to_login.emit)
        form_layout.addWidget(have_account_label)
        form_layout.addWidget(login_btn)
        self.username_input.returnPressed.connect(self.handle_register)
        self.password_input.returnPressed.connect(self.handle_register)

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
        popup_x = form_local_pos.x() + (self.form_container.width() - 350) // 2
        popup_y = form_local_pos.y() - 55
        self.error_popup.setGeometry(popup_x, popup_y, 350, 45)
        self.error_popup.show()
        QTimer.singleShot(5000, self.hide_error_message)

    def hide_error_message(self):
        if self.error_popup:
            self.error_popup.hide()
            self.error_popup.deleteLater()
            self.error_popup = None