from PyQt5.QtWidgets import QFrame, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal


class NavigationSidebar(QFrame):
    """Reusable navigation sidebar for switching between Home and Friend List"""
    
    # Signals for navigation
    home_clicked = pyqtSignal()
    friend_list_clicked = pyqtSignal()
    
    def __init__(self, active_page="home"):
        super().__init__()
        self.active_page = active_page  # "home" or "friend_list"
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the sidebar UI"""
        self.setFixedWidth(216)
        self.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border-right: 2px solid #B0C4C6;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Home button
        self.home_btn = QPushButton("Home")
        self.home_btn.setFixedHeight(66)
        self.home_btn.clicked.connect(self.on_home_clicked)
        
        # Friend List button
        self.friend_list_btn = QPushButton("Friend List")
        self.friend_list_btn.setFixedHeight(66)
        self.friend_list_btn.clicked.connect(self.on_friend_list_clicked)
        
        # Add buttons to layout
        layout.addWidget(self.home_btn)
        layout.addWidget(self.friend_list_btn)
        layout.addStretch()
        
        # Set initial active state
        self.set_active_page(self.active_page)
    
    def set_active_page(self, page):
        """Set which page is currently active"""
        self.active_page = page
        
        if page == "home":
            # Home is active
            self.home_btn.setStyleSheet("""
                QPushButton {
                    background-color: #9DB4B8;
                    color: #2C2C2C;
                    border: none;
                    padding: 20px;
                    font-size: 18px;
                    font-weight: normal;
                    text-align: left;
                    border-bottom: 1px solid #7A9499;
                }
            """)
            
            # Friend List is inactive
            self.friend_list_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E8E1E1;
                    color: #2C2C2C;
                    border: none;
                    padding: 20px;
                    font-size: 18px;
                    font-weight: normal;
                    text-align: left;
                    border-bottom: 1px solid #B0C4C6;
                }
                QPushButton:hover {
                    background-color: #D5CECE;
                }
            """)
            
        elif page == "friend_list":
            # Friend List is active
            self.friend_list_btn.setStyleSheet("""
                QPushButton {
                    background-color: #9DB4B8;
                    color: #2C2C2C;
                    border: none;
                    padding: 20px;
                    font-size: 18px;
                    font-weight: normal;
                    text-align: left;
                    border-bottom: 1px solid #7A9499;
                }
            """)
            
            # Home is inactive
            self.home_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E8E1E1;
                    color: #2C2C2C;
                    border: none;
                    padding: 20px;
                    font-size: 18px;
                    font-weight: normal;
                    text-align: left;
                    border-bottom: 1px solid #B0C4C6;
                }
                QPushButton:hover {
                    background-color: #D5CECE;
                }
            """)
    
    def on_home_clicked(self):
        """Handle home button click"""
        if self.active_page != "home":
            self.set_active_page("home")
            self.home_clicked.emit()
    
    def on_friend_list_clicked(self):
        """Handle friend list button click"""
        if self.active_page != "friend_list":
            self.set_active_page("friend_list")
            self.friend_list_clicked.emit()