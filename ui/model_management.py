from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QTableWidget, QDateEdit, QMessageBox
)
from PyQt6.QtCore import QDate
from ui.custom_widgets import DateEditWithToday

# ✅ CORRECT import
from ui.dialogs.model_export_equipment_dialog import (
    ModelExportEquipmentDialog
)


class ModelManagementUI(QWidget):
    def __init__(self):
        super().__init__()
        self.export_equipment_dialog = None  # keep reference
        self._build_ui()
        self._connect_signals()

    # ================= UI =================
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
            QLineEdit, QComboBox, QDateEdit {
                background-color: #ffffff;
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
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
        """)

        # -------- FILTER AREA --------
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

        # -------- BUTTON BAR --------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_inquiry = QPushButton("Inquiry")
        self.btn_delete = QPushButton("Delete")
        self.btn_export = QPushButton("Export")
        self.btn_export_ias = QPushButton("Export IAS Model File")
        self.btn_export_equipment = QPushButton(
            "Export Model File for IAS Equipment"
        )
        self.btn_clear_selection = QPushButton("Clear Selection")

        btn_layout.addWidget(self.btn_inquiry)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_export_ias)
        btn_layout.addWidget(self.btn_export_equipment)
        btn_layout.addWidget(self.btn_clear_selection)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # -------- TABLE --------
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "", "Model ID", "Model Name",
            "Project Name", "User ID",
            "Creation Time", "Status",
            "Description", "Version", "Remark"
        ])
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
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
                border-bottom: 1px solid #c9d6e5;
                font-weight: bold;
            }
        """)
        
        # Install event filter to detect clicks on empty table space
        self.table.viewport().installEventFilter(self)

        main_layout.addWidget(self.table)

    # ================= SIGNALS =================
    def _connect_signals(self):
        self.btn_export_equipment.clicked.connect(
            self.open_export_equipment_dialog
        )
        self.btn_delete.clicked.connect(self.delete_model)
        self.btn_clear_selection.clicked.connect(self.on_clear_selection_clicked)
    
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
    
    def on_clear_selection_clicked(self):
        """Clear all row selections"""
        self.table.clearSelection()

    # ================= ACTIONS =================
    def open_export_equipment_dialog(self):
        print("Opening Export Model File for IAS Equipment dialog")

        # ✅ keep reference so it does NOT close
        self.export_equipment_dialog = ModelExportEquipmentDialog(self)
        self.export_equipment_dialog.setModal(True)
        self.export_equipment_dialog.show()

    def delete_model(self):
        row = self.table.currentRow()

        if row < 0:
            QMessageBox.information(
                self,
                "Information",
                "Please select a model to delete!"
            )
            return

        model_item = self.table.item(row, 1)
        model_id = model_item.text() if model_item else "Unknown"

        reply = QMessageBox.question(
            self,
            "Warning",
            f"delete this model data:{model_id}?",
            QMessageBox.StandardButton.Ok |
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Ok:
            print(f"Model {model_id} deleted")
            self.table.removeRow(row)
