# home_page.py - Complete implementation
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QListWidget, QListWidgetItem,
                             QTextEdit, QLineEdit, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from datetime import datetime

class ChatBubble(QWidget):
    def __init__(self, message, timestamp, is_sent=False):
        super().__init__()
        self.is_sent = is_sent
        self.setup_ui(message, timestamp)
    
    def setup_ui(self, message, timestamp):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Message bubble
        bubble = QLabel(message)
        bubble.setWordWrap(True)
        bubble.setStyleSheet(f"""
            QLabel {{
                background-color: {'#a8ccc8' if self.is_sent else '#b8a8a8'};
                border-radius: 15px;
                padding: 10px 15px;
                color: #333;
                font-size: 14px;
            }}
        """)
        
        # Timestamp
        time_label = QLabel(timestamp)
        time_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                margin: 2px 10px;
            }
        """)
        
        if self.is_sent:
            layout.setAlignment(Qt.AlignRight)
            time_label.setAlignment(Qt.AlignRight)
        else:
            layout.setAlignment(Qt.AlignLeft)
            time_label.setAlignment(Qt.AlignLeft)
        
        layout.addWidget(bubble)
        layout.addWidget(time_label)
        self.setLayout(layout)

class HomePage(QWidget):
    """Enhanced Home page with integrated chat functionality"""
    switch_to_friend_list = pyqtSignal()
    
    def __init__(self, backend=None):
        super().__init__()
        self.backend = backend
        self.current_chat = None
        self.chat_data = {}  # Store chat conversations
        self.chat_contacts = []  # List of friends we've chatted with
        self.current_user_name = None  # Track current user
        self.polling_timer = QTimer(self)
        
        self.setup_ui()
        self.setup_backend_connections()
        
        self.setup_polling_timer()
    
    def setup_backend_connections(self):
        """Connect backend signals to frontend handlers."""
        
        # This connection is correct for the HomePage if it can also send messages.
        self.backend.message_sent_response.connect(self.on_message_sent)
        
        # --- FIX: REMOVE OR COMMENT OUT THIS FINAL INCORRECT LINE ---
        # This connection is incorrect. The ChatPage handles message history.
        # self.backend.message_history_fetched.connect(self.on_message_history_received)
        
        self.backend.error_occurred.connect(self.on_backend_error)

    def on_message_sent(self, response):
        """Handle message sent confirmation"""
        print("✅ Message sent to server successfully")

    def on_messages_fetched(self, data):
        """Handle fetched messages from server"""
        if data.get("status") == "success":
            messages = data.get("messages", [])
            contact = data.get("contact")
            
        if contact and contact == self.current_chat:
            # Buat daftar pesan baru dari server
            server_messages = []
            for msg in messages:
                is_sent_by_me = msg.get('sender') == self.current_user_name
                server_messages.append({
                    'message': msg.get('content', ''),
                    'time': msg.get('timestamp', ''),
                    'sent': is_sent_by_me
                })
            
            # --- PERBAIKAN PENTING: HANYA UPDATE JIKA ADA PERUBAHAN ---
            # Ini mencegah UI berkedip jika tidak ada pesan baru.
            if self.chat_data.get(contact) != server_messages:
                print(f"✅ Fetched {len(server_messages)} messages for {contact}. UI is being updated.")
                self.chat_data[contact] = server_messages
                self.load_chat_messages(contact)
                self.update_chat_contacts_display() # Update preview pesan terakhir
            # else:
            #     # Tidak ada pesan baru, tidak melakukan apa-apa.
            #     print(f"👍 No new messages for {contact}.")


    def showEvent(self, event):
        """Dipanggil saat widget ditampilkan."""
        # Mulai polling lagi jika ada chat yang dipilih saat kembali ke halaman ini
        if self.current_chat and not self.polling_timer.isActive():
            self.polling_timer.start()
            print("▶️ Polling resumed as page became visible.")
        super().showEvent(event)

    def hideEvent(self, event):
        """Dipanggil saat widget disembunyikan."""
        # Selalu hentikan polling saat meninggalkan halaman untuk menghemat resource
        if self.polling_timer.isActive():
            self.polling_timer.stop()
            print("⏹️ Polling paused as page was hidden.")
        super().hideEvent(event)

    def on_backend_error(self, error_message):
        """Handle backend errors"""
        print(f"❌ Backend error: {error_message}")
    
    def setup_ui(self):
        # Main layout - 3 columns
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left sidebar (navigation)
        self.setup_left_sidebar(main_layout)
        
        # Middle area (chat contacts)
        self.setup_middle_area(main_layout)
        
        # Right area (chat or welcome)
        self.setup_right_area(main_layout)
    
    def setup_left_sidebar(self, parent_layout):
        """Setup the left sidebar with navigation"""
        sidebar = QFrame()
        sidebar.setFixedWidth(150)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #E8E1E1;
                border-right: 2px solid #B0C4C6;
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Home button (active)
        home_btn = QPushButton("Home")
        home_btn.setStyleSheet("""
            QPushButton {
                background-color: #9DB4B8;
                color: #2C2C2C;
                border: none;
                padding: 15px;
                font-size: 16px;
                font-weight: normal;
                text-align: left;
                border-bottom: 1px solid #7A9499;
            }
        """)
        home_btn.setFixedHeight(50)
        
        # Friend List button
        friend_list_btn = QPushButton("Friend List")
        friend_list_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8E1E1;
                color: #2C2C2C;
                border: none;
                padding: 15px;
                font-size: 16px;
                font-weight: normal;
                text-align: left;
                border-bottom: 1px solid #B0C4C6;
            }
            QPushButton:hover {
                background-color: #D5CECE;
            }
        """)
        friend_list_btn.setFixedHeight(50)
        friend_list_btn.clicked.connect(self.switch_to_friend_list.emit)
        
        sidebar_layout.addWidget(home_btn)
        sidebar_layout.addWidget(friend_list_btn)
        sidebar_layout.addStretch()
        
        parent_layout.addWidget(sidebar)
    
    def setup_middle_area(self, parent_layout):
        """Setup middle area for chat contacts"""
        middle_widget = QFrame()
        middle_widget.setFixedWidth(250)
        middle_widget.setStyleSheet("""
            QFrame {
                background-color: #d4d4d4;
                border-right: 1px solid #bbb;
            }
        """)
        
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        
        # Header
        header = QLabel("Chat Contacts")
        header.setStyleSheet("""
            QLabel {
                background-color: #a8ccc8;
                color: #333;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                border-bottom: 1px solid #999;
            }
        """)
        
        # Chat contacts list
        self.chat_contacts_list = QListWidget()
        self.chat_contacts_list.setStyleSheet("""
            QListWidget {
                background-color: #d4d4d4;
                border: none;
                outline: none;
            }
            QListWidget::item {
                border-bottom: 1px solid #bbb;
                padding: 12px 15px;
                background-color: #d4d4d4;
            }
            QListWidget::item:hover {
                background-color: #c8c8c8;
            }
            QListWidget::item:selected {
                background-color: #a8ccc8;
            }
        """)
        self.chat_contacts_list.itemClicked.connect(self.on_contact_selected)
        
        # Welcome message for empty contacts
        self.no_chats_label = QLabel("No active chats\nStart by adding friends!")
        self.no_chats_label.setAlignment(Qt.AlignCenter)
        self.no_chats_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 14px;
                font-style: italic;
                padding: 40px 20px;
            }
        """)
        
        middle_layout.addWidget(header)
        middle_layout.addWidget(self.chat_contacts_list)
        middle_layout.addWidget(self.no_chats_label)
        
        parent_layout.addWidget(middle_widget)
    
    def setup_right_area(self, parent_layout):
        """Setup right area for chat or welcome message"""
        self.right_widget = QWidget()
        right_layout = QVBoxLayout(self.right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Chat header
        self.chat_header = QFrame()
        self.chat_header.setStyleSheet("""
            QFrame {
                background-color: #a8ccc8;
                border-bottom: 1px solid #999;
                padding: 15px 20px;
            }
        """)
        
        header_layout = QHBoxLayout(self.chat_header)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        self.chat_title = QLabel("Welcome to Messenger!")
        self.chat_title.setStyleSheet("font-size: 18px; font-weight: 500; color: #333;")
        
        header_layout.addWidget(self.chat_title)
        header_layout.addStretch()
        
        # Chat area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #f0f0f0;
                border: none;
            }
        """)
        
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_content.setLayout(self.chat_layout)
        self.chat_scroll.setWidget(self.chat_content)
        
        # Welcome message
        self.welcome_message = QLabel("Start by selecting friends from Friend List\nto begin chatting!")
        self.welcome_message.setAlignment(Qt.AlignCenter)
        self.welcome_message.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #666;
                margin: 40px;
            }
        """)
        self.chat_layout.addWidget(self.welcome_message)
        
        # Input area
        self.input_frame = QFrame()
        self.input_frame.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border-top: 1px solid #ccc;
                padding: 15px 20px;
            }
        """)
        
        input_layout = QHBoxLayout(self.input_frame)
        input_layout.setContentsMargins(20, 15, 20, 15)
        
        # Message input
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px;
                border: 1px solid #bbb;
                border-radius: 20px;
                background-color: #fff;
                font-size: 14px;
            }
        """)
        self.message_input.returnPressed.connect(self.send_message)
        self.message_input.setEnabled(False)  # Disabled until chat is selected
        
        # Send button
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #a8ccc8;
                border: none;
                border-radius: 20px;
                padding: 10px 20px;
                font-size: 14px;
                color: #333;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #95b8b4;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setEnabled(False)  # Disabled until chat is selected
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_btn)
        
        right_layout.addWidget(self.chat_header)
        right_layout.addWidget(self.chat_scroll)
        right_layout.addWidget(self.input_frame)
        
        parent_layout.addWidget(self.right_widget)
    
    def add_chat_contact(self, friend_name):
        """Add friend to chat contacts list"""
        if friend_name not in self.chat_contacts:
            self.chat_contacts.append(friend_name)
            self.update_chat_contacts_display()
            print(f"Added {friend_name} to chat contacts")
    
    def setup_polling_timer(self):
        """Mengatur timer untuk polling pesan baru."""
        self.polling_timer.setInterval(3000)  # Interval 3000 ms = 3 detik
        self.polling_timer.timeout.connect(self.poll_for_messages)

    def poll_for_messages(self):
        """Meminta pesan baru jika ada obrolan yang aktif."""
        if self.current_chat and self.backend:
            print(f"🔄 Polling for new messages in chat with {self.current_chat}...")
            # Meminta semua pesan (server akan memberikan yang terbaru)
            self.backend.get_messages(self.current_chat)

    def set_current_chat(self, friend_name):
        """Set current active chat"""
        self.current_chat = friend_name

        # Fetch messages from server
        if self.backend:
            self.backend.get_messages(friend_name)

        self.load_chat_messages(friend_name)
        self.update_chat_header(friend_name)
        print(f"Set current chat to {friend_name}")
        self.polling_timer.start()
    
    def update_chat_contacts_display(self):
        """Update the chat contacts list display"""
        self.chat_contacts_list.clear()
        
        if not self.chat_contacts:
            self.no_chats_label.show()
            self.chat_contacts_list.hide()
        else:
            self.no_chats_label.hide()
            self.chat_contacts_list.show()
            
            for contact in self.chat_contacts:
                item = QListWidgetItem()
                contact_widget = QWidget()
                contact_layout = QVBoxLayout(contact_widget)
                contact_layout.setContentsMargins(0, 0, 0, 0)
                
                name_label = QLabel(contact)
                name_label.setStyleSheet("font-weight: 500; font-size: 16px; color: #333;")
                
                last_msg = "Active chat"
                if contact in self.chat_data and self.chat_data[contact]:
                    last_msg = self.chat_data[contact][-1]['message'][:30] + "..."
                
                preview_label = QLabel(last_msg)
                preview_label.setStyleSheet("font-size: 14px; color: #666; margin-top: 2px;")
                
                contact_layout.addWidget(name_label)
                contact_layout.addWidget(preview_label)
                
                item.setSizeHint(contact_widget.sizeHint())
                self.chat_contacts_list.addItem(item)
                self.chat_contacts_list.setItemWidget(item, contact_widget)
                item.setData(Qt.UserRole, contact)
    
    def on_contact_selected(self, item):
        """Handle contact selection from list"""
        contact_name = item.data(Qt.UserRole)
        self.set_current_chat(contact_name)
    
    def load_chat_messages(self, contact_name):
        """Load chat messages for selected contact"""
        # Clear current messages
        for i in reversed(range(self.chat_layout.count())): 
            child = self.chat_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Add messages if any exist
        if contact_name in self.chat_data and self.chat_data[contact_name]:
            for msg_data in self.chat_data[contact_name]:
                bubble = ChatBubble(
                    msg_data['message'], 
                    msg_data['time'], 
                    msg_data['sent']
                )
                self.chat_layout.addWidget(bubble)
        else:
            # Show welcome message for new chat
            welcome_msg = QLabel(f"Start your conversation with {contact_name}")
            welcome_msg.setAlignment(Qt.AlignCenter)
            welcome_msg.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #666;
                    margin: 40px 20px;
                    font-style: italic;
                }
            """)
            self.chat_layout.addWidget(welcome_msg)
        
        # Scroll to bottom
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )
        
        # Enable input
        self.message_input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.message_input.setFocus()
    
    def update_chat_header(self, contact_name):
        """Update chat header with contact name"""
        self.chat_title.setText(f"Chat with {contact_name}")
    
    def send_message(self):
        """Send message in current chat"""
        if not self.current_chat:
            return
        
        message_text = self.message_input.text().strip()
        if not message_text:
            return
        
        if self.backend:
            self.backend.send_message(self.current_chat, message_text)
        
        self.message_input.clear()
        
        # Add to local chat data
        current_time = datetime.now().strftime("%I:%M %p").lower()
        if self.current_chat not in self.chat_data:
            self.chat_data[self.current_chat] = []
        
        self.chat_data[self.current_chat].append({
            'message': message_text,
            'time': current_time,
            'sent': True
        })
        
        # Update UI
        bubble = ChatBubble(message_text, current_time, True)
        self.chat_layout.addWidget(bubble)
        self.message_input.clear()
        
        # Update contacts list to show latest message
        self.update_chat_contacts_display()
        
        # Scroll to bottom
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )
        
        print(f"Sent message to {self.current_chat}: {message_text}")