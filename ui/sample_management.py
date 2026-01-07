from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QDateEdit
)
from PyQt6.QtCore import Qt, QDate

# 🔴 Dialog imports
from ui.dialogs.sample_add_dialog import SampleAddDialog
from ui.dialogs.sample_modify_dialog import SampleModifyDialog
from PyQt6.QtWidgets import QMessageBox


class SampleManagementUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------------- FILTER AREA ----------------
        filter_layout = QGridLayout()

        filter_layout.addWidget(QLabel("Sample name:"), 0, 0)
        self.sample_name = QLineEdit()
        filter_layout.addWidget(self.sample_name, 0, 1)

        filter_layout.addWidget(QLabel("Sample status:"), 0, 2)
        self.sample_status = QComboBox()
        self.sample_status.addItems([
            "all", "Not Collected", "Collected", "Completed"
        ])
        filter_layout.addWidget(self.sample_status, 0, 3)

        filter_layout.addWidget(QLabel("User ID:"), 0, 4)
        self.user_id = QLineEdit("Agnext")
        filter_layout.addWidget(self.user_id, 0, 5)

        filter_layout.addWidget(QLabel("Creation time:"), 0, 6)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd MMMM yyyy")

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd MMMM yyyy")

        filter_layout.addWidget(self.date_from, 0, 7)
        filter_layout.addWidget(self.date_to, 0, 8)

        main_layout.addLayout(filter_layout)

        # ---------------- BUTTON BAR ----------------
        btn_layout = QHBoxLayout()

        self.btn_inquiry = QPushButton("Inquiry")
        self.btn_add = QPushButton("Add")
        self.btn_modify = QPushButton("Modify")
        self.btn_delete = QPushButton("Delete")
        self.btn_tick = QPushButton("Tick")
        self.btn_batch_import = QPushButton("Batch import substance content")

        btn_layout.addWidget(self.btn_inquiry)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_modify)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_tick)
        btn_layout.addWidget(self.btn_batch_import)

        self.template_download = QLabel('<a href="#">template download</a>')
        self.template_download.setTextFormat(Qt.TextFormat.RichText)
        self.template_download.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.template_download.setOpenExternalLinks(False)

        btn_layout.addWidget(self.template_download)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # Spacer (table will be added later)
        main_layout.addStretch()

    # ---------------- SIGNALS ----------------
    def _connect_signals(self):
        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_modify.clicked.connect(self.open_modify_dialog)

    # ---------------- ADD ----------------
    def open_add_dialog(self):
        dialog = SampleAddDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            print("Add sample:", data)
            # TODO: insert into table / database

    # ---------------- MODIFY ----------------
    def open_modify_dialog(self):
        # 🔴 TEMPORARY: replace with real table selection later
        sample_data = self._mock_selected_sample()

        if not sample_data:
            print("No sample selected for modify")
            return

        dialog = SampleModifyDialog(sample_data, self)
        if dialog.exec():
            updated_data = dialog.get_data()
            print("Modified sample:", updated_data)
            # TODO: update table / database

    def _connect_signals(self):
        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_modify.clicked.connect(self.open_modify_dialog)
        self.btn_delete.clicked.connect(self.open_delete_dialog)  # 🔴 NEW

    

    def open_delete_dialog(self):
        # 🔴 Replace this later with real table selection check
        has_selection = False  # example placeholder

        if not has_selection:
            QMessageBox.information(
                self,
                "Information",
                "Please check the samples to be deleted!"
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete the selected samples?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            print("Delete confirmed")
            # TODO: delete from table / database

    # ---------------- MOCK DATA (REMOVE LATER) ----------------
    def _mock_selected_sample(self):
        """
        Temporary helper until table selection is implemented.
        Replace this with selected row data.
        """
        return {
            "sample_name": "Sample_001",
            "scan_quantity": 10,
            "initial_wavelength": 900,
            "terminal_wavelength": 1700,
            "wavelength_step": 1,
            "user_id": "Agnext",
            "remark": "Initial sample",
            "substance_content": ["Protein", "Oil"],
            "batch": False
        }
