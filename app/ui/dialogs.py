from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QDateTimeEdit, QComboBox, QPushButton, QMessageBox, QFormLayout, QColorDialog)
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

class ProjectEditDialog(QDialog):
    def __init__(self, storage: Storage, project_data=None, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.project_data = project_data
        
        self.setWindowTitle("Edit Project" if project_data else "Add Project")
        self.layout = QVBoxLayout(self)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Project Name")
        self.layout.addWidget(self.name_edit)
        
        color_layout = QHBoxLayout()
        self.color_btn = QPushButton("Select Color")
        self.selected_color = "#3498db" # Default color
        
        if project_data:
            self.name_edit.setText(project_data.get('name', ''))
            self.selected_color = project_data.get('color') or "#3498db"
            
        self.update_color_btn()
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(QLabel("Color:"))
        color_layout.addWidget(self.color_btn)
        self.layout.addLayout(color_layout)
        
        self.save_btn = QPushButton("Save Project")
        self.save_btn.clicked.connect(self.save_project)
        self.layout.addWidget(self.save_btn)

    def update_color_btn(self):
        try:
            h = self.selected_color.lstrip('#')
            if len(h) == 6:
                r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                text_color = "black" if luminance > 0.5 else "white"
            else:
                text_color = "white"
        except:
            text_color = "white"
            
        self.color_btn.setStyleSheet(f"background-color: {self.selected_color}; color: {text_color};")

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()
            self.update_color_btn()

    def save_project(self):
        name = self.name_edit.text().strip()
        if not name:
            return
        try:
            if self.project_data:
                self.storage.update_project(self.project_data['id'], name, self.selected_color)
            else:
                self.storage.add_project(name, self.selected_color)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

from PySide6.QtWidgets import QListWidget, QListWidgetItem

class ManageProjectsDialog(QDialog):
    def __init__(self, storage: Storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle("Manage Projects")
        self.resize(400, 300)
        self.layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add New")
        self.add_btn.clicked.connect(self.add_project)
        btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.clicked.connect(self.edit_project)
        btn_layout.addWidget(self.edit_btn)
        
        self.del_btn = QPushButton("Delete Selected")
        self.del_btn.setStyleSheet("color: red;")
        self.del_btn.clicked.connect(self.delete_project)
        btn_layout.addWidget(self.del_btn)
        
        self.layout.addLayout(btn_layout)
        
        self.projects = []
        self.load_projects()
        
    def load_projects(self):
        self.list_widget.clear()
        self.projects = self.storage.get_projects()
        for p in self.projects:
            item = QListWidgetItem(p['name'])
            # Store ID in item data
            item.setData(Qt.ItemDataRole.UserRole, p['id'])
            self.list_widget.addItem(item)
            
    def add_project(self):
        dlg = ProjectEditDialog(self.storage, parent=self)
        if dlg.exec():
            self.load_projects()
            
    def edit_project(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        p_id = item.data(Qt.ItemDataRole.UserRole)
        project_data = next((p for p in self.projects if p['id'] == p_id), None)
        
        if project_data:
            dlg = ProjectEditDialog(self.storage, project_data, parent=self)
            if dlg.exec():
                self.load_projects()
                
    def delete_project(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        p_id = item.data(Qt.ItemDataRole.UserRole)
        
        res = QMessageBox.question(self, "Confirm Delete", 
                                   "Are you sure you want to delete this project? Sessions will be kept but unlinked from the project.", 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if res == QMessageBox.StandardButton.Yes:
            self.storage.delete_project(p_id)
            self.load_projects()
