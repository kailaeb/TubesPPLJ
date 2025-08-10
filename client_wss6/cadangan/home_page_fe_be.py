from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QScrollArea, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor
from navigation_sidebar import NavigationSidebar
import datetime


class HomePage(QWidget):
    """Home page with chat interface - matches Figma design"""
    
    logout_requested = pyqtSignal()
    friend_list_requested = pyqtSignal()  # Emit when friend list navigation is requested
    
    def __init__(self):
        super().__init__()
        self.current_chat_user = None  # Currently selected friend for chat
        self.auth_token = None
        self.current_user = None
        self.has_chats = False  # Track if user has any chats
        
        # Create navigation sidebar
        self.sidebar = NavigationSidebar(active_page="home")
        self.sidebar.friend_list_clicked.connect(self.on_friend_list_clicked)
        
        self.setup_ui()
    
    def set_auth_token(self, token):
        """Set authentication token"""
        self.auth_token = token
    
    def set_current_user(self, user_info):
        """Set current logged in user info"""
        self.current_user = user_info
        if user_info:
            username = user_info.get('username', 'username')
    
    def setup_ui(self):
        """Setup the home page UI"""
        # Main layout - horizontal split with THREE sections
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left navigation sidebar (starts from very top)
        main_layout.addWidget(self.sidebar)
        
        # Middle chat list sidebar with controls at top
        self.setup_chat_list_area(main_layout)
        
        # Right main content area
        self.setup_main_content(main_layout)
    
    
    def setup_chat_controls_header(self, parent_layout):
        """Setup the chat controls header with start chat and search"""
        controls_header = QFrame()
        controls_header.setFixedHeight(80)
        controls_header.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border-bottom: 2px solid #B0C4C6;
            }
        """)
        
        controls_layout = QHBoxLayout(controls_header)
        controls_layout.setContentsMargins(30, 15, 30, 15)
        controls_layout.setSpacing(30)
        
        # "Start a new chat" label
        chat_title = QLabel("Start a new chat")
        chat_title.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)
        
        # Search input with icon
        search_input_container = QFrame()
        search_input_container.setMaximumWidth(400)
        search_input_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #B0C4C6;
                border-radius: 8px;
            }
        """)
        
        search_input_layout = QHBoxLayout(search_input_container)
        search_input_layout.setContentsMargins(10, 0, 10, 0)
        search_input_layout.setSpacing(8)
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 14px;
                background-color: transparent;
                border: none;
            }
        """)
        
        self.chat_search_input = QLineEdit()
        self.chat_search_input.setPlaceholderText("Search for messages ...")
        self.chat_search_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                font-size: 14px;
                color: #2C2C2C;
                padding: 8px 0px;
            }
        """)
        
        search_input_layout.addWidget(search_icon)
        search_input_layout.addWidget(self.chat_search_input)
        
        controls_layout.addWidget(chat_title)
        controls_layout.addWidget(search_input_container)
        controls_layout.addStretch()
        
        parent_layout.addWidget(controls_header)
    
    def setup_chat_list_area(self, parent_layout):
        """Setup the middle chat list sidebar with controls at top"""
        chat_sidebar = QFrame()
        chat_sidebar.setFixedWidth(350)  
        chat_sidebar.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border-left: 2px solid #B0C4C6;
                border-right: 2px solid #B0C4C6;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        chat_sidebar_layout = QVBoxLayout(chat_sidebar)
        chat_sidebar_layout.setContentsMargins(0, 0, 0, 0)  # Absolutely no margins
        chat_sidebar_layout.setSpacing(0)  # No spacing between elements
        
        # Chat header - "Start a new chat" at the very top - MATCH NAVIGATION HEIGHT
        chat_header = QFrame()
        chat_header.setFixedHeight(66)  # Match navigation button height exactly
        chat_header.setStyleSheet("""
            QFrame {
                background-color: #9DB4B8;
                border-bottom: 1px solid #7A9499;
                border-left: none;
                border-right: none;
                border-top: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        header_layout = QVBoxLayout(chat_header)
        header_layout.setContentsMargins(20, 0, 20, 0)  # Only left/right margins for text
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(0)
        
        chat_title = QLabel("Start a new chat")
        chat_title.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        chat_title.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(chat_title)
        
        # Search area - below "Start a new chat" - MATCH NAVIGATION HEIGHT
        search_container = QFrame()
        search_container.setFixedHeight(66)  # Match navigation button height exactly
        search_container.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border-bottom: 1px solid #B0C4C6;
                border-left: none;
                border-right: none;
                border-top: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(15, 13, 15, 13)  # Centered vertically
        search_layout.setSpacing(0)
        
        # Search input with icon
        search_input_container = QFrame()
        search_input_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #B0C4C6;
                border-radius: 8px;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        search_input_layout = QHBoxLayout(search_input_container)
        search_input_layout.setContentsMargins(10, 0, 10, 0)
        search_input_layout.setSpacing(8)
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 14px;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        self.chat_search_input = QLineEdit()
        self.chat_search_input.setPlaceholderText("Search for messages ...")
        self.chat_search_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                font-size: 14px;
                color: #2C2C2C;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        search_input_layout.addWidget(search_icon)
        search_input_layout.addWidget(self.chat_search_input)
        
        search_layout.addWidget(search_input_container)
        
        # Chat list scroll area - TAKES UP REMAINING SPACE
        self.chat_scroll_area = QScrollArea()
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat_scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #E8E1E1;
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QScrollBar:vertical {
                background-color: #B0C4C6;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background-color: #7A9499;
                border-radius: 3px;
                min-height: 20px;
            }
        """)
        
        # Container for chat items
        self.chat_container_widget = QWidget()
        self.chat_container_widget.setStyleSheet("""
            QWidget {
                background-color: #E8E1E1;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        # Chat layout for the scrollable area
        self.chat_layout = QVBoxLayout(self.chat_container_widget)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(0)
        self.chat_layout.setAlignment(Qt.AlignTop)
        
        print("🔍 DEBUG: chat_layout created in setup_chat_list_area")
        
        # Initially empty - just clean space for future chats
        self.chat_layout.addStretch()
        
        self.chat_scroll_area.setWidget(self.chat_container_widget)
        
        # Add to chat sidebar layout IN ORDER: header, search, then scrollable list
        chat_sidebar_layout.addWidget(chat_header)          # "Start a new chat" at top - height 66px
        chat_sidebar_layout.addWidget(search_container)     # Search below it - height 66px  
        chat_sidebar_layout.addWidget(self.chat_scroll_area) # Chat list takes remaining space
        
        # Add chat sidebar to main layout
        parent_layout.addWidget(chat_sidebar)
    
    @pyqtSlot()
    def on_friend_list_clicked(self):
        """Handle when friend list button is clicked"""
        print("👥 Friend list navigation requested from home")
        self.friend_list_requested.emit()

    @pyqtSlot()
    def on_send_button_clicked(self):
        """Send the message and show it in chat UI."""
        message = self.message_input.text().strip()
        if not message:
            return

    # # If you have a WebSocket connection, send first:
    #     if hasattr(self, 'websocket') and self.websocket.open:
    #         self.websocket.send(json.dumps({"type": "chat", "msg": message}))
    #         print("Message successfully sent.")
    #     else:
    #         print("WebSocket is not connected or unavailable.")
    #     # You can omit this if you don't have a WebSocket yet
    
    # Display it in the chat UI
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        message_widget = self.create_message_widget(
            message,
            is_sent=True,
            timestamp=timestamp
        )
        self.chat_layout.addWidget(message_widget)
        self.message_input.clear()

    def show_welcome_message(self):
        """Show welcome message when no chats exist - now in main content area"""
        # This method is called to show welcome in the chat list area
        # Clear existing widgets
        while self.chat_layout.count():
            child = self.chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add stretch to keep area clean
        self.chat_layout.addStretch()
    
    def setup_main_content(self, parent_layout):
        """Setup the main chat content area (right side) - shows welcome message"""
        main_content = QFrame()
        main_content.setStyleSheet("""
            QFrame {
                background-color: #9DB4B8;
            }
        """)
        
        content_layout = QVBoxLayout(main_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Top header with welcome message
        #self.setup_top_header(content_layout)
        
        # Main welcome area - shows the main welcome message
        self.setup_welcome_area(content_layout)
        
        # Message input area - HIDDEN initially, only shown when chatting
        self.setup_message_input(content_layout)
        
        parent_layout.addWidget(main_content)
    
    # def setup_top_header(self, parent_layout):
    #     """Setup the top header with welcome message"""
    #     header = QFrame()
    #     header.setFixedHeight(80)
    #     header.setStyleSheet("""
    #         QFrame {
    #             background-color: #9DB4B8;
    #             border-bottom: 2px solid #7A9499;
    #         }
    #     """)
        
        #parent_layout.addWidget(header)
    
    def setup_welcome_area(self, parent_layout):
        """Setup the main welcome area in the right content"""
        self.main_welcome_area = QFrame()
        self.main_welcome_area.setStyleSheet("""
            QFrame {
                background-color: #9DB4B8;
            }
        """)
        
        welcome_layout = QVBoxLayout(self.main_welcome_area)
        welcome_layout.setAlignment(Qt.AlignCenter)
        welcome_layout.setSpacing(30)
        welcome_layout.setContentsMargins(50, 50, 50, 50)
        
        # Welcome title
        title_label = QLabel("Welcome to Messenger!")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 36px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin: 20px;
            }
        """)
        
        # Subtitle
        subtitle_label = QLabel("Start by adding friends to begin chatting")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 20px;
                background-color: transparent;
                border: none;
                margin: 10px;
            }
        """)
        
        # Go to Friend List button
        friend_list_btn = QPushButton("Go to Friend List")
        friend_list_btn.setStyleSheet("""
            QPushButton {
                background-color: #7A9499;
                color: white;
                border: none;
                border-radius: 15px;
                padding: 20px 40px;
                font-size: 18px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #6A8489;
            }
            QPushButton:pressed {
                background-color: #5A7479;
            }
        """)
        friend_list_btn.clicked.connect(self.on_friend_list_clicked)
        
        
        welcome_layout.addWidget(title_label)
        welcome_layout.addWidget(subtitle_label)
        welcome_layout.addWidget(friend_list_btn, 0, Qt.AlignCenter)
        
        parent_layout.addWidget(self.main_welcome_area)
    
    def setup_message_input(self, parent_layout):
        """Setup the message input area at bottom - initially hidden"""
        self.input_container = QFrame()
        self.input_container.setFixedHeight(80)
        self.input_container.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border-top: 2px solid #B0C4C6;
            }
        """)
        
        input_layout = QHBoxLayout(self.input_container)
        input_layout.setContentsMargins(20, 15, 20, 15)
        input_layout.setSpacing(15)
        
        # Attachment button
        attach_btn = QPushButton("📎")
        attach_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #B0C4C6;
                border-radius: 8px;
                font-size: 18px;
                color: #7F8C8D;
                padding: 8px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """)
        
        # Message input
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Select a friend to start chatting...")
        self.message_input.setStyleSheet("""
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
        self.message_input.setFixedHeight(50)
        
        # Send button
        send_btn = QPushButton("Send")
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #9DB4B8;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 25px;
                font-size: 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #8BA5A9;
            }
            QPushButton:pressed {
                background-color: #7A9499;
            }
        """)
        send_btn.setFixedHeight(50)
        send_btn.clicked.connect(self.on_send_button_clicked)

        
        input_layout.addWidget(attach_btn)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_btn)
        
        # Hide the input container initially
        self.input_container.hide()
        
        parent_layout.addWidget(self.input_container)
    
    def start_chat_with_friend(self, friend_username):
        """Start a chat with the selected friend"""
        self.current_chat_user = friend_username
        print(f"🗨️ Starting chat with: {friend_username}")
        
        # Hide the welcome area and show chat interface
        self.main_welcome_area.hide()
        
        # Show the message input area when a chat is started
        self.input_container.show()
        
        # Update the message input placeholder
        self.message_input.setPlaceholderText(f"Type a message to {friend_username}...")
        
        # Replace welcome message with actual chat interface
        self.show_chat_interface()
        
        print(f"✅ Chat interface shown for {friend_username}")
    
    def show_chat_interface(self):
        """Show the actual chat interface instead of welcome message"""
        # Create new chat area if it doesn't exist OR update existing one
        if not hasattr(self, 'chat_area') or not self.chat_area:
            self.chat_area = QFrame()
            self.chat_area.setStyleSheet("""
                QFrame {
                    background-color: #B8C4C8;
                    border: none;
                }
            """)
            
            self.chat_area_layout = QVBoxLayout(self.chat_area)
            self.chat_area_layout.setContentsMargins(0, 0, 0, 0)
            self.chat_area_layout.setSpacing(0)
            
            # Chat header showing current friend's name (no welcome message)
            chat_header = QFrame()
            chat_header.setFixedHeight(60)
            chat_header.setStyleSheet("""
                QFrame {
                    background-color: #B8C4C8;
                    border-bottom: 1px solid #A0A8AC;
                }
            """)
            
            header_layout = QHBoxLayout(chat_header)
            header_layout.setContentsMargins(30, 15, 30, 15)
            header_layout.setAlignment(Qt.AlignLeft)
            
            self.friend_name_label = QLabel(f"{self.current_chat_user}")
            self.friend_name_label.setStyleSheet("""
                QLabel {
                    color: #2C2C2C;
                    font-size: 18px;
                    font-weight: bold;
                    background-color: transparent;
                    border: none;
                }
            """)
            
            header_layout.addWidget(self.friend_name_label)
            
            # Chat messages scroll area with gray background
            self.chat_messages_scroll = QScrollArea()
            self.chat_messages_scroll.setWidgetResizable(True)
            self.chat_messages_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.chat_messages_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.chat_messages_scroll.setStyleSheet("""
                QScrollArea {
                    background-color: #B8C4C8;
                    border: none;
                }
                QScrollBar:vertical {
                    background-color: #A0A8AC;
                    width: 6px;
                    border-radius: 3px;
                }
                QScrollBar::handle:vertical {
                    background-color: #808890;
                    border-radius: 3px;
                    min-height: 20px;
                }
            """)
            
            # Container for messages with gray background
            self.messages_container = QWidget()
            self.messages_container.setStyleSheet("""
                QWidget {
                    background-color: #B8C4C8;
                }
            """)
            
            self.messages_layout = QVBoxLayout(self.messages_container)
            self.messages_layout.setContentsMargins(20, 20, 20, 20)
            self.messages_layout.setSpacing(10)
            self.messages_layout.setAlignment(Qt.AlignTop)
            
            # Add stretch to keep area clean for new conversations
            self.messages_layout.addStretch()
            
            self.chat_messages_scroll.setWidget(self.messages_container)
            
            # Add only chat header and messages area (no welcome header)
            self.chat_area_layout.addWidget(chat_header)         # Friend name header only
            self.chat_area_layout.addWidget(self.chat_messages_scroll)  # Messages area (takes remaining space)
            
            # Insert the chat area before the input container
            main_layout = self.main_welcome_area.parent().layout()
            main_layout.insertWidget(0, self.chat_area)
        else:
            # Update existing chat area with new friend name
            if hasattr(self, 'friend_name_label'):
                self.friend_name_label.setText(f"{self.current_chat_user}")
        
        self.chat_area.show()
        print(f"💬 Chat interface updated for {self.current_chat_user}")
    
    
    def create_message_widget(self, message_text, is_sent, timestamp):
        """Create a message widget (sent or received) - for future real messaging"""
        message_container = QFrame()
        message_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                margin: 2px 0px;
            }
        """)

        container_layout = QHBoxLayout(message_container)
        container_layout.setContentsMargins(0, 0, 0, 0)

    # Message bubble
        message_bubble = QFrame()
        message_bubble.setMaximumWidth(400)

        if is_sent:
        # Sent message (right aligned)
            message_bubble.setStyleSheet("""
                QFrame {
                    background-color: #A8B8BC;
                    border-radius: 15px;
                    padding: 10px 15px;
                    margin: 2px;
                }
            """)
            container_layout.addStretch()
            container_layout.addWidget(message_bubble)
        else:
        # Received message (left aligned)
            message_bubble.setStyleSheet("""
                QFrame {
                    background-color: #D5CECE;
                    border-radius: 15px;
                    padding: 10px 15px;
                    margin: 2px;
                }
            """)
            container_layout.addWidget(message_bubble)
            container_layout.addStretch()

        bubble_layout = QVBoxLayout(message_bubble)
        bubble_layout.setContentsMargins(5, 5, 5, 5)
        bubble_layout.setSpacing(2)

    # Message text
        message_label = QLabel(message_text)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 14px;
                background-color: transparent;
                border: none;
            }
        """)

    # Timestamp
        time_label = QLabel(timestamp)
        time_label.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 10px;
                background-color: transparent;
                border: none;
            }
        """)
        time_label.setAlignment(Qt.AlignRight if is_sent else Qt.AlignLeft)

        bubble_layout.addWidget(message_label)
        bubble_layout.addWidget(time_label)

        return message_container

    
    def show_no_chat_selected(self):
        """Show welcome message when no chat is selected"""
        # Hide message input
        if hasattr(self, 'input_container'):
            self.input_container.hide()
        
        # Hide chat area if it exists
        if hasattr(self, 'chat_area'):
            self.chat_area.hide()
        
        # Show welcome area
        self.main_welcome_area.show()
        
        # Clear current chat user
        self.current_chat_user = None
    
    def add_chat_to_list(self, friend_username):
        """Add a new chat to the chat list when starting a conversation"""
        print(f"📝 Adding {friend_username} to chat list...")
        
        # Check if chat already exists
        for i in range(self.chat_layout.count()):
            widget = self.chat_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'objectName') and widget.objectName() == f"chat_{friend_username}":
                print(f"ℹ️ Chat with {friend_username} already exists")
                return  # Chat already exists
        
        # Clear any existing welcome messages or stretches
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                pass  # Spacer items don't need to be deleted
        
        # Create new chat item
        new_chat = self.create_chat_item(friend_username, "No messages yet", "Now")
        new_chat.setObjectName(f"chat_{friend_username}")
        
        # Add click handler to chat item
        def on_chat_clicked():
            print(f"💬 Chat item clicked: {friend_username}")
            self.start_chat_with_friend(friend_username)
        
        new_chat.mousePressEvent = lambda event: on_chat_clicked()
        
        # Insert at the top
        self.chat_layout.insertWidget(0, new_chat)
        
        # Add stretch back at the end to push chats to top
        self.chat_layout.addStretch()
        
        print(f"✅ Added {friend_username} to chat list successfully")
    
    def create_chat_item(self, name, last_message, time):
        """Create a chat item widget"""
        chat_item = QFrame()
        chat_item.setFixedHeight(80)
        chat_item.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border-bottom: 1px solid #D0C9C9;
                padding: 0px;
            }
            QFrame:hover {
                background-color: #D5CECE;
            }
        """)
        chat_item.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(chat_item)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        # Top row: name and time
        top_row = QHBoxLayout()
        
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            QLabel {
                color: #2C2C2C;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)
        
        time_label = QLabel(time)
        time_label.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 12px;
                background-color: transparent;
                border: none;
            }
        """)
        time_label.setAlignment(Qt.AlignRight)
        
        top_row.addWidget(name_label)
        top_row.addStretch()
        top_row.addWidget(time_label)
        
        # Bottom row: last message
        message_label = QLabel(last_message)
        message_label.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 14px;
                background-color: transparent;
                border: none;
            }
        """)
        
        layout.addLayout(top_row)
        layout.addWidget(message_label)
        
        return chat_item