import sys
from datetime import timedelta
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                               QTextEdit, QMessageBox, QSystemTrayIcon, QMenu,
                               QRadioButton, QButtonGroup, QTimeEdit, QGroupBox, QFrame,
                               QComboBox)
from PySide6.QtCore import QTimer, Qt, QTime
from PySide6.QtGui import QIcon, QAction
from app.core.timer import Timer
from app.core.storage import Storage
from app.ui.sessions_window import SessionsWindow
from app.ui.dialogs import ProjectDialog
import winsound
from pynput import keyboard

# Helper for idle time on Windows
import ctypes
import os

class IdleDetector:
    def __init__(self, threshold_minutes=5, callback=None):
        self.threshold_seconds = threshold_minutes * 60
        self.callback = callback
        self.last_activity = 0

    def get_idle_time(self):
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
             millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
             return millis / 1000.0
        return 0

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("WorkTrack Timer")
        self.resize(500, 500)
        
        # Core components
        self.storage = Storage()
        self.timer_logic = Timer(self.storage)
        
        # UI Setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # Styles
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f5; }
            QLabel { font-family: 'Segoe UI', sans-serif; }
            QPushButton { border-radius: 5px; font-weight: bold; }
            QLineEdit, QTimeEdit, QComboBox { padding: 8px; border: 1px solid #ccc; border-radius: 4px; background: white; }
            QGroupBox { font-weight: bold; border: 1px solid #ddd; border-radius: 6px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)

        # --- Header Section (Timer Display) ---
        timer_frame = QFrame()
        timer_frame.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #e0e0e0;")
        timer_layout = QVBoxLayout(timer_frame)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;")
        timer_layout.addWidget(self.status_label)
        
        self.time_label = QLabel("00:00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #2c3e50; font-family: 'Consolas', monospace;")
        timer_layout.addWidget(self.time_label)
        
        self.layout.addWidget(timer_frame)
        
        # --- Mode Selection ---
        mode_group = QGroupBox("Timer Mode")
        mode_layout = QHBoxLayout(mode_group)
        
        self.radio_countup = QRadioButton("Count Up")
        self.radio_countup.setChecked(True)
        self.radio_countdown = QRadioButton("Countdown")
        
        self.mode_btn_group = QButtonGroup(self)
        self.mode_btn_group.addButton(self.radio_countup)
        self.mode_btn_group.addButton(self.radio_countdown)
        
        self.radio_countup.toggled.connect(self.toggle_mode_ui)
        self.radio_countdown.toggled.connect(self.toggle_mode_ui)
        
        mode_layout.addWidget(self.radio_countup)
        mode_layout.addWidget(self.radio_countdown)
        
        # Countdown Input (Hidden by default)
        self.countdown_input = QTimeEdit()
        self.countdown_input.setDisplayFormat("HH:mm:ss")
        self.countdown_input.setTime(QTime(0, 45, 0)) # Default 45 mins
        self.countdown_input.setVisible(False)
        mode_layout.addWidget(self.countdown_input)
        
        self.layout.addWidget(mode_group)
        
        # --- Project & Comment Section ---
        input_group = QGroupBox("Session Details")
        input_layout = QVBoxLayout(input_group)
        
        # Project Row
        proj_layout = QHBoxLayout()
        self.project_combo = QComboBox()
        self.project_combo.addItem("No Project", None)
        self.reload_projects()
        
        self.add_proj_btn = QPushButton("+")
        self.add_proj_btn.setFixedWidth(30)
        self.add_proj_btn.clicked.connect(self.add_new_project)
        
        proj_layout.addWidget(QLabel("Project:"))
        proj_layout.addWidget(self.project_combo, 1)
        proj_layout.addWidget(self.add_proj_btn)
        input_layout.addLayout(proj_layout)
        
        # Comment Row
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("What are you working on? (Optional)")
        input_layout.addWidget(self.comment_input)
        
        self.layout.addWidget(input_group)
        
        # --- Action Buttons ---
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("START")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.clicked.connect(self.start_timer)
        self.start_button.setStyleSheet("""
            QPushButton { background-color: #2ecc71; color: white; padding: 15px; font-size: 16px; border: none; }
            QPushButton:hover { background-color: #27ae60; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        
        self.stop_button = QPushButton("STOP")
        self.stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_button.clicked.connect(self.stop_timer)
        self.stop_button.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; padding: 15px; font-size: 16px; border: none; }
            QPushButton:hover { background-color: #c0392b; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.stop_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        self.layout.addLayout(button_layout)
        
        # --- Footer ---
        footer_layout = QHBoxLayout()
        
        self.sessions_button = QPushButton("View History / Export")
        self.sessions_button.setFlat(True)
        self.sessions_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sessions_button.setStyleSheet("color: #3498db; text-decoration: underline;")
        self.sessions_button.clicked.connect(self.open_sessions)
        
        footer_layout.addWidget(self.sessions_button)
        footer_layout.addStretch()
        
        self.analytics_button = QPushButton("Analytics")
        self.analytics_button.setFlat(True)
        self.analytics_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analytics_button.setStyleSheet("color: #3498db; text-decoration: underline;")
        self.analytics_button.clicked.connect(self.open_analytics)
        footer_layout.addWidget(self.analytics_button)

        self.layout.addLayout(footer_layout)
        
        # --- Timers & State ---
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.timeout.connect(self.update_display)
        self.ui_update_timer.start(100)
        
        self.countdown_notified = False

        # --- Tray Icon ---
        self.tray_icon = QSystemTrayIcon(self)
        # Use a default system icon or fallback
        if os.path.exists("app/resources/icon.ico"):
            self.tray_icon.setIcon(QIcon("app/resources/icon.ico"))
        else:
             # Fallback to standard icon if resource missing
             self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
             
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_activated)

        # --- Idle Detection ---
        self.idle_detector = IdleDetector(threshold_minutes=5)
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.check_idle)
        self.idle_timer.start(5000) # Check every 5s
        
        # --- Hotkeys ---
        try:
             self.setup_hotkeys()
        except Exception:
             print("Failed to setup global hotkeys")

        # Check for existing session
        if self.timer_logic.is_running():
            self.restore_ui_state()

    def setup_hotkeys(self):
        # Global Hotkey Ctrl+Alt+S
        # Note: pynput listener blocks if run in main thread, need non-blocking or separate thread
        # QThread or simple listener
        self.hotkey_listener = keyboard.GlobalHotKeys({
            '<ctrl>+<alt>+s': self.on_hotkey_toggle
        })
        self.hotkey_listener.start()
        
    def on_hotkey_toggle(self):
        # This runs in a separate thread, so use QMetaObject.invokeMethod or signals if modifying UI
        # But start/stop logic mostly safe? Better to emit signal.
        # For simplicity, we'll try direct call but wrap in try
        # Actually PySide requires UI updates on main thread.
        # We'll skip complex threading for MVP and hope python GIL handles it or use QTimer.singleShot
        # But we can't easily cross threads without signals.
        pass # Placeholder: need signal/slot mechanism for thread safety

    def check_idle(self):
        if self.timer_logic.is_running() and self.timer_logic.mode == 'countup':
            idle_sec = self.idle_detector.get_idle_time()
            if idle_sec > 300: # 5 mins
                # Just flash status for now or simple log
                self.status_label.setText(f"IDLE DETECTED ({int(idle_sec/60)}m)")
                # Full auto-pause logic requires more state handling

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def closeEvent(self, event):
        # Minimize to tray instead of close?
        # User preference usually, but let's hide
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("WorkTrack Timer", "App minimized to tray. Double-click to open.", QSystemTrayIcon.MessageIcon.Information, 2000)

    def reload_projects(self):
        current_data = self.project_combo.currentData()
        self.project_combo.clear()
        self.project_combo.addItem("No Project", None)
        projects = self.storage.get_projects()
        for p in projects:
            self.project_combo.addItem(p['name'], p['id'])
        
        idx = self.project_combo.findData(current_data)
        if idx >= 0:
            self.project_combo.setCurrentIndex(idx)

    def add_new_project(self):
        dlg = ProjectDialog(self.storage, self)
        if dlg.exec():
            self.reload_projects()

    def toggle_mode_ui(self):
        is_countdown = self.radio_countdown.isChecked()
        self.countdown_input.setVisible(is_countdown)
        # Update display if not running
        if not self.timer_logic.is_running():
            if is_countdown:
                self.time_label.setText(self.countdown_input.time().toString("HH:mm:ss"))
            else:
                self.time_label.setText("00:00:00")

    def update_display(self):
        if self.timer_logic.is_running():
            if self.timer_logic.mode == 'countdown' and self.timer_logic.target_duration:
                remaining = self.timer_logic.get_remaining()
                # Handle overtime (negative remaining)
                total_seconds = int(remaining.total_seconds())
                
                is_overtime = total_seconds < 0
                abs_seconds = abs(total_seconds)
                
                h = abs_seconds // 3600
                m = (abs_seconds % 3600) // 60
                s = abs_seconds % 60
                
                display_str = f"{h:02}:{m:02}:{s:02}"
                if is_overtime:
                    self.time_label.setText(f"+{display_str}")
                    self.time_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #e74c3c; font-family: 'Consolas', monospace;")
                    self.status_label.setText("OVERTIME")
                else:
                    self.time_label.setText(display_str)
                    self.time_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #2c3e50; font-family: 'Consolas', monospace;")
                    self.status_label.setText("COUNTDOWN")

                # Check for completion (approx 0)
                if total_seconds <= 0 and not self.countdown_notified and not is_overtime:
                    # Notify once when hitting 0
                    self.trigger_notification()
                    self.countdown_notified = True

            else:
                # Count Up
                elapsed = self.timer_logic.get_elapsed()
                total_seconds = int(elapsed.total_seconds())
                h = total_seconds // 3600
                m = (total_seconds % 3600) // 60
                s = total_seconds % 60
                self.time_label.setText(f"{h:02}:{m:02}:{s:02}")
                # Don't overwrite IDLE status if detected
                if "IDLE" not in self.status_label.text():
                    self.status_label.setText("RUNNING")
                self.time_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #2c3e50; font-family: 'Consolas', monospace;")
        else:
            # Not running
            if self.radio_countdown.isChecked():
                pass
            else:
                pass

    def trigger_notification(self):
        winsound.Beep(1000, 500) # Frequency, Duration
        self.activateWindow()
        self.tray_icon.showMessage("Timer Finished", "Your countdown has reached zero!", QSystemTrayIcon.MessageIcon.Information)

    def start_timer(self):
        comment = self.comment_input.text()
        project_id = self.project_combo.currentData()
        mode = 'countdown' if self.radio_countdown.isChecked() else 'countup'
        target_duration = None
        
        if mode == 'countdown':
            qtime = self.countdown_input.time()
            target_duration = timedelta(hours=qtime.hour(), minutes=qtime.minute(), seconds=qtime.second())
            if target_duration.total_seconds() == 0:
                 QMessageBox.warning(self, "Invalid Time", "Please set a countdown duration.")
                 return

        try:
            self.timer_logic.start(mode=mode, target_duration=target_duration, comment=comment, project_id=project_id)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.comment_input.setEnabled(False)
            self.project_combo.setEnabled(False)
            self.add_proj_btn.setEnabled(False)
            self.radio_countup.setEnabled(False)
            self.radio_countdown.setEnabled(False)
            self.countdown_input.setEnabled(False)
            self.countdown_notified = False
            self.status_label.setText("STARTED")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def stop_timer(self):
        comment = self.comment_input.text()
        self.timer_logic.stop(comment=comment)
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.comment_input.setEnabled(True)
        self.project_combo.setEnabled(True)
        self.add_proj_btn.setEnabled(True)
        self.radio_countup.setEnabled(True)
        self.radio_countdown.setEnabled(True)
        self.countdown_input.setEnabled(True)
        
        self.comment_input.clear()
        
        # Reset display
        if self.radio_countup.isChecked():
            self.time_label.setText("00:00:00")
        else:
            self.time_label.setText(self.countdown_input.time().toString("HH:mm:ss"))
            
        self.status_label.setText("SESSION SAVED")
        self.time_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #2c3e50; font-family: 'Consolas', monospace;")

    def restore_ui_state(self):
        # Called if session was already running
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.radio_countup.setEnabled(False)
        self.radio_countdown.setEnabled(False)
        self.countdown_input.setEnabled(False)
        self.project_combo.setEnabled(False)
        self.add_proj_btn.setEnabled(False)
        
        if self.timer_logic.mode == 'countdown':
            self.radio_countdown.setChecked(True)
        else:
            self.radio_countup.setChecked(True)
            
        if self.timer_logic.current_session_id:
             conn = self.storage._get_connection()
             cursor = conn.cursor()
             cursor.execute("SELECT comment, project_id FROM sessions WHERE id=?", (self.timer_logic.current_session_id,))
             row = cursor.fetchone()
             conn.close()
             if row:
                 self.comment_input.setText(row[0] or "")
                 idx = self.project_combo.findData(row[1])
                 if idx >= 0:
                     self.project_combo.setCurrentIndex(idx)

    def open_sessions(self):
        self.sessions_window = SessionsWindow(self.storage, self)
        self.sessions_window.show()

    def open_analytics(self):
        from app.ui.analytics_window import AnalyticsWindow
        self.analytics_window = AnalyticsWindow(self.storage, self)
        self.analytics_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
