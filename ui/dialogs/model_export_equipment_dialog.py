from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QSpinBox, QTableWidget, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt

from services.model_management_service import ModelManagementService
from utils.model_encryption import get_default_encryption_key, load_encrypted_model


class ModelExportEquipmentDialog(QDialog):
    def __init__(self, parent=None, model_path=None, model_name="model"):
        super().__init__(parent)
        self.model_path = model_path
        self.model_name = model_name or "model"
        self.setWindowTitle("Model Export")
        self.resize(1200, 700)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ================= TOP AREA =================
        top_layout = QHBoxLayout()

        # -------- Spectrometer Information --------
        spectro_box = QGroupBox("spectrometer information")
        spectro_layout = QGridLayout(spectro_box)

        spectro_layout.addWidget(QLabel("initial wavelength:"), 0, 0)
        self.initial_wavelength_spin = QSpinBox()
        self.initial_wavelength_spin.setRange(0, 10000)
        self.initial_wavelength_spin.setValue(900)
        spectro_layout.addWidget(self.initial_wavelength_spin, 0, 1)

        spectro_layout.addWidget(QLabel("terminal wavelength:"), 0, 2)
        self.terminal_wavelength_spin = QSpinBox()
        self.terminal_wavelength_spin.setRange(0, 10000)
        self.terminal_wavelength_spin.setValue(1700)
        spectro_layout.addWidget(self.terminal_wavelength_spin, 0, 3)

        spectro_layout.addWidget(QLabel("resolution:"), 1, 0)
        spectro_layout.addWidget(QLineEdit("12.87"), 1, 1)

        spectro_layout.addWidget(QLabel("exposure time:"), 1, 2)
        spectro_layout.addWidget(QLineEdit("0.635"), 1, 3)

        spectro_layout.addWidget(QLabel("average number:"), 2, 0)
        self.average_number_spin = QSpinBox()
        self.average_number_spin.setRange(0, 10000)
        spectro_layout.addWidget(self.average_number_spin, 2, 1)

        spectro_layout.addWidget(QLabel("number of scanning:"), 2, 2)
        self.number_of_scanning_spin = QSpinBox()
        self.number_of_scanning_spin.setRange(0, 10000)
        spectro_layout.addWidget(self.number_of_scanning_spin, 2, 3)

        top_layout.addWidget(spectro_box, 2)

        # -------- Model Information --------
        model_box = QGroupBox("model information")
        model_layout = QGridLayout(model_box)

        model_layout.addWidget(QLabel("instrument type:"), 0, 0)
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(["IAS5100", "IAS5200"])
        model_layout.addWidget(self.instrument_combo, 0, 1)

        model_layout.addWidget(QLabel("model name:"), 0, 2)
        self.model_name_edit = QLineEdit(self.model_name)
        model_layout.addWidget(self.model_name_edit, 0, 3)

        model_layout.addWidget(QLabel("model abbreviation:"), 1, 0)
        self.model_abbreviation_edit = QLineEdit()
        model_layout.addWidget(self.model_abbreviation_edit, 1, 1)

        model_layout.addWidget(QLabel("version:"), 1, 2)
        self.version_edit = QLineEdit()
        model_layout.addWidget(self.version_edit, 1, 3)

        model_layout.addWidget(QLabel("remark:"), 2, 0)
        self.remark_edit = QLineEdit()
        model_layout.addWidget(self.remark_edit, 2, 1, 1, 3)

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

    def _connect_signals(self):
        self.btn_export_official.clicked.connect(self.export_official_version)
        self.btn_export_normal.clicked.connect(self.export_normal_version)
        self.btn_rebuild.clicked.connect(self.show_rebuild_info)
        self.btn_language.clicked.connect(self.show_language_info)

    def _safe_name(self):
        raw_name = self.model_name_edit.text().strip() or self.model_name
        return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in raw_name).strip("_") or "model"

    def _export_with_variant(self, variant_label):
        if not self.model_path:
            QMessageBox.warning(self, "Export Error", "No model was selected for export.")
            return

        safe_name = self._safe_name()
        suffix = "official" if variant_label == "official" else "normal"
        default_name = f"{safe_name}_{suffix}.agnextpro"
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {variant_label.title()} IAS Model",
            default_name,
            "Encrypted Model (*.agnextpro)"
        )
        if not export_path:
            return

        try:
            exported_path = ModelManagementService.export_model(self.model_path, export_path)

            # Verify the encrypted file exists and can be decrypted with the configured key.
            if not exported_path.exists() or exported_path.stat().st_size == 0:
                raise ValueError("Encrypted model file was not created.")
            load_encrypted_model(exported_path, get_default_encryption_key())

            QMessageBox.information(
                self,
                "Export Complete",
                f"{variant_label.title()} encrypted model exported to:\n{exported_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export model:\n{e}")

    def export_official_version(self):
        self._export_with_variant("official")

    def export_normal_version(self):
        self._export_with_variant("normal")

    def show_rebuild_info(self):
        QMessageBox.information(
            self,
            "Not Implemented",
            "Rebuild file is not implemented yet."
        )

    def show_language_info(self):
        QMessageBox.information(
            self,
            "Not Implemented",
            "Add multi languages is not implemented yet."
        )
