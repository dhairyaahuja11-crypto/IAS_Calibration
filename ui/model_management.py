from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog
)
from PyQt6.QtWidgets import QHeaderView

from services.model_management_service import ModelManagementService
from ui.custom_widgets import DateEditWithToday
from ui.dialogs.model_export_equipment_dialog import ModelExportEquipmentDialog


class ModelManagementUI(QWidget):
    def __init__(self):
        super().__init__()
        self.export_equipment_dialog = None
        self.model_records = []
        self._build_ui()
        self._connect_signals()
        self.load_models()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        self.setObjectName("modelManagementRoot")
        self.setStyleSheet("""
            QWidget#modelManagementRoot {
                background-color: #f6f8fb;
            }
            QLabel {
                color: #1f2937;
                font-size: 12px;
            }
            QLineEdit, QDateEdit {
                background-color: #ffffff;
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
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
        """)

        filter_layout = QGridLayout()
        filter_layout.setHorizontalSpacing(10)
        filter_layout.setVerticalSpacing(8)

        filter_layout.addWidget(QLabel("Model ID:"), 0, 0)
        self.model_id_edit = QLineEdit()
        filter_layout.addWidget(self.model_id_edit, 0, 1)

        filter_layout.addWidget(QLabel("Model name:"), 0, 2)
        self.model_name_edit = QLineEdit()
        filter_layout.addWidget(self.model_name_edit, 0, 3)

        filter_layout.addWidget(QLabel("Project name:"), 0, 4)
        self.project_name_edit = QLineEdit()
        filter_layout.addWidget(self.project_name_edit, 0, 5)

        filter_layout.addWidget(QLabel("User ID:"), 0, 6)
        self.user_id_edit = QLineEdit()
        filter_layout.addWidget(self.user_id_edit, 0, 7)

        filter_layout.addWidget(QLabel("Creation time:"), 0, 8)
        self.date_from = DateEditWithToday(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd MMMM yyyy")
        self.date_to = DateEditWithToday(QDate.currentDate())
        self.date_to.setDisplayFormat("dd MMMM yyyy")
        filter_layout.addWidget(self.date_from, 0, 9)
        filter_layout.addWidget(QLabel("~"), 0, 10)
        filter_layout.addWidget(self.date_to, 0, 11)

        main_layout.addLayout(filter_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_inquiry = QPushButton("Inquiry")
        self.btn_delete = QPushButton("Delete")
        self.btn_export = QPushButton("Export")
        self.btn_export_ias = QPushButton("Export IAS Model File")
        self.btn_export_equipment = QPushButton("Export Model File for IAS Equipment")
        self.btn_clear_selection = QPushButton("Clear Selection")

        btn_layout.addWidget(self.btn_inquiry)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_export_ias)
        btn_layout.addWidget(self.btn_export_equipment)
        btn_layout.addWidget(self.btn_clear_selection)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        headers = [
            "ID",
            "model\nname",
            "project\nname",
            "measurement\nindex",
            "instrument",
            "wavelength\npoints",
            "number of\ncalibration set",
            "number of\nvalidation set",
            "intercept\ndata",
            "average\nenable",
            "pre-treatment algorithm\nand parameters",
            "intercept after\npre-treatment",
            "dimension reduction\nalgorithm",
            "dimension",
            "analysis\nalgorithm",
            "analysis algorithm\nparameters",
            "User ID",
            "creation\ntime",
        ]

        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.viewport().installEventFilter(self)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        header.setMinimumHeight(52)
        header.setDefaultSectionSize(130)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8fbff;
                color: #111827;
                border: 1px solid #d8e1eb;
                border-radius: 6px;
                selection-background-color: #dbeafe;
                selection-color: #0f172a;
                gridline-color: #e5ebf2;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #eef3f9;
                color: #1f2937;
                padding: 7px 6px;
                border: 1px solid #d8e1eb;
                font-weight: bold;
                min-height: 52px;
            }
        """)

        main_layout.addWidget(self.table)

    def _connect_signals(self):
        self.btn_inquiry.clicked.connect(self.on_inquiry_clicked)
        self.btn_delete.clicked.connect(self.delete_model)
        self.btn_export.clicked.connect(self.export_model)
        self.btn_export_ias.clicked.connect(self.export_ias_model_file)
        self.btn_clear_selection.clicked.connect(self.on_clear_selection_clicked)
        self.btn_export_equipment.clicked.connect(self.open_export_equipment_dialog)

    def load_models(self):
        self.model_records = ModelManagementService.list_models()
        self._populate_table(self.model_records)

    def on_inquiry_clicked(self):
        filtered_records = []
        model_id_filter = self.model_id_edit.text().strip().casefold()
        model_name_filter = self.model_name_edit.text().strip().casefold()
        project_name_filter = self.project_name_edit.text().strip().casefold()
        user_id_filter = self.user_id_edit.text().strip().casefold()

        from_date = self.date_from.date().toPyDate()
        to_date = self.date_to.date().toPyDate()

        for record in self.model_records:
            created_date = record["_created_at"].date()
            if created_date < from_date or created_date > to_date:
                continue
            if model_id_filter and model_id_filter not in record["model_id"].casefold():
                continue
            if model_name_filter and model_name_filter not in record["model_name"].casefold():
                continue
            if project_name_filter and project_name_filter not in record["project_name"].casefold():
                continue
            if user_id_filter and user_id_filter not in record["user_id"].casefold():
                continue
            filtered_records.append(record)

        self._populate_table(filtered_records)

    def _populate_table(self, records):
        self.table.setRowCount(0)

        for row_idx, record in enumerate(records):
            self.table.insertRow(row_idx)
            values = [
                record["model_id"],
                record["model_name"],
                record["project_name"],
                record["measurement_index"],
                record["instrument"],
                record["wavelength_points"],
                record["calibration_count"],
                record["validation_count"],
                record["intercept_data"],
                record["average_enable"],
                record["pretreatment_summary"],
                record["intercept_after_pretreatment"],
                record["dimension_reduction_algorithm"],
                record["dimension"],
                record["analysis_algorithm"],
                record["analysis_algorithm_parameters"],
                record["user_id"],
                record["creation_time"],
            ]

            for col_idx, value in enumerate(values):
                item = QTableWidgetItem("" if value is None else str(value))
                if col_idx == 0:
                    item.setData(Qt.ItemDataRole.UserRole, record["_path"])
                self.table.setItem(row_idx, col_idx, item)

    def open_export_equipment_dialog(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Information", "Please select a model to export!")
            return

        model_item = self.table.item(row, 0)
        model_path = model_item.data(Qt.ItemDataRole.UserRole) if model_item else None
        model_name_item = self.table.item(row, 1)
        model_name = model_name_item.text().strip() if model_name_item else "model"
        if not model_path:
            QMessageBox.warning(self, "Export Error", "Unable to resolve the selected model file.")
            return

        self.export_equipment_dialog = ModelExportEquipmentDialog(
            self,
            model_path=model_path,
            model_name=model_name
        )
        self.export_equipment_dialog.setModal(True)
        self.export_equipment_dialog.show()

    def export_ias_model_file(self):
        """Export the selected model as an encrypted IAS model file."""
        self.export_model()

    def delete_model(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Information", "Please select a model to delete!")
            return

        model_item = self.table.item(row, 0)
        model_id = model_item.text() if model_item else "Unknown"
        model_path = model_item.data(Qt.ItemDataRole.UserRole) if model_item else None
        if not model_path:
            QMessageBox.warning(self, "Delete Error", "Unable to resolve the selected model file.")
            return

        reply = QMessageBox.question(
            self,
            "Warning",
            f"Delete this model data: {model_id}?",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Ok:
            return

        try:
            ModelManagementService.delete_model(model_path)
            self.load_models()
            self.on_inquiry_clicked()
        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Failed to delete model:\n{e}")

    def export_model(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Information", "Please select a model to export!")
            return

        model_item = self.table.item(row, 0)
        model_path = model_item.data(Qt.ItemDataRole.UserRole) if model_item else None
        model_name_item = self.table.item(row, 1)
        model_name = model_name_item.text().strip() if model_name_item else "model"
        if not model_path:
            QMessageBox.warning(self, "Export Error", "Unable to resolve the selected model file.")
            return

        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in model_name).strip("_") or "model"
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Encrypted Model",
            f"{safe_name}.agnextpro",
            "Encrypted Model (*.agnextpro)"
        )
        if not export_path:
            return

        try:
            exported_path = ModelManagementService.export_model(model_path, export_path)
            QMessageBox.information(self, "Export Complete", f"Encrypted model exported to:\n{exported_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export model:\n{e}")

    def on_clear_selection_clicked(self):
        self.table.clearSelection()

    def keyPressEvent(self, event):
        from PyQt6.QtCore import Qt

        if event.key() == Qt.Key.Key_Escape:
            self.table.clearSelection()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent

        if obj == self.table.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            index = self.table.indexAt(event.pos())
            if not index.isValid():
                self.table.clearSelection()
                return True

        return super().eventFilter(obj, event)
