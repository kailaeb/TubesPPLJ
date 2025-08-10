# main_http.py
# This is the main entry point for the HTTPS client application.

# main_http.py

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QStackedWidget, QHBoxLayout, QPushButton, QFrame, QButtonGroup)
from http_login_page import LoginPage
from http_register_page import RegisterPage
from http_client import HttpClient
from home_page import HomePage
from friend_list_page import FriendListPage
from chat_page import ChatPage

class MessengerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.http_backend = HttpClient()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Messenger")
        self.resize(1200, 800)

        self.top_level_stack = QStackedWidget()
        self.setCentralWidget(self.top_level_stack)

        # --- Create all pages ---
        self.login_page = LoginPage(self.http_backend)
        self.register_page = RegisterPage(self.http_backend)
        
        # --- Create the main app container ---
        self.app_container = QWidget()
        app_layout = QHBoxLayout(self.app_container)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)
        
        # --- Create the single, persistent sidebar ---
        self.sidebar = self.create_sidebar()
        app_layout.addWidget(self.sidebar)

        # --- Create the content stack ---
        self.main_content_stack = QStackedWidget()
        app_layout.addWidget(self.main_content_stack)
        
        # Create and add content-only pages to the stack
        self.home_page = HomePage(self.http_backend)
        self.friend_list_page = FriendListPage(self.http_backend)
        self.main_content_stack.addWidget(self.home_page)
        self.main_content_stack.addWidget(self.friend_list_page)

        # Add login/register and the main app container to the top-level stack
        self.top_level_stack.addWidget(self.login_page)
        self.top_level_stack.addWidget(self.register_page)
        self.top_level_stack.addWidget(self.app_container)

        # Connect signals
        self.login_page.login_successful.connect(self.handle_login_success)
        self.http_backend.friend_list_fetched.connect(self.friend_list_page.on_friend_list_received)
        self.friend_list_page.friend_selected.connect(self.show_chat_page)
        
        self.show_login()

    def create_sidebar(self):
        """Creates the main navigation sidebar widget."""
        sidebar = QFrame()
        sidebar.setFixedWidth(216)
        sidebar.setStyleSheet("QFrame { background-color: #E8E1E1; border-right: 2px solid #B0C4C6; }")
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Home button
        home_btn = QPushButton("Home")
        home_btn.setCheckable(True)
        home_btn.setChecked(True)
        home_btn.clicked.connect(self.show_home_page)
        
        # Friend List button
        friend_list_btn = QPushButton("Friend List")
        friend_list_btn.setCheckable(True)
        friend_list_btn.clicked.connect(self.show_friend_list_page)

        # Button Group for exclusive selection
        self.nav_button_group = QButtonGroup(self)
        self.nav_button_group.addButton(home_btn)
        self.nav_button_group.addButton(friend_list_btn)
        self.nav_button_group.setExclusive(True)

        for button in self.nav_button_group.buttons():
            button.setFixedHeight(66)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #E8E1E1; color: #2C2C2C; border: none; padding: 20px;
                    font-size: 18px; text-align: left; border-bottom: 1px solid #B0C4C6;
                }
                QPushButton:hover { background-color: #D5CECE; }
                QPushButton:checked { background-color: #9DB4B8; border-right: 4px solid #5A7175; }
            """)
        
        sidebar_layout.addWidget(home_btn)
        sidebar_layout.addWidget(friend_list_btn)
        sidebar_layout.addStretch()
        
        return sidebar

    def handle_login_success(self, response):
        """Handles post-login setup."""
        self.current_user = response.get("user", {})
        self.current_user['token'] = response.get('token')
        self.setWindowTitle(f"Messenger - {self.current_user.get('username')}")
        self.http_backend.get_friends()
        self.top_level_stack.setCurrentWidget(self.app_container)
        self.show_home_page()

    def show_home_page(self):
        self.main_content_stack.setCurrentWidget(self.home_page)

    def show_friend_list_page(self):
        self.main_content_stack.setCurrentWidget(self.friend_list_page)

    def show_chat_page(self, friend_info):
        """Creates and displays the chat page for the selected friend."""
        chat_page = ChatPage(self.current_user, friend_info, self.http_backend)
        self.main_content_stack.addWidget(chat_page)
        self.main_content_stack.setCurrentWidget(chat_page)
        
    def show_login(self):
        self.top_level_stack.setCurrentWidget(self.login_page)

    # ... (other methods like `main` can remain the same) ...

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MessengerApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()