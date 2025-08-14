from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt


class AuthPage(QWidget):
    """Base class for authentication pages"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = QLabel("Welcome to Messenger!")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                background-color: #9DB4B8;
                color: #2C2C2C;
                font-size: 32px;
                font-weight: bold;
                padding: 25px;
                border-bottom: 2px solid #7A9499;
            }
        """)
        
        # Content area
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #E8E1E1;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignCenter)
        
        # Form container
        self.form_container = QFrame()
        self.form_container.setFixedSize(500, 520)
        self.form_container.setStyleSheet("""
            QFrame {
                background-color: #C8D4D6;
                border-radius: 20px;
                border: none;
            }
        """)
        
        content_layout.addWidget(self.form_container)
        
        # Add to main layout
        main_layout.addWidget(header)
        main_layout.addWidget(content_widget, 1)
        
        self.setLayout(main_layout)