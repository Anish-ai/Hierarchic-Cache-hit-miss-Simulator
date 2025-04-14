import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QComboBox, QSpinBox, QPushButton, QTabWidget,
                            QGridLayout, QGroupBox, QSplitter, QTableWidget, QTableWidgetItem,
                            QHeaderView, QProgressBar, QDoubleSpinBox, QStyleFactory, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QCoreApplication, QPropertyAnimation, QEasingCurve, QSize, QTimer
from PyQt5.QtGui import QColor, QPalette, QFont, QIcon

from cache_simulator import Cache, CacheHierarchy
from workload_generator import WorkloadGenerator

class SimulationWorker(QThread):
    """Thread for running cache simulations without blocking the UI"""
    progress_update = pyqtSignal(int)
    simulation_complete = pyqtSignal(dict)
    
    def __init__(self, cache_hierarchy, workload):
        super().__init__()
        self.cache_hierarchy = cache_hierarchy
        self.workload = workload
    
    def run(self):
        """Run the simulation"""
        total = len(self.workload)
        
        # Reset cache statistics
        self.cache_hierarchy.reset_stats()
        
        # Emit initial progress
        self.progress_update.emit(0)
        
        # Process in smaller chunks to allow UI updates
        chunk_size = max(1, min(1000, total // 100))
        last_progress = 0
        
        for i, address in enumerate(self.workload):
            self.cache_hierarchy.access(address)
            
            # Update progress more frequently
            current_progress = int(i / total * 100)
            if current_progress > last_progress or i % chunk_size == 0:
                last_progress = current_progress
                self.progress_update.emit(current_progress)
                # Process pending events to ensure UI updates
                QCoreApplication.processEvents()
        
        # Final update
        self.progress_update.emit(100)
        
        # Return results
        self.simulation_complete.emit(self.cache_hierarchy.get_stats())

class CacheBarChart(FigureCanvas):
    """Bar chart for hit/miss rates"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        plt.style.use('ggplot')  # Use a professional style
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Set background color
        self.fig.patch.set_facecolor('#f0f0f0')
        
        # Animation settings
        self.animation_speed = 25  # ms
        self.animation_current_height = 0
        self.animation_timer = None
    
    def update_chart(self, stats):
        """Update the chart with new statistics"""
        self.axes.clear()
        
        # Extract hit rates for each cache level
        cache_levels = ["L1", "L2", "L3"]
        hit_rates = [stats[level]["hit_rate"] for level in cache_levels]
        miss_rates = [stats[level]["miss_rate"] for level in cache_levels]
        
        # Calculate maximum for y-axis (ensuring bars don't touch roof)
        max_value = max(max(hit_rates), max(miss_rates))
        y_max = max(100, min(120, max_value * 1.2))  # 20% padding, max 120%
        
        # Set up bar positions
        x = np.arange(len(cache_levels))
        width = 0.35
        
        # Professional color palette
        hit_color = '#2C7BB6'  # Blue
        miss_color = '#D7191C'  # Red
        
        # Create bars with professional styling
        self.hit_bars = self.axes.bar(
            x - width/2, [0, 0, 0], width, 
            label='Hit Rate (%)', color=hit_color, 
            edgecolor='white', linewidth=0.7, alpha=0.8
        )
        self.miss_bars = self.axes.bar(
            x + width/2, [0, 0, 0], width, 
            label='Miss Rate (%)', color=miss_color, 
            edgecolor='white', linewidth=0.7, alpha=0.8
        )
        
        # Style improvements
        self.axes.set_ylabel('Percentage (%)', fontsize=10, fontweight='bold')
        self.axes.set_title('Cache Hit/Miss Rates', fontsize=12, fontweight='bold', pad=10)
        self.axes.set_xticks(x)
        self.axes.set_xticklabels(cache_levels, fontsize=10, fontweight='bold')
        self.axes.set_ylim(0, y_max)
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        self.axes.legend(fontsize=9, frameon=True, framealpha=0.7, loc='upper right')
        
        # Grid styling
        self.axes.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Start animation
        self.target_heights = hit_rates + miss_rates
        self.start_animation()
        
        self.fig.tight_layout()
        self.draw()
    
    def start_animation(self):
        """Animate the bars growing from 0 to their target heights"""
        # Reset animation state
        self.animation_current_height = 0
        
        if hasattr(self, 'animation_timer') and self.animation_timer is not None:
            self.animation_timer.stop()
        
        # Create timer for animation
        self.animation_timer = self.startTimer(self.animation_speed)
    
    def timerEvent(self, event):
        """Handle timer events for animation"""
        if not hasattr(self, 'target_heights') or not hasattr(self, 'hit_bars') or not hasattr(self, 'miss_bars'):
            self.killTimer(event.timerId())
            return
            
        self.animation_current_height += 5  # Increment by 5% each step
        
        target_hit_rates = self.target_heights[:3]
        target_miss_rates = self.target_heights[3:]
        
        # Calculate current heights based on animation progress
        current_hit_rates = [min(h, self.animation_current_height) for h in target_hit_rates]
        current_miss_rates = [min(h, self.animation_current_height) for h in target_miss_rates]
        
        # Update bar heights
        for bar, h in zip(self.hit_bars, current_hit_rates):
            bar.set_height(h)
        
        for bar, h in zip(self.miss_bars, current_miss_rates):
            bar.set_height(h)
        
        self.draw()
        
        # Check if animation is complete
        if self.animation_current_height >= max(self.target_heights):
            self.killTimer(event.timerId())
            self.animation_timer = None

class CacheAccessChart(FigureCanvas):
    """Chart for cache accesses visualization"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        plt.style.use('ggplot')  # Use a professional style
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Set background color
        self.fig.patch.set_facecolor('#f0f0f0')
        
        # Animation settings
        self.animation_speed = 25  # ms
        self.animation_current_height = 0
        self.animation_timer = None
    
    def update_chart(self, stats):
        """Update the chart with new statistics"""
        self.axes.clear()
        
        # Extract access counts
        cache_levels = ["L1", "L2", "L3"]
        accesses = [stats[level]["accesses"] for level in cache_levels]
        hits = [stats[level]["hits"] for level in cache_levels]
        
        # Calculate maximum for y-axis (ensuring bars don't touch roof)
        max_value = max(max(accesses), max(hits))
        y_max = max_value * 1.2  # 20% padding
        
        # Set up bar positions
        x = np.arange(len(cache_levels))
        width = 0.35
        
        # Professional color palette
        access_color = '#1B9E77'  # Teal
        hit_color = '#7570B3'     # Purple
        
        # Create bars with professional styling
        self.access_bars = self.axes.bar(
            x - width/2, [0, 0, 0], width, 
            label='Accesses', color=access_color, 
            edgecolor='white', linewidth=0.7, alpha=0.8
        )
        self.hit_bars = self.axes.bar(
            x + width/2, [0, 0, 0], width, 
            label='Hits', color=hit_color, 
            edgecolor='white', linewidth=0.7, alpha=0.8
        )
        
        # Style improvements
        self.axes.set_ylabel('Count', fontsize=10, fontweight='bold')
        self.axes.set_title('Cache Accesses and Hits', fontsize=12, fontweight='bold', pad=10)
        self.axes.set_xticks(x)
        self.axes.set_xticklabels(cache_levels, fontsize=10, fontweight='bold')
        self.axes.set_ylim(0, y_max)
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        self.axes.legend(fontsize=9, frameon=True, framealpha=0.7, loc='upper right')
        
        # Format y-axis with K for thousands
        if max_value > 1000:
            from matplotlib.ticker import FuncFormatter
            def format_k(x, pos):
                return f'{x/1000:.0f}K' if x >= 1000 else f'{x:.0f}'
            self.axes.yaxis.set_major_formatter(FuncFormatter(format_k))
        
        # Grid styling
        self.axes.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Start animation
        self.target_heights = accesses + hits
        self.start_animation()
        
        self.fig.tight_layout()
        self.draw()
    
    def start_animation(self):
        """Animate the bars growing from 0 to their target heights"""
        # Reset animation state
        self.animation_current_height = 0
        
        if hasattr(self, 'animation_timer') and self.animation_timer is not None:
            self.animation_timer.stop()
            
        # Create timer for animation
        self.animation_timer = self.startTimer(self.animation_speed)
    
    def timerEvent(self, event):
        """Handle timer events for animation"""
        if not hasattr(self, 'target_heights') or not hasattr(self, 'access_bars') or not hasattr(self, 'hit_bars'):
            self.killTimer(event.timerId())
            return
            
        if max(self.target_heights) == 0:
            self.killTimer(event.timerId())
            return
            
        # Calculate animation increment based on max value
        increment = max(self.target_heights) / 20  # Complete in ~20 steps
        self.animation_current_height += increment
        
        target_accesses = self.target_heights[:3]
        target_hits = self.target_heights[3:]
        
        # Calculate current heights based on animation progress
        current_accesses = [min(h, self.animation_current_height) for h in target_accesses]
        current_hits = [min(h, self.animation_current_height) for h in target_hits]
        
        # Update bar heights
        for bar, h in zip(self.access_bars, current_accesses):
            bar.set_height(h)
        
        for bar, h in zip(self.hit_bars, current_hits):
            bar.set_height(h)
        
        self.draw()
        
        # Check if animation is complete
        if self.animation_current_height >= max(self.target_heights):
            self.killTimer(event.timerId())
            self.animation_timer = None

class AnimatedProgressBar(QProgressBar):
    """Progress bar with animation effects"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 4px;
                text-align: center;
                background-color: #f0f0f0;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                                stop:0 #2196F3, stop:1 #00BCD4);
                border-radius: 3px;
            }
        """)
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.setDuration(600)  # 600ms animation
    
    def setValue(self, value):
        """Animate the progress change"""
        if self._animation.state() == QPropertyAnimation.Running:
            self._animation.stop()
        
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(value)
        self._animation.start()

class StyledButton(QPushButton):
    """Button with hover effects and animations"""
    def __init__(self, text, parent=None, primary=False):
        super().__init__(text, parent)
        self.primary = primary
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        
        # Apply initial styling
        self.updateStyle()
        
        # Size effects
        self.size_animation = QPropertyAnimation(self, b"size")
        self.size_animation.setDuration(100)
        
    def updateStyle(self):
        """Update button styling based on state"""
        if self.primary:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1E88E5;
                }
                QPushButton:pressed {
                    background-color: #1976D2;
                }
                QPushButton:disabled {
                    background-color: #90CAF9;
                    color: #E1F5FE;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    color: #424242;
                    border: 1px solid #bdbdbd;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #bdbdbd;
                }
                QPushButton:disabled {
                    background-color: #f5f5f5;
                    color: #9e9e9e;
                    border: 1px solid #e0e0e0;
                }
            """)
    
    def enterEvent(self, event):
        """Handle mouse enter event for hover effect"""
        self.size_animation.setStartValue(self.size())
        self.size_animation.setEndValue(QSize(int(self.width() * 1.05), int(self.height() * 1.05)))
        self.size_animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave event for hover effect"""
        self.size_animation.setStartValue(self.size())
        self.size_animation.setEndValue(QSize(int(self.width() / 1.05), int(self.height() / 1.05)))
        self.size_animation.start()
        super().leaveEvent(event)

class StyledGroupBox(QGroupBox):
    """GroupBox with enhanced styling"""
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bdbdbd;
                border-radius: 6px;
                margin-top: 12px;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: #fafafa;
            }
        """)

class CacheAnalyzerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cache Hierarchy Analyzer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set application style
        QApplication.setStyle(QStyleFactory.create('Fusion'))
        
        # Set application-wide palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, QColor(66, 66, 66))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.Text, QColor(66, 66, 66))
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, QColor(66, 66, 66))
        palette.setColor(QPalette.Highlight, QColor(33, 150, 243))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        QApplication.setPalette(palette)
        
        # Set global font
        font = QFont("Segoe UI", 9)
        QApplication.setFont(font)
        
        # Initialize with default cache parameters
        self.l1_params = {
            "size_kb": 32,
            "block_size_bytes": 64,
            "associativity": 8,
            "replacement_policy": "LRU"
        }
        
        self.l2_params = {
            "size_kb": 256,
            "block_size_bytes": 64,
            "associativity": 8,
            "replacement_policy": "LRU"
        }
        
        self.l3_params = {
            "size_kb": 8192,  # 8MB
            "block_size_bytes": 64,
            "associativity": 16,
            "replacement_policy": "LRU"
        }
        
        # Create cache hierarchy with default parameters
        self.cache_hierarchy = CacheHierarchy(
            self.l1_params, self.l2_params, self.l3_params
        )
        
        # Create workload generator
        self.workload_generator = WorkloadGenerator(memory_size_kb=16384)  # 16MB
        self.current_workload = []
        
        # Create the main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Create UI components with fade-in animation
        self.ui_components = []
        self._create_config_panel()
        self._create_workload_panel()
        self._create_visualization_panel()
        self._create_stats_panel()
        
        # Animate UI components appearing
        self._animate_ui_appearance()
        
        # Initialize worker
        self.simulation_worker = None
    
    def _animate_ui_appearance(self):
        """Animate the UI components appearing one after another"""
        duration = 250  # ms per component
        
        for i, component in enumerate(self.ui_components):
            effect = QGraphicsOpacityEffect(component)
            component.setGraphicsEffect(effect)
            
            # Create animation
            animation = QPropertyAnimation(effect, b"opacity")
            animation.setDuration(duration)
            animation.setStartValue(0)
            animation.setEndValue(1)
            animation.setEasingCurve(QEasingCurve.InOutQuad)
            
            # Start after a delay based on component index
            QTimer.singleShot(i * duration, animation.start)
    
    def _create_config_panel(self):
        """Create the cache configuration panel"""
        config_group = StyledGroupBox("Cache Configuration")
        config_layout = QGridLayout()
        config_layout.setVerticalSpacing(10)
        config_layout.setHorizontalSpacing(20)
        
        # Create cache configuration widgets for each level
        cache_levels = ["L1", "L2", "L3"]
        params = [self.l1_params, self.l2_params, self.l3_params]
        
        # Add headers
        headers = ["Cache Level", "Size (KB)", "Block Size (B)", "Associativity", "Replacement Policy"]
        for col, header in enumerate(headers):
            label = QLabel(header)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-weight: bold; color: #424242;")
            config_layout.addWidget(label, 0, col)
        
        # Add configuration widgets for each cache level
        for row, (level, param) in enumerate(zip(cache_levels, params), 1):
            # Cache level label
            label = QLabel(level)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(f"font-weight: bold; color: #1565C0; background-color: #E3F2FD; padding: 5px; border-radius: 3px;")
            config_layout.addWidget(label, row, 0)
            
            # Size spinner
            size_spinner = QSpinBox()
            size_spinner.setRange(1, 16384)  # 1KB to 16MB
            size_spinner.setValue(param["size_kb"])
            size_spinner.setObjectName(f"{level.lower()}_size")
            size_spinner.valueChanged.connect(self._update_cache_config)
            size_spinner.setStyleSheet("""
                QSpinBox {
                    padding: 5px;
                    border: 1px solid #bdbdbd;
                    border-radius: 3px;
                }
            """)
            config_layout.addWidget(size_spinner, row, 1)
            
            # Block size spinner
            block_spinner = QSpinBox()
            block_spinner.setRange(16, 256)  # 16B to 256B
            block_spinner.setSingleStep(16)
            block_spinner.setValue(param["block_size_bytes"])
            block_spinner.setObjectName(f"{level.lower()}_block_size")
            block_spinner.valueChanged.connect(self._update_cache_config)
            block_spinner.setStyleSheet("""
                QSpinBox {
                    padding: 5px;
                    border: 1px solid #bdbdbd;
                    border-radius: 3px;
                }
            """)
            config_layout.addWidget(block_spinner, row, 2)
            
            # Associativity spinner
            assoc_spinner = QSpinBox()
            assoc_spinner.setRange(1, 32)  # 1-way to 32-way
            assoc_spinner.setValue(param["associativity"])
            assoc_spinner.setObjectName(f"{level.lower()}_associativity")
            assoc_spinner.valueChanged.connect(self._update_cache_config)
            assoc_spinner.setStyleSheet("""
                QSpinBox {
                    padding: 5px;
                    border: 1px solid #bdbdbd;
                    border-radius: 3px;
                }
            """)
            config_layout.addWidget(assoc_spinner, row, 3)
            
            # Replacement policy combobox
            policy_combo = QComboBox()
            policy_combo.addItems(["LRU", "FIFO", "Random"])
            policy_combo.setCurrentText(param["replacement_policy"])
            policy_combo.setObjectName(f"{level.lower()}_replacement_policy")
            policy_combo.currentTextChanged.connect(self._update_cache_config)
            policy_combo.setStyleSheet("""
                QComboBox {
                    padding: 5px;
                    border: 1px solid #bdbdbd;
                    border-radius: 3px;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 20px;
                    border-left: 1px solid #bdbdbd;
                }
            """)
            config_layout.addWidget(policy_combo, row, 4)
        
        config_group.setLayout(config_layout)
        self.main_layout.addWidget(config_group)
        self.ui_components.append(config_group)
    
    def _create_workload_panel(self):
        """Create the workload generation panel"""
        workload_group = StyledGroupBox("Workload Configuration")
        workload_layout = QGridLayout()
        workload_layout.setVerticalSpacing(10)
        workload_layout.setHorizontalSpacing(20)
        
        # Workload type
        workload_layout.addWidget(QLabel("Workload Type:"), 0, 0)
        self.workload_type = QComboBox()
        self.workload_type.addItems([
            "Sequential", "Random", "Locality", 
            "Matrix (Row-Major)", "Matrix (Column-Major)", "Loop Nest"
        ])
        self.workload_type.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #bdbdbd;
                border-radius: 3px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #bdbdbd;
            }
        """)
        workload_layout.addWidget(self.workload_type, 0, 1)
        
        # Number of memory accesses
        workload_layout.addWidget(QLabel("Number of Accesses:"), 0, 2)
        self.num_accesses = QSpinBox()
        self.num_accesses.setRange(1000, 10000000)
        self.num_accesses.setSingleStep(10000)
        self.num_accesses.setValue(100000)
        self.num_accesses.setStyleSheet("""
            QSpinBox {
                padding: 5px;
                border: 1px solid #bdbdbd;
                border-radius: 3px;
            }
        """)
        workload_layout.addWidget(self.num_accesses, 0, 3)
        
        # Generate workload button
        self.generate_button = StyledButton("Generate Workload")
        self.generate_button.clicked.connect(self._generate_workload)
        workload_layout.addWidget(self.generate_button, 0, 4)
        
        # Run simulation button
        self.run_button = StyledButton("Run Simulation", primary=True)
        self.run_button.clicked.connect(self._run_simulation)
        self.run_button.setEnabled(False)  # Disabled until workload is generated
        workload_layout.addWidget(self.run_button, 0, 5)
        
        # Progress bar
        workload_layout.addWidget(QLabel("Progress:"), 1, 0)
        self.progress_bar = AnimatedProgressBar()
        workload_layout.addWidget(self.progress_bar, 1, 1, 1, 5)
        
        workload_group.setLayout(workload_layout)
        self.main_layout.addWidget(workload_group)
        self.ui_components.append(workload_group)
    
    def _create_visualization_panel(self):
        """Create the visualization panel with charts"""
        viz_group = StyledGroupBox("Visualization")
        viz_layout = QHBoxLayout()
        viz_layout.setSpacing(15)
        
        # Hit/miss rates chart
        self.hit_miss_chart = CacheBarChart(self.main_widget)
        viz_layout.addWidget(self.hit_miss_chart)
        
        # Access counts chart
        self.access_chart = CacheAccessChart(self.main_widget)
        viz_layout.addWidget(self.access_chart)
        
        viz_group.setLayout(viz_layout)
        self.main_layout.addWidget(viz_group)
        self.ui_components.append(viz_group)
    
    def _create_stats_panel(self):
        """Create the statistics panel"""
        stats_group = StyledGroupBox("Detailed Statistics")
        stats_layout = QVBoxLayout()
        
        # Create statistics table
        self.stats_table = QTableWidget(4, 5)  # 4 rows (L1, L2, L3, Overall), 5 columns
        self.stats_table.setHorizontalHeaderLabels(["Level", "Accesses", "Hits", "Misses", "Hit Rate (%)"])
        self.stats_table.setVerticalHeaderLabels(["L1", "L2", "L3", "Overall"])
        
        # Style the table
        self.stats_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                border: 1px solid #bdbdbd;
                border-radius: 3px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 5px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
        """)
        
        # Set default values
        for row in range(4):
            for col in range(5):
                item = QTableWidgetItem("0")
                item.setTextAlignment(Qt.AlignCenter)
                if col == 0:  # Cache level column
                    if row < 3:
                        item = QTableWidgetItem(f"L{row+1}")
                    else:
                        item = QTableWidgetItem("Overall")
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    item.setBackground(QColor("#E3F2FD"))
                self.stats_table.setItem(row, col, item)
        
        # Resize columns to contents
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        stats_layout.addWidget(self.stats_table)
        stats_group.setLayout(stats_layout)
        self.main_layout.addWidget(stats_group)
        self.ui_components.append(stats_group)
    
    def _update_cache_config(self):
        """Update cache configuration based on UI values"""
        sender = self.sender()
        if sender:
            name = sender.objectName()
            parts = name.split('_')
            if len(parts) >= 2:
                level = parts[0]  # l1, l2, or l3
                param = '_'.join(parts[1:])  # size, block_size, etc.
                
                if level == "l1":
                    target_params = self.l1_params
                elif level == "l2":
                    target_params = self.l2_params
                elif level == "l3":
                    target_params = self.l3_params
                
                if hasattr(sender, 'value'):
                    value = sender.value()
                else:
                    value = sender.currentText()
                
                if param == "size":
                    target_params["size_kb"] = value
                elif param == "block_size":
                    target_params["block_size_bytes"] = value
                elif param == "associativity":
                    target_params["associativity"] = value
                elif param == "replacement_policy":
                    target_params["replacement_policy"] = value
                
                # Recreate cache hierarchy with updated parameters
                self.cache_hierarchy = CacheHierarchy(
                    self.l1_params, self.l2_params, self.l3_params
                )
    
    def _generate_workload(self):
        """Generate a workload based on selected options"""
        workload_type = self.workload_type.currentText()
        num_accesses = self.num_accesses.value()
        
        # Generate the selected workload
        if workload_type == "Sequential":
            self.current_workload = self.workload_generator.generate_sequential(num_accesses)
        elif workload_type == "Random":
            self.current_workload = self.workload_generator.generate_random(num_accesses)
        elif workload_type == "Locality":
            self.current_workload = self.workload_generator.generate_locality(num_accesses)
        elif workload_type == "Matrix (Row-Major)":
            matrix_size = int(np.sqrt(num_accesses))
            self.current_workload = self.workload_generator.generate_matrix_traversal(
                matrix_size=matrix_size, row_major=True
            )
        elif workload_type == "Matrix (Column-Major)":
            matrix_size = int(np.sqrt(num_accesses))
            self.current_workload = self.workload_generator.generate_matrix_traversal(
                matrix_size=matrix_size, row_major=False
            )
        elif workload_type == "Loop Nest":
            self.current_workload = self.workload_generator.generate_loop_nest(
                iterations=num_accesses // 3  # 3 arrays accessed per iteration
            )
        
        self.run_button.setEnabled(True)
        self.progress_bar.setValue(0)
    
    def _run_simulation(self):
        """Run the cache simulation on the current workload"""
        if not self.current_workload:
            return
        
        # Disable buttons during simulation
        self.generate_button.setEnabled(False)
        self.run_button.setEnabled(False)
        
        # Reset and prepare progress bar
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 100)
        
        # Create worker thread
        self.simulation_worker = SimulationWorker(self.cache_hierarchy, self.current_workload)
        
        # Connect signals to slots, ensuring proper disconnection first
        try:
            self.simulation_worker.progress_update.disconnect()
        except:
            pass
        try:
            self.simulation_worker.simulation_complete.disconnect()
        except:
            pass
        
        # Connect signals
        self.simulation_worker.progress_update.connect(self.progress_bar.setValue)
        self.simulation_worker.simulation_complete.connect(self._update_results)
        
        # Start simulation
        self.simulation_worker.start()
    
    def _update_results(self, stats):
        """Update UI with simulation results"""
        # Update charts
        self.hit_miss_chart.update_chart(stats)
        self.access_chart.update_chart(stats)
        
        # Update statistics table
        for row, level in enumerate(["L1", "L2", "L3"]):
            level_stats = stats[level]
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(level_stats["accesses"])))
            self.stats_table.setItem(row, 2, QTableWidgetItem(str(level_stats["hits"])))
            self.stats_table.setItem(row, 3, QTableWidgetItem(str(level_stats["misses"])))
            self.stats_table.setItem(row, 4, QTableWidgetItem(f"{level_stats['hit_rate']:.2f}"))
        
        # Overall statistics
        total_accesses = stats["total_accesses"]
        total_hits = stats["L1"]["hits"] + stats["L2"]["hits"] + stats["L3"]["hits"]
        total_misses = total_accesses - total_hits
        overall_hit_rate = (total_hits / total_accesses * 100) if total_accesses > 0 else 0
        
        self.stats_table.setItem(3, 1, QTableWidgetItem(str(total_accesses)))
        self.stats_table.setItem(3, 2, QTableWidgetItem(str(total_hits)))
        self.stats_table.setItem(3, 3, QTableWidgetItem(str(total_misses)))
        self.stats_table.setItem(3, 4, QTableWidgetItem(f"{overall_hit_rate:.2f}"))
        
        # Re-enable buttons
        self.generate_button.setEnabled(True)
        self.run_button.setEnabled(True)
    
    def closeEvent(self, event):
        """Handle cleanup when closing the application"""
        # Stop simulation worker if running
        if self.simulation_worker and self.simulation_worker.isRunning():
            self.simulation_worker.terminate()
            self.simulation_worker.wait()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = CacheAnalyzerApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 