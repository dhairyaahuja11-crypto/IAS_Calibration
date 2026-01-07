# modify_project_management.py
'''
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox
)


class ModifyProjectManagement(QWidget):
    def __init__(self):
        super().__init__()
        self.build_ui()

    def build_ui(self):
        main_layout = QHBoxLayout(self)

        # LEFT PANEL
        left_layout = QVBoxLayout()

        form = QGridLayout()
        row = 0

        self.project_name = QLineEdit()
        form.addWidget(QLabel("Project name:"), row, 0)
        form.addWidget(self.project_name, row, 1)
        row += 1

        self.measurement_type = QComboBox()
        self.measurement_type.addItems(["Quantitative", "Qualitative"])
        form.addWidget(QLabel("Measurement type:"), row, 0)
        form.addWidget(self.measurement_type, row, 1)
        row += 1

        self.remark = QLineEdit()
        form.addWidget(QLabel("Remark:"), row, 0)
        form.addWidget(self.remark, row, 1)
        row += 1

        self.user_id = QLineEdit()
        form.addWidget(QLabel("User ID:"), row, 0)
        form.addWidget(self.user_id, row, 1)
        row += 1

        self.sample_type = QComboBox()
        self.sample_type.addItems(["Granules", "Powder", "Liquid"])
        form.addWidget(QLabel("Sample type:"), row, 0)
        form.addWidget(self.sample_type, row, 1)

        left_layout.addLayout(form)

        # Measurement index
        index_group = QGroupBox("Measurement index")
        index_layout = QVBoxLayout(index_group)

        self.index_checkboxes = {}
        for name in [
            "Protein", "Oil", "Moisture", "Fiber",
            "Ash", "T. Ash", "GCV", "Sucrose"
        ]:
            cb = QCheckBox(name)
            index_layout.addWidget(cb)
            self.index_checkboxes[name] = cb

        left_layout.addWidget(index_group)
        left_layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_data)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.clear_inputs)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)

        left_layout.addLayout(btn_layout)

        main_layout.addLayout(left_layout, 2)

        # TABLE
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Sample name", "Status", "Quantity",
            "Scanning method", "User ID",
            "Creation time", ""
        ])

        main_layout.addWidget(self.table, 5)

        # RIGHT PANEL
        right_panel = QWidget()
        right_panel.setStyleSheet("border: 1px solid #c0c0c0;")
        main_layout.addWidget(right_panel, 2)

    # ---------- LOGIC ----------
    def save_data(self):
        print("Saving project:")
        print("Project name:", self.project_name.text())

    def clear_inputs(self):
        self.project_name.clear()
        self.remark.clear()
        self.user_id.clear()
        for cb in self.index_checkboxes.values():
            cb.setChecked(False)
'''

from PyQt6.QtWidgets import (
    QDialog, QWidget, QLabel, QLineEdit, QComboBox,
    QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
    QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt


class ModifyProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project Information")
        self.resize(900, 450)
        self.build_ui()

    def build_ui(self):
        main_layout = QHBoxLayout(self)

        # -------- LEFT SIDE --------
        left_layout = QVBoxLayout()
        form = QGridLayout()

        row = 0

        # Project name
        form.addWidget(QLabel("Project name:"), row, 0)
        self.project_name = QLineEdit("Automation IAS Project1")
        form.addWidget(self.project_name, row, 1)

        # Sample type
        form.addWidget(QLabel("Sample type:"), row, 2)
        self.sample_type = QComboBox()
        self.sample_type.addItems(["Granules", "Powder", "Liquid"])
        form.addWidget(self.sample_type, row, 3)
        row += 1

        # Measurement type
        form.addWidget(QLabel("Measurement type:"), row, 0)
        self.measurement_type = QComboBox()
        self.measurement_type.addItems(["Quantitative", "Qualitative"])
        form.addWidget(self.measurement_type, row, 1)

        # Measurement index label
        form.addWidget(QLabel("Measurement index:"), row, 2)
        row += 1

        # Remark
        form.addWidget(QLabel("Remark:"), row, 0)
        self.remark = QLineEdit()
        form.addWidget(self.remark, row, 1)
        row += 1

        # User ID
        form.addWidget(QLabel("User ID:"), row, 0)
        self.user_id = QLineEdit("by_automation_script")
        form.addWidget(self.user_id, row, 1)
        row += 1

        # Sample selection
        self.sample_btn = QPushButton("sample selection")
        self.sample_combo = QComboBox()
        self.sample_combo.addItem("MDOC_PY_REPLIC_MOI")
        self.copy_btn = QPushButton("copy")

        form.addWidget(self.sample_btn, row, 0)
        form.addWidget(self.sample_combo, row, 1)
        form.addWidget(self.copy_btn, row, 2)

        left_layout.addLayout(form)
        left_layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(QPushButton("Save"))
        btn_layout.addWidget(QPushButton("Cancel"))
        left_layout.addLayout(btn_layout)

        main_layout.addLayout(left_layout, 3)

        # -------- RIGHT SIDE (Measurement Index) --------
        self.index_list = QListWidget()
        for name in ["Protein", "Oil", "Moisture", "Fiber", "Ash", "T. Ash", "GCV", "Sucrose"]:
            item = QListWidgetItem(name)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.index_list.addItem(item)

        main_layout.addWidget(self.index_list, 2)
