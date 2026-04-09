from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QPushButton,
    QGridLayout, QHBoxLayout, QCheckBox
)

class AddInstrumentDialog(QDialog):
    def __init__(self, creation_date, parent=None):
        super().__init__(parent)
        self.creation_date = creation_date
        self.setWindowTitle("Instrument Information")
        self._build_ui()

    def _build_ui(self):
        layout = QGridLayout(self)

        # Row 0
        layout.addWidget(QLabel("Instrument name:"), 0, 0)
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit, 0, 1)

        layout.addWidget(QLabel("Sample type:"), 0, 2)
        self.sample_type = QComboBox()
        self.sample_type.addItems(["solid", "liquid"])
        layout.addWidget(self.sample_type, 0, 3)

        # Row 1
        layout.addWidget(QLabel("Instrument ID:"), 1, 0)
        self.instrument_id = QLineEdit()
        layout.addWidget(self.instrument_id, 1, 1)

        layout.addWidget(QLabel("Workflow selection:"), 1, 2)
        self.workflow = QComboBox()
        self.workflow.addItems(["default"])
        layout.addWidget(self.workflow, 1, 3)

        # Row 2
        layout.addWidget(QLabel("Instrument type:"), 2, 0)
        self.instrument_type = QComboBox()
        self.instrument_type.addItems(["DLP", "FTIR"])
        layout.addWidget(self.instrument_type, 2, 1)

        layout.addWidget(QLabel("Initial wavelength:"), 2, 2)
        self.initial_wl = QSpinBox()
        self.initial_wl.setRange(200, 3000)
        self.initial_wl.setValue(900)
        layout.addWidget(self.initial_wl, 2, 3)

        # Row 3
        layout.addWidget(QLabel("Terminal wavelength:"), 3, 2)
        self.terminal_wl = QSpinBox()
        self.terminal_wl.setRange(200, 3000)
        self.terminal_wl.setValue(1700)
        layout.addWidget(self.terminal_wl, 3, 3)

        # Row 4
        layout.addWidget(QLabel("Wavelength points:"), 4, 0)
        self.points = QSpinBox()
        self.points.setRange(1, 5000)
        self.points.setValue(801)
        layout.addWidget(self.points, 4, 1)

        layout.addWidget(QLabel("Resolution:"), 4, 2)
        self.resolution = QDoubleSpinBox()
        self.resolution.setDecimals(2)
        self.resolution.setValue(2.34)
        layout.addWidget(self.resolution, 4, 3)

        # Row 5
        layout.addWidget(QLabel("Average number:"), 5, 0)
        self.avg_num = QSpinBox()
        self.avg_num.setValue(10)
        layout.addWidget(self.avg_num, 5, 1)

        layout.addWidget(QLabel("Light source mode:"), 5, 2)
        self.light_mode = QComboBox()
        self.light_mode.addItems(["build-in", "external"])
        layout.addWidget(self.light_mode, 5, 3)

        # Row 6
        self.turntable = QCheckBox("Turntable enable")
        layout.addWidget(self.turntable, 6, 3)

        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout, 7, 0, 1, 4)

    def get_data(self):
        return {
            "name": self.name_edit.text(),
            "instrument_id": self.instrument_id.text(),
            "sample_type": self.sample_type.currentText(),
            "workflow": self.workflow.currentText(),
            "instrument_type": self.instrument_type.currentText(),
            "initial_wl": self.initial_wl.value(),
            "terminal_wl": self.terminal_wl.value(),
            "points": self.points.value(),
            "resolution": self.resolution.value(),
            "avg_num": self.avg_num.value(),
            "light_mode": self.light_mode.currentText(),
            "turntable": self.turntable.isChecked(),
            "creation_date": self.creation_date
        }
