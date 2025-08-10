# friend_list_page.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from http_add_friend_modal import AddFriendModal

class FriendListPage(QWidget):
    """A content-only widget for displaying the friend list."""
    friend_selected = pyqtSignal(dict) # Emit the full friend data dictionary

    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.friends_data = []  # Will store the list of friend dictionaries
        self.friend_containers = {} # To keep track of the created friend widgets
        self.add_friend_modal = None
        self.setup_ui()

    @pyqtSlot(dict)
    def on_friend_list_received(self, data):
        """Handles the fetched friend list from the backend."""
        print("UI: FriendListPage received friend list data.")
        if data.get("status") == "success":
            self.friends_data = data.get("friends", [])
            self.update_friends_display() # Update the UI with the new data
        else:
            print(f"UI Error: Could not parse friend list - {data.get('message')}")

    def setup_ui(self):
        """Setup the UI for the content area ONLY."""
        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.setup_top_bar(content_layout)
        self.setup_friends_area(content_layout)

    def setup_top_bar(self, parent_layout):
        """Setup the top bar with search and add friend button."""
        top_bar = QFrame()
        top_bar.setFixedHeight(80)
        top_bar.setStyleSheet("QFrame { background-color: #9DB4B8; border-bottom: 2px solid #7A9499; }")
        
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 15, 20, 15)
        # ... (Your existing top_bar code for search and add friend can go here) ...
        add_friend_btn = QPushButton("+ Add Friend")
        add_friend_btn.clicked.connect(self.show_add_friend_modal)
        # ... (Add styling and other widgets to top_layout) ...
        top_layout.addStretch()
        top_layout.addWidget(add_friend_btn)
        
        parent_layout.addWidget(top_bar)

    def setup_friends_area(self, parent_layout):
        """Setup the scrollable area for displaying friends."""
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: #9DB4B8; border: none; }")
        
        container_widget = QWidget()
        self.friends_layout = QVBoxLayout(container_widget)
        self.friends_layout.setContentsMargins(20, 20, 20, 20)
        self.friends_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.friends_layout.setSpacing(15)
        
        self.scroll_area.setWidget(container_widget)
        parent_layout.addWidget(self.scroll_area)
        
        self.update_friends_display() # Initial display update

    def update_friends_display(self):
        """Clears and redraws the friend list in the UI."""
        # Clear existing friend widgets from the layout
        for container in self.friend_containers.values():
            container.deleteLater()
        self.friend_containers.clear()

        if not self.friends_data:
            # Display "No Friends" message if the list is empty
            no_friends_label = QLabel("No friends found. Use the '+ Add Friend' button to connect.")
            no_friends_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_friends_label.setStyleSheet("QLabel { color: #E8E1E1; font-size: 18px; font-style: italic; padding: 50px; }")
            self.friend_containers['__no_friends__'] = no_friends_label
            self.friends_layout.addWidget(no_friends_label)
        else:
            # Create and add a widget for each friend
            for friend_info in self.friends_data:
                friend_username = friend_info.get('username')
                friend_container = self.create_friend_container(friend_info)
                self.friends_layout.addWidget(friend_container)
                self.friend_containers[friend_username] = friend_container

    def create_friend_container(self, friend_info):
        """Creates a clickable widget for a single friend."""
        container = QFrame()
        container.setFixedHeight(80)
        container.setStyleSheet("QFrame { background-color: #E8E1E1; border-radius: 15px; } QFrame:hover { background-color: #D5CECE; }")
        container.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(container)
        name_label = QLabel(friend_info.get('username', 'Unknown'))
        name_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #2C2C2C; }")
        layout.addWidget(name_label)
        layout.addStretch()

        # Connect the click event to emit the full friend_info dictionary
        container.mousePressEvent = lambda event, f_info=friend_info: self.friend_selected.emit(f_info)
        
        return container

    def show_add_friend_modal(self):
        """Shows the Add Friend dialog."""
        if not self.add_friend_modal:
            self.add_friend_modal = AddFriendModal(self.backend, self)
            self.add_friend_modal.friend_successfully_added.connect(self.refresh_friend_list)
        
        self.add_friend_modal.exec_()
    
    def refresh_friend_list(self):
        """Asks the backend to re-fetch the friend list."""
        if self.backend:
            self.backend.get_friends()