from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QRadioButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QTableWidget, QTableWidgetItem, QCheckBox, QLineEdit
)
from PyQt6.QtCore import Qt


class AnalysisMeasureUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # ================= TOP CONTROL AREA =================
        top_layout = QHBoxLayout()
        top_layout.setSpacing(5)

        # ---- Select model ----
        model_group = QGroupBox("select model")
        model_group.setMaximumHeight(90)
        model_layout = QGridLayout(model_group)
        model_layout.setContentsMargins(5, 5, 5, 5)
        model_layout.setSpacing(3)

        self.radio_current = QRadioButton("current\nproject")
        self.radio_current.setChecked(True)
        model_layout.addWidget(self.radio_current, 0, 0)

        self.current_model_combo = QComboBox()
        self.current_model_combo.setMinimumWidth(120)
        self.current_model_combo.setMaximumHeight(25)
        model_layout.addWidget(self.current_model_combo, 0, 1)

        self.radio_history = QRadioButton("historical\nmodel")
        model_layout.addWidget(self.radio_history, 1, 0)

        self.history_model_combo = QComboBox()
        self.history_model_combo.setMinimumWidth(120)
        self.history_model_combo.setMaximumHeight(25)
        model_layout.addWidget(self.history_model_combo, 1, 1)

        top_layout.addWidget(model_group)

        # ---- Select data ----
        data_group = QGroupBox("select data")
        data_group.setMaximumHeight(90)
        data_layout = QVBoxLayout(data_group)
        data_layout.setContentsMargins(5, 5, 5, 5)
        data_layout.setSpacing(2)

        self.radio_cal = QRadioButton("calibration set")
        self.radio_cal.setChecked(True)
        self.radio_val = QRadioButton("validation set")
        self.radio_cross = QRadioButton("cross validation set")

        data_layout.addWidget(self.radio_cal)
        data_layout.addWidget(self.radio_val)
        data_layout.addWidget(self.radio_cross)

        top_layout.addWidget(data_group)

        # ---- Analysis algorithm ----
        algo_group = QGroupBox("analyse algorithm")
        algo_group.setMaximumHeight(90)
        algo_layout = QVBoxLayout(algo_group)
        algo_layout.setContentsMargins(5, 5, 5, 5)
        algo_layout.setSpacing(3)

        label = QLabel("select\nalgorithm:")
        label.setMaximumHeight(30)
        algo_layout.addWidget(label)

        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems([
            "PLS quantification",
            "SIMCA", "BP-NN qualitation", "BP-NN quantification","Fisher",
            "SVM qualitation","SVM quantification"
        ])
        self.algorithm_combo.setMinimumWidth(120)
        self.algorithm_combo.setMaximumHeight(25)
        algo_layout.addWidget(self.algorithm_combo)

        top_layout.addWidget(algo_group)

        # ---- Action buttons (horizontal layout) ----
        btn_group = QGroupBox()
        btn_group.setMaximumHeight(90)
        btn_layout = QVBoxLayout(btn_group)
        btn_layout.setContentsMargins(5, 5, 5, 5)
        btn_layout.setSpacing(3)
        
        self.analysis_btn = QPushButton("analysis")
        self.analysis_btn.setMaximumHeight(30)
        btn_layout.addWidget(self.analysis_btn)
        
        self.measure_btn = QPushButton("PLS quantification\nmeasure")
        self.measure_btn.setMaximumHeight(35)
        btn_layout.addWidget(self.measure_btn)
        
        self.save_model_btn = QPushButton("save model")
        self.save_model_btn.setMaximumHeight(30)
        btn_layout.addWidget(self.save_model_btn)
        
        btn_layout.addStretch()

        top_layout.addWidget(btn_group)
        top_layout.addStretch()
        main_layout.addLayout(top_layout, 0)  # Give 0 stretch to top layout

        # ================= MIDDLE AREA =================
        middle_layout = QHBoxLayout()

        # ---- Table ----
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "ID", "sample name", "serial number", "wavelength points",
            "wavelength", "absorbance", "creation time",
            "actual value", "measurement value", "relative error"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        
        # Install event filter to detect clicks on empty table space
        self.table.viewport().installEventFilter(self)

        middle_layout.addWidget(self.table, 5)

        # ---- Metrics panel ----
        metrics_layout = QVBoxLayout()
        metrics_layout.setSpacing(3)

        self.deviation_checkbox = QCheckBox("display deviation diagram")
        metrics_layout.addWidget(self.deviation_checkbox)

        metrics_layout.addSpacing(5)

        # Create metric fields as dictionary for easy access
        self.metric_fields = {}
        metric_labels = [
            ("SEC:", "sec"),
            ("SECV:", "secv"),
            ("SEP:", "sep"),
            ("RPD:", "rpd"),
            ("E:", "e"),
            ("R:", "r"),
            ("R2:", "r2"),
            ("t:", "t"),
            ("accuracy:", "accuracy"),
            ("recall:", "recall")
        ]
        
        for label_text, field_name in metric_labels:
            row = QHBoxLayout()
            row.setSpacing(3)
            label = QLabel(label_text)
            label.setMinimumWidth(70)
            label.setMaximumWidth(70)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(label)
            
            field = QLineEdit()
            field.setReadOnly(True)
            field.setMinimumWidth(100)
            field.setMaximumHeight(25)
            field.setStyleSheet("""
                QLineEdit {
                    background-color: white;
                    border: 1px solid #c0c0c0;
                    padding: 2px;
                }
            """)
            row.addWidget(field)
            self.metric_fields[field_name] = field
            
            metrics_layout.addLayout(row)

        metrics_layout.addStretch()

        middle_layout.addLayout(metrics_layout, 1)

        main_layout.addLayout(middle_layout, 1)  # Give 1 stretch to middle (expand to fill)
    
    def _connect_signals(self):
        """Connect signals to slots"""
        self.algorithm_combo.currentTextChanged.connect(self._on_algorithm_changed)
        self.analysis_btn.clicked.connect(self._on_analysis_clicked)
        self.measure_btn.clicked.connect(self._on_measure_clicked)
        self.save_model_btn.clicked.connect(self._on_save_model_clicked)
    
    def _on_algorithm_changed(self, algorithm):
        """Update measure button text based on selected algorithm"""
        if "quantification" in algorithm.lower():
            self.measure_btn.setText(f"{algorithm}\nmeasure")
        elif "qualitation" in algorithm.lower():
            self.measure_btn.setText(f"{algorithm}\nmeasure")
        else:
            self.measure_btn.setText(f"{algorithm}\nmeasure")
    
    def _on_analysis_clicked(self):
        """Handle analysis button click"""
        # TODO: Implement analysis logic
        pass
    
    def _on_measure_clicked(self):
        """Handle measure button click"""
        # TODO: Implement measurement logic
        pass
    
    def _on_save_model_clicked(self):
        """Handle save model button click"""
        # TODO: Implement save model logic
        pass
    
    def update_metrics(self, metrics_dict):
        """Update metric display fields
        
        Args:
            metrics_dict: Dictionary with metric names as keys and values as floats
                         e.g., {'sec': 0.153, 'r2': 0.426, ...}
        """
        for field_name, value in metrics_dict.items():
            if field_name in self.metric_fields:
                if value is not None:
                    self.metric_fields[field_name].setText(str(value))
                else:
                    self.metric_fields[field_name].clear()
    
    def keyPressEvent(self, event):
        """Handle key press events - Escape to clear selection"""
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Escape:
            self.table.clearSelection()
        else:
            super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        """Filter events to detect clicks on empty table space"""
        from PyQt6.QtCore import QEvent
        
        if obj == self.table.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            index = self.table.indexAt(event.pos())
            if not index.isValid():
                self.table.clearSelection()
                return True
        
        return super().eventFilter(obj, event)
