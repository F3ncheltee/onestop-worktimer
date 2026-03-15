from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QCheckBox, QSpinBox, QPushButton, QGroupBox, QFormLayout)
from app.core.storage import Storage

class SettingsDialog(QDialog):
    def __init__(self, storage: Storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle("Settings")
        self.resize(400, 300)
        
        self.layout = QVBoxLayout(self)
        
        # --- Idle Detection Settings ---
        idle_group = QGroupBox("Idle Detection")
        idle_layout = QFormLayout(idle_group)
        
        # Enable Toggle
        self.idle_enabled_cb = QCheckBox("Enable Idle Detection")
        idle_layout.addRow(self.idle_enabled_cb)
        
        # Threshold
        self.idle_threshold_spin = QSpinBox()
        self.idle_threshold_spin.setRange(1, 120)
        self.idle_threshold_spin.setSuffix(" min")
        idle_layout.addRow("Idle Threshold:", self.idle_threshold_spin)
        
        # Warning Duration (Time before auto-stop)
        self.warning_duration_spin = QSpinBox()
        self.warning_duration_spin.setRange(10, 300)
        self.warning_duration_spin.setSuffix(" sec")
        idle_layout.addRow("Warning Timeout:", self.warning_duration_spin)
        
        # Auto-Resume
        self.auto_resume_cb = QCheckBox("Auto-resume when activity detected")
        self.auto_resume_cb.setToolTip("If the timer was auto-stopped, it will restart when you move the mouse.")
        idle_layout.addRow(self.auto_resume_cb)
        
        self.layout.addWidget(idle_group)
        
        # --- Smart Reminders Settings ---
        smart_group = QGroupBox("Smart Reminders")
        smart_layout = QFormLayout(smart_group)
        
        self.smart_enabled_cb = QCheckBox("Enable Smart Reminders")
        self.smart_enabled_cb.setToolTip("Get suggestions to take a break or switch tasks after working for a while.")
        smart_layout.addRow(self.smart_enabled_cb)
        
        self.smart_interval_spin = QSpinBox()
        self.smart_interval_spin.setRange(10, 240)
        self.smart_interval_spin.setSuffix(" min")
        smart_layout.addRow("Reminder Interval:", self.smart_interval_spin)
        
        self.layout.addWidget(smart_group)
        
        # --- Buttons ---
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(btn_layout)
        
        # Load current values
        self.load_settings()
        
        # Connect signals to enable/disable fields
        self.idle_enabled_cb.toggled.connect(self.update_states)
        self.smart_enabled_cb.toggled.connect(self.update_states)
        self.update_states(False) # Initial call to set states correctly based on loaded values
        self.idle_threshold_spin.setEnabled(self.idle_enabled_cb.isChecked())
        self.warning_duration_spin.setEnabled(self.idle_enabled_cb.isChecked())
        self.auto_resume_cb.setEnabled(self.idle_enabled_cb.isChecked())
        self.smart_interval_spin.setEnabled(self.smart_enabled_cb.isChecked())

    def load_settings(self):
        # Defaults
        enabled = self.storage.get_setting("idle_enabled", False)
        threshold = self.storage.get_setting("idle_threshold", 5)
        warning = self.storage.get_setting("idle_warning_sec", 30)
        auto_resume = self.storage.get_setting("idle_auto_resume", True)
        
        smart_enabled = self.storage.get_setting("smart_enabled", True)
        smart_interval = self.storage.get_setting("smart_interval", 50)
        
        self.idle_enabled_cb.setChecked(bool(enabled))
        self.idle_threshold_spin.setValue(int(threshold))
        self.warning_duration_spin.setValue(int(warning))
        self.auto_resume_cb.setChecked(bool(auto_resume))
        
        self.smart_enabled_cb.setChecked(bool(smart_enabled))
        self.smart_interval_spin.setValue(int(smart_interval))

    def update_states(self, checked):
        self.idle_threshold_spin.setEnabled(checked)
        self.warning_duration_spin.setEnabled(checked)
        self.auto_resume_cb.setEnabled(checked)
        
        # Smart reminders state
        self.smart_interval_spin.setEnabled(self.smart_enabled_cb.isChecked())

    def save_settings(self):
        self.storage.save_setting("idle_enabled", self.idle_enabled_cb.isChecked())
        self.storage.save_setting("idle_threshold", self.idle_threshold_spin.value())
        self.storage.save_setting("idle_warning_sec", self.warning_duration_spin.value())
        self.storage.save_setting("idle_auto_resume", self.auto_resume_cb.isChecked())
        
        self.storage.save_setting("smart_enabled", self.smart_enabled_cb.isChecked())
        self.storage.save_setting("smart_interval", self.smart_interval_spin.value())
        
        self.accept()
