from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QSpinBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QRadioButton, QGroupBox
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg


class MeasurementDemoUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        self.setObjectName("measurementDemoRoot")
        self.setStyleSheet("""
            QWidget#measurementDemoRoot {
                background-color: #f6f8fb;
            }
            QLabel {
                color: #1f2937;
                font-size: 12px;
            }
            QComboBox, QSpinBox {
                background-color: #ffffff;
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QComboBox:focus, QSpinBox:focus {
                border: 1px solid #7aa7ff;
            }
            QPushButton {
                background-color: #ffffff;
                color: #1f2937;
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 30px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f2f6ff;
                border-color: #aac2ef;
            }
            QPushButton:pressed {
                background-color: #e7efff;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #d8e1eb;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #374151;
            }
        """)

        # ================= MAIN SPLITTER =================
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # ================= LEFT PANEL =================
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.result_area = QLabel(" ")
        self.result_area.setMinimumWidth(200)
        self.result_area.setStyleSheet(
            "background-color: #ffffff; border: 1px solid #d8e1eb; border-radius: 8px;"
        )
        left_layout.addWidget(self.result_area)

        export_btn = QPushButton("results\nexport")
        export_btn.setFixedSize(90, 40)
        left_layout.addWidget(export_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        splitter.addWidget(left_panel)

        # ================= RIGHT PANEL =================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # -------- Spectrogram --------
        plot = pg.PlotWidget(title="spectrogram")
        plot.setLabel("left", "absorbance(AU)")
        plot.setLabel("bottom", "wavelength(nm)")
        plot.showGrid(x=True, y=True)

        right_layout.addWidget(plot)

        # -------- Axis & Order Controls --------
        axis_layout = QHBoxLayout()

        axis_layout.addWidget(QRadioButton("wavenumber"))
        rb_wavelength = QRadioButton("wavelength")
        rb_wavelength.setChecked(True)
        axis_layout.addWidget(rb_wavelength)

        axis_layout.addStretch()

        rb_asc = QRadioButton("ascending")
        rb_asc.setChecked(True)
        axis_layout.addWidget(rb_asc)
        axis_layout.addWidget(QRadioButton("descending"))

        right_layout.addLayout(axis_layout)

        # ================= CONTROL PANEL =================
        control_layout = QGridLayout()

        # Model selection
        control_layout.addWidget(QLabel("model\nselection:"), 0, 0)
        model_cb = QComboBox()
        model_cb.addItem("Almond_Peroxide_23122")
        control_layout.addWidget(model_cb, 0, 1)

        # Number of scanning
        control_layout.addWidget(QLabel("number of\nscanning:"), 0, 2)
        scan_spin = QSpinBox()
        scan_spin.setRange(1, 100)
        scan_spin.setValue(1)
        control_layout.addWidget(scan_spin, 0, 3)

        # Instrument selection
        control_layout.addWidget(QLabel("instrument\nselection:"), 1, 0)
        instr_cb = QComboBox()
        instr_cb.addItem("3120")
        control_layout.addWidget(instr_cb, 1, 1)

        right_layout.addLayout(control_layout)

        # ================= SAMPLE TESTING =================
        test_group = QGroupBox("sample testing")
        test_layout = QGridLayout(test_group)

        test_layout.addWidget(QPushButton("reference\nscanning"), 0, 0)
        test_layout.addWidget(QPushButton("sample\nscanning"), 0, 1)
        test_layout.addWidget(QPushButton("file\npredict"), 0, 2)

        test_layout.addWidget(QPushButton("clear"), 1, 0)
        test_layout.addWidget(QPushButton("import file\nand predict"), 1, 1)
        test_layout.addWidget(QPushButton("export\nresults"), 1, 2)

        right_layout.addWidget(test_group)

        splitter.addWidget(right_panel)
        splitter.setSizes([250, 900])
