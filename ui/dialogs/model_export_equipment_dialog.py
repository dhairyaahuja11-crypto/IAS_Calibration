from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QSpinBox, QTableWidget
)
from PyQt6.QtCore import Qt


class ModelExportEquipmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Model Export")
        self.resize(1200, 700)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ================= TOP AREA =================
        top_layout = QHBoxLayout()

        # -------- Spectrometer Information --------
        spectro_box = QGroupBox("spectrometer information")
        spectro_layout = QGridLayout(spectro_box)

        spectro_layout.addWidget(QLabel("initial wavelength:"), 0, 0)
        spectro_layout.addWidget(QSpinBox(), 0, 1)

        spectro_layout.addWidget(QLabel("terminal wavelength:"), 0, 2)
        spectro_layout.addWidget(QSpinBox(), 0, 3)

        spectro_layout.addWidget(QLabel("resolution:"), 1, 0)
        spectro_layout.addWidget(QLineEdit("12.87"), 1, 1)

        spectro_layout.addWidget(QLabel("exposure time:"), 1, 2)
        spectro_layout.addWidget(QLineEdit("0.635"), 1, 3)

        spectro_layout.addWidget(QLabel("average number:"), 2, 0)
        spectro_layout.addWidget(QSpinBox(), 2, 1)

        spectro_layout.addWidget(QLabel("number of scanning:"), 2, 2)
        spectro_layout.addWidget(QSpinBox(), 2, 3)

        top_layout.addWidget(spectro_box, 2)

        # -------- Model Information --------
        model_box = QGroupBox("model information")
        model_layout = QGridLayout(model_box)

        model_layout.addWidget(QLabel("instrument type:"), 0, 0)
        instrument_combo = QComboBox()
        instrument_combo.addItems(["IAS5100", "IAS5200"])
        model_layout.addWidget(instrument_combo, 0, 1)

        model_layout.addWidget(QLabel("model name:"), 0, 2)
        model_layout.addWidget(QLineEdit(), 0, 3)

        model_layout.addWidget(QLabel("model abbreviation:"), 1, 0)
        model_layout.addWidget(QLineEdit(), 1, 1)

        model_layout.addWidget(QLabel("version:"), 1, 2)
        model_layout.addWidget(QLineEdit(), 1, 3)

        model_layout.addWidget(QLabel("remark:"), 2, 0)
        model_layout.addWidget(QLineEdit(), 2, 1, 1, 3)

        top_layout.addWidget(model_box, 3)

        # -------- Export Buttons --------
        btn_layout = QVBoxLayout()

        self.btn_export_official = QPushButton("export official\nversion")
        self.btn_export_normal = QPushButton("export normal\nversion")
        self.btn_rebuild = QPushButton("rebuild file")
        self.btn_language = QPushButton("add multi\nlanguages")

        for btn in [
            self.btn_export_official,
            self.btn_export_normal,
            self.btn_rebuild,
            self.btn_language
        ]:
            btn.setMinimumHeight(45)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        top_layout.addLayout(btn_layout, 1)

        main_layout.addLayout(top_layout)

        # ================= ID / ITEM AREA =================
        id_layout = QGridLayout()

        headers = [
            "ID", "item", "precision",
            "measurement range", "extreme difference"
        ]

        for col, text in enumerate(headers):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            id_layout.addWidget(lbl, 0, col)

        self.id_edit = QLineEdit("479")
        self.item_edit = QLineEdit("AIA")
        self.precision_edit = QLineEdit("1")
        self.range_edit = QLineEdit("100")
        self.extreme_edit = QLineEdit("4")

        id_layout.addWidget(self.id_edit, 1, 0)
        id_layout.addWidget(self.item_edit, 1, 1)
        id_layout.addWidget(self.precision_edit, 1, 2)
        id_layout.addWidget(self.range_edit, 1, 3)
        id_layout.addWidget(self.extreme_edit, 1, 4)

        main_layout.addLayout(id_layout)

        # ================= TABLE =================
        self.table = QTableWidget(0, 13)
        self.table.setHorizontalHeaderLabels([
            "model name", "model version", "model ID",
            "precision", "lower limit", "upper limit",
            "extreme difference", "instrument information",
            "average number", "number of scanning",
            "version type", "instrument type", "remark"
        ])

        main_layout.addWidget(self.table)
