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

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ================= TOP CONTROL AREA =================
        top_layout = QHBoxLayout()

        # ---- Select model ----
        model_group = QGroupBox("select model")
        model_layout = QGridLayout(model_group)

        self.radio_current = QRadioButton("current\nproject")
        self.radio_current.setChecked(True)
        model_layout.addWidget(self.radio_current, 0, 0)

        self.current_model_edit = QLineEdit()
        model_layout.addWidget(self.current_model_edit, 0, 1)

        self.radio_history = QRadioButton("historical\nmodel")
        model_layout.addWidget(self.radio_history, 1, 0)

        self.history_model_combo = QComboBox()
        model_layout.addWidget(self.history_model_combo, 1, 1)

        top_layout.addWidget(model_group)

        # ---- Select data ----
        data_group = QGroupBox("select data")
        data_layout = QVBoxLayout(data_group)

        self.radio_cal = QRadioButton("calibration set")
        self.radio_cal.setChecked(True)
        self.radio_val = QRadioButton("validation set")
        self.radio_cross = QRadioButton("cross validation set")

        data_layout.addWidget(self.radio_cal)
        data_layout.addWidget(self.radio_val)
        data_layout.addWidget(self.radio_cross)

        top_layout.addWidget(data_group)

        # ---- Analysis algorithm ----
        algo_group = QGroupBox("analysis algorithm")
        algo_layout = QVBoxLayout(algo_group)

        algo_layout.addWidget(QLabel("select algorithm:"))

        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems([
            "PLS quantification",
            "SIMCA", "BP-NN qualitation", "BP-NN quantification","Fisher",
            "SVM qualitation","SVM quantification"
        ])
        algo_layout.addWidget(self.algorithm_combo)

        top_layout.addWidget(algo_group)

        # ---- Action buttons ----
        btn_layout = QVBoxLayout()
        btn_layout.addWidget(QPushButton("analysis"))
        btn_layout.addWidget(QPushButton("measurement"))
        btn_layout.addWidget(QPushButton("save model"))
        btn_layout.addStretch()

        top_layout.addLayout(btn_layout)

        top_layout.addStretch()
        main_layout.addLayout(top_layout)

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

        self.deviation_checkbox = QCheckBox("display deviation diagram")
        metrics_layout.addWidget(self.deviation_checkbox)

        metrics_layout.addSpacing(10)

        for label in [
            "SEC:", "SECV:", "SEP:", "RPD:", "E:",
            "R:", "R2:", "t:", "accuracy:", "recall:"
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(QLineEdit())
            metrics_layout.addLayout(row)

        metrics_layout.addStretch()

        middle_layout.addLayout(metrics_layout, 1)

        main_layout.addLayout(middle_layout)
    
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
