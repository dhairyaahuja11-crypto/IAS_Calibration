from PyQt6.QtWidgets import (
    QDialog, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGroupBox, QComboBox, QSpinBox, QRadioButton, QGridLayout
)
from PyQt6.QtCore import Qt


class DataScanningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Gather Data")
        self.resize(1100, 650)
        self.build_ui()

    def build_ui(self):
        main_layout = QHBoxLayout(self)

        # ---------------- LEFT: Spectrogram placeholder ----------------
        plot_container = QVBoxLayout()

        title = QLabel("spectrogram")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:18px; font-weight:bold;")

        plot_area = QLabel("Plot Area")
        plot_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plot_area.setStyleSheet(
            "border: 1px solid #999; background:#fff;"
        )
        plot_area.setMinimumSize(750, 520)

        plot_container.addWidget(title)
        plot_container.addWidget(plot_area)

        main_layout.addLayout(plot_container, 4)

        # ---------------- RIGHT PANEL ----------------
        right_layout = QVBoxLayout()

        # Scanning detail
        detail_box = QGroupBox("scanning detail")
        detail_layout = QVBoxLayout(detail_box)

        detail_layout.addWidget(QLabel("sample no:"))
        detail_layout.addWidget(QLabel("scanning method:"))
        detail_layout.addWidget(QLabel("sample qu: 10"))
        detail_layout.addWidget(QLabel("scanned number:"))

        right_layout.addWidget(detail_box)

        # Controls
        form = QGridLayout()

        form.addWidget(QLabel("select select"), 0, 0)
        self.select_combo = QComboBox()
        self.select_combo.addItems(["5100", "5200", "5300"])
        form.addWidget(self.select_combo, 0, 1)

        form.addWidget(QLabel("input batch"), 1, 0)
        self.batch_spin = QSpinBox()
        self.batch_spin.setMinimum(1)
        form.addWidget(self.batch_spin, 1, 1)

        form.addWidget(QLabel("quantity collected"), 2, 0)
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(0)
        form.addWidget(self.quantity_spin, 2, 1)

        right_layout.addLayout(form)

        # Reference selection
        ref_box = QGroupBox()
        ref_layout = QVBoxLayout(ref_box)

        self.rb_last = QRadioButton("use last reference")
        self.rb_rescan = QRadioButton("rescan the reference")
        self.rb_factory = QRadioButton("use factory reference")

        self.rb_last.setChecked(True)

        ref_layout.addWidget(self.rb_last)
        ref_layout.addWidget(self.rb_rescan)
        ref_layout.addWidget(self.rb_factory)

        right_layout.addWidget(ref_box)

        # Buttons
        btn_layout = QGridLayout()

        self.btn_ref = QPushButton("reference\nscanning")
        self.btn_sample = QPushButton("sample\nscanning")
        self.btn_clear = QPushButton("clear")
        self.btn_save = QPushButton("scan reference\ndata to file")

        btn_layout.addWidget(self.btn_ref, 0, 0)
        btn_layout.addWidget(self.btn_sample, 0, 1)
        btn_layout.addWidget(self.btn_clear, 1, 0)
        btn_layout.addWidget(self.btn_save, 1, 1)

        right_layout.addLayout(btn_layout)
        right_layout.addStretch()

        main_layout.addLayout(right_layout, 2)
