from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QTableWidget
)
from PyQt6.QtCore import QDate

from ui.custom_widgets import DateEditWithToday

from ui.dialogs.data_scanning_dialog import DataScanningDialog
from ui.dialogs.dlp_test_dialog import DLPTestDialog



class ScanningManagementUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        self.setObjectName("scanningManagementRoot")
        self.setStyleSheet("""
            QWidget#scanningManagementRoot {
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

        # ---------------- FILTER AREA ----------------
        filter_layout = QGridLayout()
        filter_layout.setHorizontalSpacing(10)
        filter_layout.setVerticalSpacing(8)

        filter_layout.addWidget(QLabel("Sample name:"), 0, 0)
        self.sample_name_edit = QLineEdit()
        filter_layout.addWidget(self.sample_name_edit, 0, 1)

        filter_layout.addWidget(QLabel("Sample status:"), 0, 2)
        self.sample_status_combo = QComboBox()
        self.sample_status_combo.addItems(["all", "pending", "scanned"])
        filter_layout.addWidget(self.sample_status_combo, 0, 3)

        filter_layout.addWidget(QLabel("User ID:"), 0, 4)
        self.user_id_edit = QLineEdit()
        filter_layout.addWidget(self.user_id_edit, 0, 5)

        filter_layout.addWidget(QLabel("Creation time:"), 1, 0)

        self.date_from = DateEditWithToday(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd MMMM yyyy")

        self.date_to = DateEditWithToday(QDate.currentDate())
        self.date_to.setDisplayFormat("dd MMMM yyyy")

        filter_layout.addWidget(self.date_from, 1, 1)
        filter_layout.addWidget(QLabel("~"), 1, 2)
        filter_layout.addWidget(self.date_to, 1, 3)

        main_layout.addLayout(filter_layout)

        # ---------------- BUTTON BAR ----------------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

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

        main_layout.addWidget(self.table)

    def open_data_scanning_dialog(self):
        dialog = DataScanningDialog(self)
        dialog.exec()

    def open_dlp_test_dialog(self):
        dialog = DLPTestDialog(self)
        dialog.exec()
