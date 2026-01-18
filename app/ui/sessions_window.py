from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                               QPushButton, QHBoxLayout, QHeaderView, QFileDialog, QMessageBox,
                               QLabel, QDateEdit, QLineEdit)
from PySide6.QtCore import Qt, QDate
from app.core.storage import Storage
from app.core.export import Exporter
from app.ui.dialogs import SessionDialog
from datetime import datetime

class SessionsWindow(QDialog):
    def __init__(self, storage: Storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle("Sessions History")
        self.resize(900, 600)
        
        self.layout = QVBoxLayout(self)
        
        # --- Filters ---
        filter_layout = QHBoxLayout()
        
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate.currentDate().addDays(-30)) # Default last 30 days
        filter_layout.addWidget(QLabel("From:"))
        filter_layout.addWidget(self.date_from)
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        filter_layout.addWidget(QLabel("To:"))
        filter_layout.addWidget(self.date_to)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search comments or project...")
        filter_layout.addWidget(self.search_input)
        
        self.apply_filter_btn = QPushButton("Apply")
        self.apply_filter_btn.clicked.connect(self.load_data)
        filter_layout.addWidget(self.apply_filter_btn)
        
        self.layout.addLayout(filter_layout)
        
        # --- Toolbar ---
        toolbar_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add Session")
        self.add_btn.clicked.connect(self.add_session)
        toolbar_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.clicked.connect(self.edit_session)
        toolbar_layout.addWidget(self.edit_btn)
        
        self.del_btn = QPushButton("Delete Selected")
        self.del_btn.setStyleSheet("color: red;")
        self.del_btn.clicked.connect(self.delete_session)
        toolbar_layout.addWidget(self.del_btn)
        
        toolbar_layout.addStretch()
        
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(self.export_csv)
        toolbar_layout.addWidget(self.export_csv_btn)
        
        self.export_excel_btn = QPushButton("Export Excel")
        self.export_excel_btn.clicked.connect(self.export_excel)
        toolbar_layout.addWidget(self.export_excel_btn)
        
        self.layout.addLayout(toolbar_layout)
        
        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Date", "Project", "Start", "End", "Duration", "Comment"])
        self.table.setColumnCount(7) # Updated count
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.hideColumn(0) # Hide ID
        self.table.doubleClicked.connect(self.edit_session)
        self.layout.addWidget(self.table)
        
        # Close
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        self.layout.addWidget(self.close_btn)
        
        self.current_sessions = []
        self.load_data()

    def load_data(self):
        d_from = self.date_from.date().toString("yyyy-MM-dd")
        d_to = self.date_to.date().toString("yyyy-MM-dd")
        search = self.search_input.text()
        
        self.current_sessions = self.storage.get_sessions(limit=None, date_from=d_from, date_to=d_to, search=search)
        self.table.setRowCount(len(self.current_sessions))
        
        for i, session in enumerate(self.current_sessions):
            # ID
            self.table.setItem(i, 0, QTableWidgetItem(str(session['id'])))
            
            # Date
            self.table.setItem(i, 1, QTableWidgetItem(session.get('date', '')))
            
            # Project
            self.table.setItem(i, 2, QTableWidgetItem(session.get('project_name') or '-'))
            
            # Start
            start = session.get('start_ts', '')
            if start:
                try:
                    dt = datetime.fromisoformat(start)
                    start = dt.strftime("%H:%M:%S")
                except: pass
            self.table.setItem(i, 3, QTableWidgetItem(start))
            
            # End
            end = session.get('end_ts', '')
            if end:
                try:
                    dt = datetime.fromisoformat(end)
                    end = dt.strftime("%H:%M:%S")
                except: pass
            self.table.setItem(i, 4, QTableWidgetItem(end or "Running"))
            
            # Duration
            dur_sec = session.get('duration_sec')
            dur_str = ""
            if dur_sec is not None:
                m, s = divmod(dur_sec, 60)
                h, m = divmod(m, 60)
                dur_str = f"{h:02}:{m:02}:{s:02}"
            self.table.setItem(i, 5, QTableWidgetItem(dur_str))
            
            # Comment
            self.table.setItem(i, 6, QTableWidgetItem(session.get('comment', '')))

    def add_session(self):
        dlg = SessionDialog(self.storage, parent=self)
        if dlg.exec():
            self.load_data()

    def edit_session(self):
        row = self.table.currentRow()
        if row < 0:
            return
        
        # Get session ID from hidden column 0
        s_id = int(self.table.item(row, 0).text())
        # Find session data
        session = next((s for s in self.current_sessions if s['id'] == s_id), None)
        
        if session:
            dlg = SessionDialog(self.storage, session_data=session, parent=self)
            if dlg.exec():
                self.load_data()

    def delete_session(self):
        row = self.table.currentRow()
        if row < 0:
            return
        
        s_id = int(self.table.item(row, 0).text())
        
        res = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this session?", 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if res == QMessageBox.StandardButton.Yes:
            self.storage.delete_session(s_id)
            self.load_data()

    def export_csv(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Export CSV", "sessions.csv", "CSV Files (*.csv)")
        if filepath:
            try:
                Exporter.export_csv(filepath, self.current_sessions)
                QMessageBox.information(self, "Success", "Export successful!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def export_excel(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Export Excel", "sessions.xlsx", "Excel Files (*.xlsx)")
        if filepath:
            try:
                Exporter.export_excel(filepath, self.current_sessions)
                QMessageBox.information(self, "Success", "Export successful!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
