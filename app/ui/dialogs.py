from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QDateTimeEdit, QComboBox, QPushButton, QMessageBox, QFormLayout)
from PySide6.QtCore import Qt, QDateTime
from app.core.storage import Storage
from datetime import datetime

class SessionDialog(QDialog):
    def __init__(self, storage: Storage, session_data=None, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.session_data = session_data
        
        self.setWindowTitle("Edit Session" if session_data else "Add Past Session")
        self.resize(400, 300)
        
        self.layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Start Time
        self.start_edit = QDateTimeEdit()
        self.start_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_edit.setCalendarPopup(True)
        form_layout.addRow("Start Time:", self.start_edit)
        
        # End Time
        self.end_edit = QDateTimeEdit()
        self.end_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_edit.setCalendarPopup(True)
        form_layout.addRow("End Time:", self.end_edit)
        
        # Project
        self.project_combo = QComboBox()
        self.project_combo.addItem("No Project", None)
        self.load_projects()
        form_layout.addRow("Project:", self.project_combo)
        
        # Comment
        self.comment_edit = QLineEdit()
        form_layout.addRow("Comment:", self.comment_edit)
        
        self.layout.addLayout(form_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(btn_layout)
        
        # Init Data
        if session_data:
            self.start_edit.setDateTime(QDateTime.fromString(session_data['start_ts'][:19], Qt.ISODate))
            if session_data.get('end_ts'):
                self.end_edit.setDateTime(QDateTime.fromString(session_data['end_ts'][:19], Qt.ISODate))
            else:
                self.end_edit.setDateTime(QDateTime.currentDateTime())
                
            self.comment_edit.setText(session_data.get('comment', ''))
            
            # Select project
            idx = self.project_combo.findData(session_data.get('project_id'))
            if idx >= 0:
                self.project_combo.setCurrentIndex(idx)
        else:
            now = QDateTime.currentDateTime()
            self.start_edit.setDateTime(now.addSecs(-3600)) # Default 1h ago
            self.end_edit.setDateTime(now)

    def load_projects(self):
        projects = self.storage.get_projects()
        for p in projects:
            self.project_combo.addItem(p['name'], p['id'])

    def save(self):
        start_dt = self.start_edit.dateTime().toPython()
        end_dt = self.end_edit.dateTime().toPython()
        comment = self.comment_edit.text()
        project_id = self.project_combo.currentData()
        
        if end_dt <= start_dt:
            QMessageBox.warning(self, "Invalid Duration", "End time must be after start time.")
            return
            
        duration = int((end_dt - start_dt).total_seconds())
        date_str = start_dt.strftime("%Y-%m-%d")
        
        try:
            if self.session_data:
                # Update
                self.storage.update_session_details(
                    self.session_data['id'],
                    start_dt.isoformat(),
                    end_dt.isoformat(),
                    duration,
                    date_str,
                    comment,
                    project_id
                )
            else:
                # Add
                self.storage.add_past_session(
                    start_dt.isoformat(),
                    end_dt.isoformat(),
                    date_str,
                    duration,
                    comment,
                    project_id
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

class ProjectDialog(QDialog):
    def __init__(self, storage: Storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle("Manage Projects")
        self.layout = QVBoxLayout(self)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Project Name")
        self.layout.addWidget(self.name_edit)
        
        self.add_btn = QPushButton("Add Project")
        self.add_btn.clicked.connect(self.add_project)
        self.layout.addWidget(self.add_btn)

    def add_project(self):
        name = self.name_edit.text().strip()
        if not name:
            return
        try:
            self.storage.add_project(name)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
