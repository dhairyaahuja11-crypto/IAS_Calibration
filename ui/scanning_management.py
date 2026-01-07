from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QTableWidget, QDateEdit
)
from PyQt6.QtCore import QDate

from ui.dialogs.data_scanning_dialog import DataScanningDialog
from ui.dialogs.dlp_test_dialog import DLPTestDialog



class ScanningManagementUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------------- FILTER AREA ----------------
        filter_layout = QGridLayout()

        filter_layout.addWidget(QLabel("Sample name:"), 0, 0)
        self.sample_name_edit = QLineEdit()
        filter_layout.addWidget(self.sample_name_edit, 0, 1)

        filter_layout.addWidget(QLabel("Sample status:"), 0, 2)
        self.sample_status_combo = QComboBox()
        self.sample_status_combo.addItems(["all", "pending", "scanned"])
        filter_layout.addWidget(self.sample_status_combo, 0, 3)

        filter_layout.addWidget(QLabel("User ID:"), 0, 4)
        self.user_id_edit = QLineEdit("Agnext")
        filter_layout.addWidget(self.user_id_edit, 0, 5)

        filter_layout.addWidget(QLabel("Creation time:"), 1, 0)

        self.date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd MMMM yyyy")

        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd MMMM yyyy")

        filter_layout.addWidget(self.date_from, 1, 1)
        filter_layout.addWidget(QLabel("~"), 1, 2)
        filter_layout.addWidget(self.date_to, 1, 3)

        main_layout.addLayout(filter_layout)

        # ---------------- BUTTON BAR ----------------
        btn_layout = QHBoxLayout()

        self.inquiry_btn = QPushButton("Inquiry")
        self.btn_data_scanning = QPushButton("Data Scanning")
        self.dlp_btn = QPushButton("DLP Test")

        btn_layout.addWidget(self.inquiry_btn)
        btn_layout.addWidget(self.btn_data_scanning)
        btn_layout.addWidget(self.dlp_btn)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        self.btn_data_scanning.clicked.connect(self.open_data_scanning_dialog )

        self.dlp_btn.clicked.connect(self.open_dlp_test_dialog)


        # ---------------- TABLE ----------------
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "", "ID", "Sample Name",
            "Instrument", "Scanning Method",
            "Start Wavelength", "End Wavelength",
            "Step", "User ID", "Status"
        ])

        main_layout.addWidget(self.table)

    def open_data_scanning_dialog(self):
        dialog = DataScanningDialog(self)
        dialog.exec()

    def open_dlp_test_dialog(self):
        dialog = DLPTestDialog(self)
        dialog.exec()
