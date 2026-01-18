from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                               QWidget)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from app.core.storage import Storage
from app.core.analytics import Analytics

class AnalyticsWindow(QDialog):
    def __init__(self, storage: Storage, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analytics")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #f5f5f5;")
        
        self.storage = storage
        self.analytics = Analytics(storage)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)
        
        # --- KPI Section ---
        kpi_layout = QHBoxLayout()
        kpis = self.analytics.get_kpis()
        
        kpi_layout.addWidget(self.create_kpi_card("Today", kpis["today"], "#3498db"))
        kpi_layout.addWidget(self.create_kpi_card("This Week", kpis["week"], "#2ecc71"))
        kpi_layout.addWidget(self.create_kpi_card("This Month", kpis["month"], "#9b59b6"))
        
        self.layout.addLayout(kpi_layout)
        
        # --- Chart Section ---
        chart_frame = QFrame()
        chart_frame.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #ddd;")
        chart_layout = QVBoxLayout(chart_frame)
        
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        chart_layout.addWidget(self.canvas)
        
        self.layout.addWidget(chart_frame)
        
        self.plot_data()

    def create_kpi_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ 
                background-color: white; 
                border-left: 5px solid {color}; 
                border-radius: 5px;
                border: 1px solid #ddd;
            }}
        """)
        layout = QVBoxLayout(card)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #7f8c8d; font-size: 14px; border: none;")
        
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"color: #2c3e50; font-size: 24px; font-weight: bold; border: none;")
        
        layout.addWidget(title_lbl)
        layout.addWidget(val_lbl)
        return card

    def plot_data(self):
        data = self.analytics.get_daily_hours(days=14)
        
        self.canvas.axes.clear()
        bars = self.canvas.axes.bar(data['dates'], data['hours'], color="#3498db")
        
        self.canvas.axes.set_title("Hours Worked (Last 14 Days)")
        self.canvas.axes.set_ylabel("Hours")
        
        # Style grid
        self.canvas.axes.grid(axis='y', linestyle='--', alpha=0.7)
        self.canvas.axes.set_axisbelow(True)
        
        self.canvas.draw()

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
