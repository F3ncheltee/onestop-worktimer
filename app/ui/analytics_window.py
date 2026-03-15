from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                               QWidget, QComboBox)
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
        self.resize(1000, 600)
        self.setStyleSheet("background-color: #f5f5f5;")
        
        self.storage = storage
        self.analytics = Analytics(storage)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)
        
        # --- Top Bar ---
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("<b>Time Range:</b>"))
        self.range_combo = QComboBox()
        self.range_combo.addItems(["Last 7 Days", "Last 14 Days", "Last 30 Days", "Last 90 Days"])
        self.range_combo.setCurrentIndex(1) # Default 14 days
        self.range_combo.currentIndexChanged.connect(self.refresh_charts)
        top_bar.addWidget(self.range_combo)
        top_bar.addStretch()
        self.layout.addLayout(top_bar)
        
        # --- KPI Section ---
        kpi_layout = QHBoxLayout()
        kpis = self.analytics.get_kpis()
        
        kpi_layout.addWidget(self.create_kpi_card("Today", kpis["today"], "#3498db"))
        kpi_layout.addWidget(self.create_kpi_card("This Week", kpis["week"], "#2ecc71"))
        kpi_layout.addWidget(self.create_kpi_card("This Month", kpis["month"], "#9b59b6"))
        kpi_layout.addWidget(self.create_kpi_card("All Time", kpis["all_time"], "#e67e22"))
        
        self.layout.addLayout(kpi_layout)
        
        # --- Chart Section ---
        chart_layout_main = QHBoxLayout()
        
        # Daily Hours Chart
        chart_frame = QFrame()
        chart_frame.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #ddd;")
        chart_layout = QVBoxLayout(chart_frame)
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        chart_layout.addWidget(self.canvas)
        chart_layout_main.addWidget(chart_frame, 2)
        
        # Project Breakdown Chart
        proj_frame = QFrame()
        proj_frame.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #ddd;")
        proj_layout = QVBoxLayout(proj_frame)
        self.proj_canvas = MplCanvas(self, width=4, height=4, dpi=100)
        proj_layout.addWidget(self.proj_canvas)
        chart_layout_main.addWidget(proj_frame, 1)
        
        self.layout.addLayout(chart_layout_main)
        
        self.refresh_charts()

    def refresh_charts(self):
        idx = self.range_combo.currentIndex()
        days_map = {0: 7, 1: 14, 2: 30, 3: 90}
        days = days_map.get(idx, 14)
        
        self.plot_data(days)
        self.plot_project_data(days)

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

    def plot_data(self, days=14):
        data = self.analytics.get_daily_hours(days=days)
        
        self.canvas.axes.clear()
        bars = self.canvas.axes.bar(data['dates'], data['hours'], color="#3498db")
        
        self.canvas.axes.set_title(f"Hours Worked (Last {days} Days)")
        self.canvas.axes.set_ylabel("Hours")
        
        # Rotate x-axis labels if there are many days
        if days > 14:
            self.canvas.axes.tick_params(axis='x', rotation=45)
        else:
            self.canvas.axes.tick_params(axis='x', rotation=0)
            
        # Style grid
        self.canvas.axes.grid(axis='y', linestyle='--', alpha=0.7)
        self.canvas.axes.set_axisbelow(True)
        
        self.canvas.fig.tight_layout()
        self.canvas.draw()

    def plot_project_data(self, days=30):
        data = self.analytics.get_project_hours(days=days)
        
        self.proj_canvas.axes.clear()
        
        if sum(data['hours']) == 0:
            self.proj_canvas.axes.text(0.5, 0.5, "No Data", ha='center', va='center')
        else:
            self.proj_canvas.axes.pie(data['hours'], labels=data['names'], colors=data['colors'], autopct='%1.1f%%', startangle=90)
            self.proj_canvas.axes.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
            
        self.proj_canvas.axes.set_title(f"Projects (Last {days} Days)")
        self.proj_canvas.fig.tight_layout()
        self.proj_canvas.draw()

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
