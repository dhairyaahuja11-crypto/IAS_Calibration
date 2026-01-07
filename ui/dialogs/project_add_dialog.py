from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QListWidget,
    QListWidgetItem, QTableWidget, QTableWidgetItem, QWidget
)
from PyQt6.QtCore import Qt


class ProjectAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("project name")
        self.resize(900, 600)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------------- TOP FORM ----------------
        form_layout = QGridLayout()

        form_layout.addWidget(QLabel("project name:"), 0, 0)
        self.project_name_edit = QLineEdit()
        form_layout.addWidget(self.project_name_edit, 0, 1)

        form_layout.addWidget(QLabel("sample type:"), 0, 2)
        self.sample_type_combo = QComboBox()
        self.sample_type_combo.addItems(["Granules", "Powder", "Liquid"])
        form_layout.addWidget(self.sample_type_combo, 0, 3)

        form_layout.addWidget(QLabel("measurement type:"), 1, 0)
        self.measurement_type_combo = QComboBox()
        self.measurement_type_combo.addItems(["Qualitative", "Quantitative"])
        form_layout.addWidget(self.measurement_type_combo, 1, 1)

        form_layout.addWidget(QLabel("measurement index:"), 1, 2)
        self.measurement_index_list = QListWidget()
        for text in ["Protein", "Oil", "Moisture"]:
            item = QListWidgetItem(text)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.measurement_index_list.addItem(item)
        form_layout.addWidget(self.measurement_index_list, 1, 3, 3, 1)

        form_layout.addWidget(QLabel("remark:"), 2, 0)
        self.remark_edit = QLineEdit()
        form_layout.addWidget(self.remark_edit, 2, 1)

        form_layout.addWidget(QLabel("User ID:"), 3, 0)
        self.user_id_edit = QLineEdit("Agnext")
        form_layout.addWidget(self.user_id_edit, 3, 1)

        main_layout.addLayout(form_layout)

        # ---------------- SAMPLE SELECTION ----------------
        sample_layout = QHBoxLayout()

        self.sample_select_btn = QPushButton("sample\nselection")
        self.copy_btn = QPushButton("copy")

        sample_layout.addWidget(self.sample_select_btn)
        sample_layout.addStretch()
        sample_layout.addWidget(self.copy_btn)

        main_layout.addLayout(sample_layout)

        # ---------------- SAMPLE TABLE ----------------
        self.sample_table = QTableWidget(0, 6)
        self.sample_table.setHorizontalHeaderLabels([
            "sample name", "status", "quantity",
            "scanning method", "User ID", "creation time"
        ])
        self.sample_table.horizontalHeader().setStretchLastSection(True)

        main_layout.addWidget(QLabel("sample selected:"))
        main_layout.addWidget(self.sample_table)

        # ---------------- BUTTONS ----------------
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.save_btn = QPushButton("save")
        self.cancel_btn = QPushButton("cancel")

        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(btn_layout)

    # ---------------- DATA ACCESS ----------------
    def get_data(self):
        measurement_indexes = []
        for i in range(self.measurement_index_list.count()):
            item = self.measurement_index_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                measurement_indexes.append(item.text())

        return {
            "project_name": self.project_name_edit.text(),
            "sample_type": self.sample_type_combo.currentText(),
            "measurement_type": self.measurement_type_combo.currentText(),
            "measurement_index": measurement_indexes,
            "remark": self.remark_edit.text(),
            "user_id": self.user_id_edit.text(),
        }
