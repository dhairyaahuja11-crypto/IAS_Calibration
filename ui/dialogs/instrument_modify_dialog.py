from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout
)


class InstrumentModifyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("instrument information")
        self.resize(650, 420)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        grid = QGridLayout()

        # -------- LEFT COLUMN --------
        grid.addWidget(QLabel("instrument name:"), 0, 0)
        self.instrument_name = QLineEdit("5100")
        grid.addWidget(self.instrument_name, 0, 1)

        grid.addWidget(QLabel("instrument ID:"), 1, 0)
        self.instrument_id = QLineEdit("5100")
        grid.addWidget(self.instrument_id, 1, 1)

        grid.addWidget(QLabel("instrument type:"), 2, 0)
        self.instrument_type = QComboBox()
        self.instrument_type.addItems(["DLP"])
        grid.addWidget(self.instrument_type, 2, 1)

        grid.addWidget(QLabel("instrument type:"), 3, 0)
        self.instrument_form = QComboBox()
        self.instrument_form.addItems(["hand-held"])
        grid.addWidget(self.instrument_form, 3, 1)

        grid.addWidget(QLabel("wavelength points:"), 4, 0)
        self.wavelength_points = QSpinBox()
        self.wavelength_points.setValue(801)
        grid.addWidget(self.wavelength_points, 4, 1)

        grid.addWidget(QLabel("average number:"), 5, 0)
        self.avg_number = QSpinBox()
        self.avg_number.setValue(90)
        grid.addWidget(self.avg_number, 5, 1)

        grid.addWidget(QLabel("exposure time:"), 6, 0)
        self.exposure_time = QDoubleSpinBox()
        self.exposure_time.setDecimals(3)
        self.exposure_time.setValue(0.635)
        grid.addWidget(self.exposure_time, 6, 1)

        # -------- RIGHT COLUMN --------
        grid.addWidget(QLabel("sample type:"), 0, 2)
        self.sample_type = QComboBox()
        self.sample_type.addItems(["solid", "liquid", "powder"])
        grid.addWidget(self.sample_type, 0, 3)

        grid.addWidget(QLabel("workflow selection:"), 1, 2)
        self.workflow = QComboBox()
        self.workflow.addItems(["default"])
        grid.addWidget(self.workflow, 1, 3)

        grid.addWidget(QLabel("initial wavelength:"), 2, 2)
        self.initial_wave = QSpinBox()
        self.initial_wave.setValue(900)
        grid.addWidget(self.initial_wave, 2, 3)

        grid.addWidget(QLabel("terminal wavelength:"), 3, 2)
        self.terminal_wave = QSpinBox()
        self.terminal_wave.setValue(1700)
        grid.addWidget(self.terminal_wave, 3, 3)

        grid.addWidget(QLabel("resolution:"), 4, 2)
        self.resolution = QDoubleSpinBox()
        self.resolution.setValue(12.87)
        grid.addWidget(self.resolution, 4, 3)

        grid.addWidget(QLabel("light source mode:"), 5, 2)
        self.light_source = QComboBox()
        self.light_source.addItems(["build in"])
        grid.addWidget(self.light_source, 5, 3)

        self.turntable = QCheckBox("turntable enable")
        grid.addWidget(self.turntable, 6, 3)

        main_layout.addLayout(grid)

        # -------- BUTTONS --------
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("cancel")

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)

        main_layout.addLayout(btn_layout)