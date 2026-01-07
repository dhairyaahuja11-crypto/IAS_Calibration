from PyQt6.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QComboBox, QSpinBox, QRadioButton, QGridLayout
)
from PyQt6.QtCore import Qt, QDateTime


class DLPTestDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data Scanning - DLP Test")
        self.resize(1150, 680)
        self.setModal(True)
        self.build_ui()

    def build_ui(self):
        main_layout = QHBoxLayout(self)

        # ---------------- LEFT: Spectrogram ----------------
        left_layout = QVBoxLayout()

        title = QLabel("spectrogram")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:18px; font-weight:bold;")

        plot_area = QLabel("Plot Area")
        plot_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plot_area.setStyleSheet("border:1px solid #999; background:white;")
        plot_area.setMinimumSize(750, 520)

        left_layout.addWidget(title)
        left_layout.addWidget(plot_area)

        main_layout.addLayout(left_layout, 4)

        # ---------------- RIGHT PANEL ----------------
        right_layout = QVBoxLayout()

        # Scanning detail
        detail_box = QGroupBox("scanning detail")
        detail_layout = QVBoxLayout(detail_box)
        detail_layout.addWidget(QLabel("sample name:"))
        detail_layout.addWidget(QLabel("scanning method:"))
        detail_layout.addWidget(QLabel("sample qu: 10"))
        detail_layout.addWidget(QLabel("scanned number:"))
        right_layout.addWidget(detail_box)

        # Controls
        form = QGridLayout()

        form.addWidget(QLabel("choose instrument"), 0, 0)
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(["5100", "5200"])
        form.addWidget(self.instrument_combo, 0, 1)

        form.addWidget(QLabel("start time"), 1, 0)
        self.start_time = QSpinBox()
        form.addWidget(self.start_time, 1, 1)

        form.addWidget(QLabel("end time"), 2, 0)
        self.end_time = QSpinBox()
        form.addWidget(self.end_time, 2, 1)

        form.addWidget(QLabel("number of models"), 3, 0)
        self.model_spin = QSpinBox()
        self.model_spin.setMinimum(1)
        form.addWidget(self.model_spin, 3, 1)

        right_layout.addLayout(form)

        # Reference options
        ref_box = QGroupBox()
        ref_layout = QVBoxLayout(ref_box)

        self.rb_last = QRadioButton("use last reference")
        self.rb_rescan = QRadioButton("rescan the reference")
        self.rb_last.setChecked(True)

        ref_layout.addWidget(self.rb_last)
        ref_layout.addWidget(self.rb_rescan)

        right_layout.addWidget(ref_box)

        # Buttons
        btn_layout = QGridLayout()

        self.btn_ref = QPushButton("reference\nscanning")
        self.btn_sample = QPushButton("sample\nscanning")
        self.btn_clear = QPushButton("clear")
        self.btn_eval = QPushButton("stability\nevaluation")

        btn_layout.addWidget(self.btn_ref, 0, 0)
        btn_layout.addWidget(self.btn_sample, 0, 1)
        btn_layout.addWidget(self.btn_clear, 1, 0)
        btn_layout.addWidget(self.btn_eval, 1, 1)

        right_layout.addLayout(btn_layout)
        right_layout.addStretch()

        main_layout.addLayout(right_layout, 2)
