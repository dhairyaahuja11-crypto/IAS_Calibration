from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QSpinBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget,
    QSplitter, QFrame
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg


class DataSelectionUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ================= TOP FILTER / CONTROL AREA =================
        top_layout = QGridLayout()

        # Project
        top_layout.addWidget(QLabel("Project:"), 0, 0)
        self.project_cb = QComboBox()
        top_layout.addWidget(self.project_cb, 0, 1)

        # Sample list label (placeholder)
        top_layout.addWidget(QLabel("Sample list:"), 0, 2, 1, 4)

        # Instrument + OK
        top_layout.addWidget(QLabel("Instrument:"), 1, 0)
        self.instrument_cb = QComboBox()
        top_layout.addWidget(self.instrument_cb, 1, 1)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.setFixedWidth(60)
        top_layout.addWidget(self.ok_btn, 1, 2)

        main_layout.addLayout(top_layout)

        # ================= ACTION BUTTON BAR =================
        action_layout = QHBoxLayout()

        for text in [
            "Select All",
            "Set as Calibration",
            "Set as Validation",
            "Invalidation"
        ]:
            action_layout.addWidget(QPushButton(text))

        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        # ================= DATA + PLOT AREA =================
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # -------- LEFT: TABLE --------
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Sample Name",
            "Instrument",
            "Serial Number",
            "Wavelength Points",
            "Wavelength",
            "Absorbance",
            "Creation Time"
        ])
        splitter.addWidget(self.table)

        # -------- RIGHT: CONTROL + PLOT --------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Measurement controls
        measure_frame = QFrame()
        measure_layout = QGridLayout(measure_frame)

        measure_layout.addWidget(QLabel("Measurement index:"), 0, 0)

        self.index_cb = QComboBox()
        self.index_cb.addItems(["leverage value"])
        measure_layout.addWidget(self.index_cb, 0, 1)

        measure_layout.addWidget(QLabel("Contribution rate:"), 1, 0)
        self.contrib_spin = QSpinBox()
        self.contrib_spin.setRange(0, 100)
        self.contrib_spin.setValue(80)
        measure_layout.addWidget(self.contrib_spin, 1, 1)

        self.invalidation_btn = QPushButton("Invalidation")
        measure_layout.addWidget(self.invalidation_btn, 0, 2, 2, 1)

        # Sorting / selection
        self.order_cb = QComboBox()
        self.order_cb.addItems(["ascending", "descending"])
        measure_layout.addWidget(self.order_cb, 0, 3)

        measure_layout.addWidget(QLabel("Each sample from"), 1, 3)
        self.from_spin = QSpinBox()
        self.from_spin.setValue(0)
        measure_layout.addWidget(self.from_spin, 1, 4)

        measure_layout.addWidget(QLabel("start, get"), 1, 5)
        self.count_spin = QSpinBox()
        self.count_spin.setValue(10)
        measure_layout.addWidget(self.count_spin, 1, 6)

        measure_layout.addWidget(QLabel("number of data"), 1, 7)

        self.select_data_btn = QPushButton("Select Data")
        measure_layout.addWidget(self.select_data_btn, 0, 4, 1, 2)

        right_layout.addWidget(measure_frame)

        # Averaging controls
        avg_layout = QHBoxLayout()
        avg_layout.addWidget(QLabel("Data averaged into one"))
        self.avg_spin = QSpinBox()
        self.avg_spin.setValue(5)
        avg_layout.addWidget(self.avg_spin)
        avg_layout.addWidget(QPushButton("Average"))
        avg_layout.addWidget(QPushButton("OK"))
        avg_layout.addStretch()
        right_layout.addLayout(avg_layout)

        # Plot
        self.plot = pg.PlotWidget(title="wavelength-absorbance spectrogram")
        self.plot.setLabel("left", "absorbance(AU)")
        self.plot.setLabel("bottom", "wavelength")
        self.plot.showGrid(x=True, y=True)
        right_layout.addWidget(self.plot)

        splitter.addWidget(right_widget)
        splitter.setSizes([800, 600])

        main_layout.addWidget(splitter)
