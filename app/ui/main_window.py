import sys
from datetime import timedelta
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                               QTextEdit, QMessageBox, QSystemTrayIcon, QMenu,
                               QRadioButton, QButtonGroup, QTimeEdit, QGroupBox, QFrame,
                               QComboBox, QDialog, QGridLayout)
from PySide6.QtCore import QTimer, Qt, QTime
from PySide6.QtGui import QIcon, QAction
from app.core.timer import Timer
from app.core.storage import Storage
from app.ui.sessions_window import SessionsWindow
from app.ui.dialogs import ManageProjectsDialog
from app.ui.settings_dialog import SettingsDialog
import winsound
from pynput import keyboard

# Helper for idle time on Windows
import ctypes
import os

class IdleDetector:
    def __init__(self):
        pass

    def get_idle_time(self):
        """Returns idle time in seconds."""
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
             millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
             return millis / 1000.0
        return 0

class IdleWarningDialog(QDialog):
    def __init__(self, timeout_sec=30, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Are you still working?")
        self.resize(300, 150)
        self.timeout_sec = timeout_sec
        self.remaining = timeout_sec
        
        layout = QVBoxLayout(self)
        self.label = QLabel(f"No activity detected.\nPausing timer in {self.remaining} seconds.")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.label)
        
        btn = QPushButton("I'm still here!")
        btn.setStyleSheet("background-color: #2ecc71; color: white; padding: 10px;")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

    def tick(self):
        self.remaining -= 1
        self.label.setText(f"No activity detected.\nPausing timer in {self.remaining} seconds.")
        if self.remaining <= 0:
            self.reject() # Timeout -> Auto Stop

class SmartReminderDialog(QDialog):
    def __init__(self, worked_minutes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Smart Reminder")
        self.resize(350, 300)
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel(f"You've been working for {worked_minutes} minutes straight.\n\nIt's good to take a step back and refresh your mind!")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        
        self.break_btn = QPushButton("☕ Take a 5 min break")
        self.break_btn.setStyleSheet("background-color: #3498db; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.break_btn.clicked.connect(self.take_break)
        btn_layout.addWidget(self.break_btn)
        
        self.switch_btn = QPushButton("🔄 Switch Project / Task")
        self.switch_btn.setStyleSheet("background-color: #9b59b6; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.switch_btn.clicked.connect(self.switch_project)
        btn_layout.addWidget(self.switch_btn)
        
        self.continue_btn = QPushButton("▶ Continue Working")
        self.continue_btn.setStyleSheet("background-color: #2ecc71; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.continue_btn.clicked.connect(self.continue_work)
        btn_layout.addWidget(self.continue_btn)
        
        self.stop_btn = QPushButton("⏹ Stop Timer")
        self.stop_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.stop_btn.clicked.connect(self.stop_work)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
        self.action = None
        
    def take_break(self):
        self.action = "break"
        self.accept()
        
    def switch_project(self):
        self.action = "switch"
        self.accept()
        
    def continue_work(self):
        self.action = "continue"
        self.accept()
        
    def stop_work(self):
        self.action = "stop"
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("OneStop-Worktimer")
        self.resize(550, 650)
        
        # Core components
        self.storage = Storage()
        self.timer_logic = Timer(self.storage)
        
        # Idle State
        self.idle_detector = IdleDetector()
        self.auto_paused = False
        self.idle_warning_active = False
        self.warning_dialog = None
        
        # Smart Reminders State
        self.smart_reminder_active = False
        self.next_reminder_sec = 0
        
        # UI Setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # Quick Start (layout created early so reload_projects() can use it)
        self.quick_start_group = QGroupBox("Quick Start")
        self.quick_start_layout = QGridLayout(self.quick_start_group)
        
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
        
        self.add_proj_btn = QPushButton("⚙")
        self.add_proj_btn.setToolTip("Manage Projects")
        self.add_proj_btn.setFixedWidth(30)
        self.add_proj_btn.clicked.connect(self.manage_projects)
        
        proj_layout.addWidget(QLabel("Project:"))
        proj_layout.addWidget(self.project_combo, 1)
        proj_layout.addWidget(self.add_proj_btn)
        input_layout.addLayout(proj_layout)
        
        # Comment Row
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("What are you working on? (Optional)")
        input_layout.addWidget(self.comment_input)
        
        self.layout.addWidget(input_group)
        
        # --- Quick Start Projects (widget added to layout here) ---
        self.layout.addWidget(self.quick_start_group)
        
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
        
        self.sessions_button = QPushButton("History")
        self.sessions_button.setFlat(True)
        self.sessions_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sessions_button.setStyleSheet("color: #3498db; text-decoration: underline;")
        self.sessions_button.clicked.connect(self.open_sessions)
        footer_layout.addWidget(self.sessions_button)

        self.analytics_button = QPushButton("Analytics")
        self.analytics_button.setFlat(True)
        self.analytics_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analytics_button.setStyleSheet("color: #3498db; text-decoration: underline;")
        self.analytics_button.clicked.connect(self.open_analytics)
        footer_layout.addWidget(self.analytics_button)
        
        footer_layout.addStretch()

        self.settings_button = QPushButton("Settings")
        self.settings_button.setFlat(True)
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.setStyleSheet("color: #7f8c8d; text-decoration: underline;")
        self.settings_button.clicked.connect(self.open_settings)
        footer_layout.addWidget(self.settings_button)

        self.layout.addLayout(footer_layout)
        
        # --- Timers & State ---
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.timeout.connect(self.update_display)
        self.ui_update_timer.start(100)
        
        self.countdown_notified = False

        # --- Tray Icon ---
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists("app/resources/icon.ico"):
            self.tray_icon.setIcon(QIcon("app/resources/icon.ico"))
        else:
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

        # --- Idle Loop ---
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.check_idle)
        self.idle_timer.start(2000) # Check every 2s
        
        # --- Hotkeys ---
        try:
             self.setup_hotkeys()
        except Exception:
             pass

        # Check for existing session
        if self.timer_logic.is_running():
            self.restore_ui_state()

    def setup_hotkeys(self):
        self.hotkey_listener = keyboard.GlobalHotKeys({
            '<ctrl>+<alt>+s': self.on_hotkey_toggle
        })
        self.hotkey_listener.start()
        
    def on_hotkey_toggle(self):
        # Thread safety note: strictly this should emit a signal
        pass 

    def check_idle(self):
        # Settings
        enabled = self.storage.get_setting("idle_enabled", False)
        if not enabled:
            return

        threshold_sec = self.storage.get_setting("idle_threshold", 5) * 60
        warning_sec = self.storage.get_setting("idle_warning_sec", 30)
        auto_resume = self.storage.get_setting("idle_auto_resume", True)
        
        idle_time = self.idle_detector.get_idle_time()

        # Case 1: Timer is running, User becomes idle
        if self.timer_logic.is_running() and self.timer_logic.mode == 'countup':
            if idle_time > threshold_sec:
                if not self.idle_warning_active:
                    self.show_idle_warning(warning_sec)

        # Case 2: Auto-paused, User returns
        if self.auto_paused and auto_resume:
            # Active if idle time is very low (user moved mouse recently)
            if idle_time < 2.0:
                self.resume_from_auto_pause()
                
    def show_idle_warning(self, warning_sec):
        self.idle_warning_active = True
        self.warning_dialog = IdleWarningDialog(warning_sec, self)
        
        # Non-blocking exec? No, QDialog.exec() blocks.
        # But we want the background timer to update.
        # We also need to know if it rejected (timeout) or accepted (user click)
        # However, checking 'idle' requires the main loop.
        
        # Strategy: Use exec(). It runs its own event loop, so our background timers (idle check)
        # might still fire if they are on the main thread? Yes, QTimer fires in event loop.
        
        res = self.warning_dialog.exec()
        
        self.idle_warning_active = False
        
        if res == QDialog.Accepted:
            # User clicked "I'm here"
            # Do nothing, just continue
            pass
        else:
            # Timeout (auto stop)
            # OR user closed it manually? If closed manually, assume working.
            if self.warning_dialog.remaining <= 0:
                self.auto_stop_timer()

    def auto_stop_timer(self):
        self.stop_timer()
        self.auto_paused = True
        self.status_label.setText("AUTO-PAUSED (IDLE)")
        self.tray_icon.showMessage("Timer Auto-Paused", "You were idle, so we stopped the timer.", QSystemTrayIcon.MessageIcon.Information)

    def resume_from_auto_pause(self):
        # Restart timer
        # We need to preserve the project/comment
        # But stop_timer cleared inputs. 
        # Ideally, auto_stop should cache them or not clear them.
        # For now, let's just start a new session with previous values if possible?
        # Or better: don't clear inputs if auto-stopped.
        
        # NOTE: self.stop_timer() clears inputs. We should fix that.
        
        # Quick fix: Retrieve last session settings?
        # Let's just start.
        self.start_timer()
        self.auto_paused = False
        self.status_label.setText("RESUMED (AUTO)")
        self.tray_icon.showMessage("Timer Resumed", "Welcome back! Timer started.", QSystemTrayIcon.MessageIcon.Information)

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("OneStop-Worktimer", "App minimized to tray. Double-click to open.", QSystemTrayIcon.MessageIcon.Information, 2000)

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
            
        self.reload_quick_start_buttons(projects)

    def reload_quick_start_buttons(self, projects):
        # Clear existing buttons
        while self.quick_start_layout.count():
            item = self.quick_start_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        if not projects:
            lbl = QLabel("No projects added yet.")
            lbl.setStyleSheet("color: #7f8c8d; font-style: italic;")
            self.quick_start_layout.addWidget(lbl, 0, 0)
            return
            
        row, col = 0, 0
        max_cols = 3
        for p in projects:
            btn = QPushButton(f"▶ {p['name']}")
            color = p.get('color') or '#3498db'
            
            # Calculate text color based on background luminance
            try:
                # Basic hex to rgb
                h = color.lstrip('#')
                if len(h) == 6:
                    r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                    text_color = "black" if luminance > 0.5 else "white"
                else:
                    text_color = "white"
            except:
                text_color = "white"
                
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color}; 
                    color: {text_color}; 
                    border-radius: 4px; 
                    padding: 10px;
                    font-weight: bold;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {color}dd;
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Use a closure to capture the project id
            btn.clicked.connect(lambda checked=False, pid=p['id']: self.quick_start_project(pid))
            self.quick_start_layout.addWidget(btn, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
            
    def quick_start_project(self, project_id):
        if self.timer_logic.is_running():
            QMessageBox.warning(self, "Timer Running", "Please stop the current timer first.")
            return
            
        # Set project combo
        idx = self.project_combo.findData(project_id)
        if idx >= 0:
            self.project_combo.setCurrentIndex(idx)
            
        # Start timer
        self.start_timer()

    def manage_projects(self):
        dlg = ManageProjectsDialog(self.storage, self)
        dlg.exec()
        self.reload_projects()

    def toggle_mode_ui(self):
        is_countdown = self.radio_countdown.isChecked()
        self.countdown_input.setVisible(is_countdown)
        if not self.timer_logic.is_running():
            if is_countdown:
                self.time_label.setText(self.countdown_input.time().toString("HH:mm:ss"))
            else:
                self.time_label.setText("00:00:00")

    def update_display(self):
        if self.timer_logic.is_running():
            # Calculate elapsed time for smart reminders
            elapsed = self.timer_logic.get_elapsed()
            elapsed_seconds = int(elapsed.total_seconds())
            
            if self.timer_logic.mode == 'countdown' and self.timer_logic.target_duration:
                remaining = self.timer_logic.get_remaining()
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

                if total_seconds <= 0 and not self.countdown_notified and not is_overtime:
                    self.trigger_notification()
                    self.countdown_notified = True
            else:
                total_seconds = elapsed_seconds
                h = total_seconds // 3600
                m = (total_seconds % 3600) // 60
                s = total_seconds % 60
                self.time_label.setText(f"{h:02}:{m:02}:{s:02}")
                
                if "PAUSED" not in self.status_label.text():
                     self.status_label.setText("RUNNING")
                
                self.time_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #2c3e50; font-family: 'Consolas', monospace;")
                
            # Check for smart reminder (based on elapsed time, not remaining time)
            if self.next_reminder_sec > 0 and elapsed_seconds >= self.next_reminder_sec and not self.smart_reminder_active:
                self.show_smart_reminder(elapsed_seconds)
        else:
            if self.radio_countdown.isChecked():
                pass

    def show_smart_reminder(self, total_seconds):
        self.smart_reminder_active = True
        winsound.Beep(1000, 500)
        self.activateWindow()
        
        worked_minutes = total_seconds // 60
        dlg = SmartReminderDialog(worked_minutes, self)
        
        # We don't want to block the timer updates entirely, but QDialog.exec() runs its own event loop
        # so QTimer will still fire.
        dlg.exec()
        
        action = dlg.action
        self.smart_reminder_active = False
        
        smart_interval = int(self.storage.get_setting("smart_interval", 50))
        
        if action == "break":
            # Stop current timer
            self.stop_timer()
            # Start a 5 min countdown
            self.radio_countdown.setChecked(True)
            self.countdown_input.setTime(QTime(0, 5, 0))
            # Set project to none, comment to break
            self.project_combo.setCurrentIndex(0)
            self.comment_input.setText("Coffee Break ☕")
            self.start_timer()
            
        elif action == "switch":
            self.stop_timer()
            self.manage_projects() # Just open project manager or let them pick from UI
            # They can manually start again
            
        elif action == "stop":
            self.stop_timer()
            
        elif action == "continue" or action is None:
            # Just bump the next reminder time
            self.next_reminder_sec += smart_interval * 60

    def trigger_notification(self):
        winsound.Beep(1000, 500)
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
            self.auto_paused = False # Reset flag
            
            # Setup smart reminders
            smart_enabled = self.storage.get_setting("smart_enabled", True)
            smart_interval = self.storage.get_setting("smart_interval", 50)
            if smart_enabled:
                self.next_reminder_sec = int(smart_interval) * 60
            else:
                self.next_reminder_sec = 0
                
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
        
        # Only clear inputs if NOT auto-paused
        # But wait, stop_timer IS called by auto_stop.
        # We need to distinguish or just not clear inputs generally?
        # User preference usually is to clear.
        # But for auto-resume, we want them back.
        # Let's save them if auto-pausing.
        
        # If this call is coming from button click, self.auto_paused is False/True depending on state.
        # Actually, let's just NOT clear inputs on stop. The user can clear them if they want, 
        # or we clear them on START of next session?
        # Let's clear on stop only if manual.
        
        # Hack: Check if we are inside auto_stop logic?
        # Better: modify stop_timer signature or check caller.
        # Simplest: Just don't clear inputs here. Clear them when 'Start' is clicked? 
        # No, 'Start' reads them.
        
        # Let's just keep inputs for now. Frictionless means remembering context usually.
        # self.comment_input.clear() 
        
        if self.radio_countup.isChecked():
            self.time_label.setText("00:00:00")
        else:
            self.time_label.setText(self.countdown_input.time().toString("HH:mm:ss"))
            
        self.status_label.setText("SESSION SAVED")
        self.time_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #2c3e50; font-family: 'Consolas', monospace;")

    def restore_ui_state(self):
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

    def open_settings(self):
        dlg = SettingsDialog(self.storage, self)
        dlg.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
