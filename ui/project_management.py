from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QDateEdit, QMessageBox
)
from PyQt6.QtCore import QDate

# Add dialog
from ui.dialogs.project_add_dialog import ProjectAddDialog

# Modify dialog
from ui.dialogs.modify_project_management import ModifyProjectDialog


class ProjectManagementUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._connect_signals()

    # ---------------- UI ----------------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------- FILTER AREA ----------
        filter_layout = QGridLayout()

        filter_layout.addWidget(QLabel("Project name:"), 0, 0)
        self.project_name = QLineEdit()
        filter_layout.addWidget(self.project_name, 0, 1)

        filter_layout.addWidget(QLabel("Sample Type:"), 0, 2)
        self.sample_combo = QComboBox()
        self.sample_combo.addItems(["all", "granules", "powdery", "flake"])
        filter_layout.addWidget(self.sample_combo, 0, 3)

        filter_layout.addWidget(QLabel("Type:"), 0, 4)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["all", "Qualitative", "Quantitative"])
        filter_layout.addWidget(self.type_combo, 0, 5)

        filter_layout.addWidget(QLabel("Status:"), 0, 6)
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            "all", "Created", "Gathering",
            "Modelling", "ReModelling",
            "Completed", "Data Test"
        ])
        filter_layout.addWidget(self.status_combo, 0, 7)

        filter_layout.addWidget(QLabel("User ID:"), 0, 8)
        self.user_id = QLineEdit()
        filter_layout.addWidget(self.user_id, 0, 9)

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

        # ---------- BUTTON BAR ----------
        btn_layout = QHBoxLayout()

        self.btn_inquiry = QPushButton("Inquiry")
        self.btn_add = QPushButton("Add")
        self.btn_modify = QPushButton("Modify")
        self.btn_delete = QPushButton("Delete")

        btn_layout.addWidget(self.btn_inquiry)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_modify)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)
        main_layout.addStretch()

    # ---------------- SIGNALS ----------------
    def _connect_signals(self):
        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_modify.clicked.connect(self.open_modify_dialog)
        self.btn_delete.clicked.connect(self.open_delete_dialog)

    # ---------------- ACTIONS ----------------
    def open_add_dialog(self):
        dialog = ProjectAddDialog(self)
        if dialog.exec():
            print("Project added")

    def open_modify_dialog(self):
        # IMPORTANT: keep reference + use exec()
        self.modify_dialog = ModifyProjectDialog(self)
        self.modify_dialog.setWindowTitle("Modify Project")
        self.modify_dialog.resize(1200, 700)
        self.modify_dialog.exec()

    def open_delete_dialog(self):
        reply = QMessageBox.question(
            self,
            "Warning",
            "Delete OK?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            print("Project deleted")
        else:
            print("Delete cancelled")
