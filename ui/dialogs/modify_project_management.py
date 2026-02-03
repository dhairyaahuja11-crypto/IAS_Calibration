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
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt
from ui.dialogs.sample_selection_dialog import SampleSelectionDialog
from services.project_service import ProjectService


class ModifyProjectDialog(QDialog):
    def __init__(self, parent=None, project_data=None, project_samples=None):
        super().__init__(parent)
        self.project_data = project_data or {}
        self.project_samples = project_samples or []
        self.setWindowTitle("Project Information")
        self.resize(900, 600)
        self.build_ui()
        self.connect_signals()
        self.populate_data()

    def build_ui(self):
        main_layout = QVBoxLayout(self)

        # -------- TOP FORM --------
        form = QGridLayout()

        # Project name
        form.addWidget(QLabel("Project name:"), 0, 0)
        self.project_name = QLineEdit()
        form.addWidget(self.project_name, 0, 1)

        # Sample type
        form.addWidget(QLabel("Sample type:"), 0, 2)
        self.sample_type = QComboBox()
        self.sample_type.addItems(["Granules", "Powder", "Liquid"])
        form.addWidget(self.sample_type, 0, 3)

        # Measurement type
        form.addWidget(QLabel("Measurement type:"), 1, 0)
        self.measurement_type = QComboBox()
        self.measurement_type.addItems(["Quantitative", "Qualitative"])
        form.addWidget(self.measurement_type, 1, 1)

        # Measurement index
        form.addWidget(QLabel("Measurement index:"), 1, 2)
        self.index_list = QListWidget()
        self.index_list.setMaximumHeight(120)
        
        # Load measurement indexes dynamically
        self.load_measurement_indexes()
        
        form.addWidget(self.index_list, 1, 3, 3, 1)

        # Remark
        form.addWidget(QLabel("Remark:"), 2, 0)
        self.remark = QLineEdit()
        form.addWidget(self.remark, 2, 1)

        # User ID
        form.addWidget(QLabel("User ID:"), 3, 0)
        self.user_id = QLineEdit()
        form.addWidget(self.user_id, 3, 1)

        main_layout.addLayout(form)

        # -------- SAMPLE SELECTION --------
        sample_layout = QHBoxLayout()
        self.sample_btn = QPushButton("sample\nselection")
        self.copy_btn = QPushButton("copy")
        sample_layout.addWidget(self.sample_btn)
        sample_layout.addStretch()
        sample_layout.addWidget(self.copy_btn)
        main_layout.addLayout(sample_layout)

        # -------- SAMPLE TABLE --------
        main_layout.addWidget(QLabel("Sample selected:"))
        self.sample_table = QTableWidget(0, 5)
        self.sample_table.setHorizontalHeaderLabels([
            "sample name", "status", "quantity",
            "scanning method", "creation time"
        ])
        self.sample_table.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.sample_table)

        # -------- BUTTONS --------
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(btn_layout)
    
    def connect_signals(self):
        """Connect button signals"""
        self.sample_btn.clicked.connect(self.open_sample_selection)
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self.save_project)
    
    def load_measurement_indexes(self):
        """Load measurement indexes dynamically from content_dictionary table"""
        try:
            from database.db import get_connection
            
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT content_name FROM content_dictionary ORDER BY content_name")
            parameters = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            self.index_list.clear()
            for param in parameters:
                param_name = param['content_name']
                item = QListWidgetItem(param_name)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.index_list.addItem(item)
            
            if not parameters:
                for text in ["Protein", "Oil", "Moisture"]:
                    item = QListWidgetItem(text)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    self.index_list.addItem(item)
                    
        except Exception as e:
            print(f"Error loading measurement indexes: {e}")
            for text in ["Protein", "Oil", "Moisture"]:
                item = QListWidgetItem(text)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.index_list.addItem(item)
    
    def populate_data(self):
        """Populate form with project data"""
        if not self.project_data:
            return
        
        # Decode bytes if necessary
        def decode_if_bytes(value):
            if isinstance(value, bytes):
                return value.decode('utf-8')
            return str(value) if value is not None else ''
        
        # Populate form fields
        self.project_name.setText(decode_if_bytes(self.project_data.get('project_name', '')))
        self.remark.setText(decode_if_bytes(self.project_data.get('remark', '')))
        self.user_id.setText(decode_if_bytes(self.project_data.get('user_id', '')))
        
        # Set sample type
        sample_type = decode_if_bytes(self.project_data.get('sample_type', ''))
        index = self.sample_type.findText(sample_type, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            self.sample_type.setCurrentIndex(index)
        
        # Set measurement type
        measurement_type = decode_if_bytes(self.project_data.get('measurement_type', ''))
        if measurement_type.lower().startswith('qual'):
            self.measurement_type.setCurrentText("Qualitative")
        elif measurement_type.lower().startswith('quan'):
            self.measurement_type.setCurrentText("Quantitative")
        
        # Check measurement indexes
        measurement_index = decode_if_bytes(self.project_data.get('measurement_index', ''))
        selected_indexes = [idx.strip() for idx in measurement_index.split(',') if idx.strip()]
        
        for i in range(self.index_list.count()):
            item = self.index_list.item(i)
            if item.text() in selected_indexes:
                item.setCheckState(Qt.CheckState.Checked)
        
        # Populate sample table
        self.populate_sample_table(self.project_samples)
    
    def populate_sample_table(self, samples):
        """Populate the sample table with samples"""
        self.sample_table.setRowCount(0)
        
        for sample in samples:
            row = self.sample_table.rowCount()
            self.sample_table.insertRow(row)
            
            # Decode bytes if necessary
            def decode_if_bytes(value):
                if isinstance(value, bytes):
                    return value.decode('utf-8')
                return str(value) if value is not None else ''
            
            columns = [
                decode_if_bytes(sample.get('sample_name', '')),
                decode_if_bytes(sample.get('sample_status', '')),
                decode_if_bytes(sample.get('sample_quantity', '0')),
                decode_if_bytes(sample.get('scanning_method', '')),
                decode_if_bytes(sample.get('creation_time', ''))
            ]
            
            for col, value in enumerate(columns):
                item = QTableWidgetItem(value)
                self.sample_table.setItem(row, col, item)
    
    def open_sample_selection(self):
        """Open sample selection dialog"""
        dialog = SampleSelectionDialog(self)
        if dialog.exec():
            # Add newly selected samples
            new_samples = dialog.selected_samples
            self.project_samples.extend(new_samples)
            self.populate_sample_table(self.project_samples)
    
    def save_project(self):
        """Save modified project to database"""
        # Get form data
        project_data = {
            'project_name': self.project_name.text().strip(),
            'sample_type': self.sample_type.currentText(),
            'measurement_type': self.measurement_type.currentText(),
            'measurement_index': [],
            'remark': self.remark.text().strip()
        }
        
        # Get checked measurement indexes
        for i in range(self.index_list.count()):
            item = self.index_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                project_data['measurement_index'].append(item.text())
        
        # Validate
        if not project_data['project_name']:
            QMessageBox.warning(self, "Validation Error", "Please enter a project name.")
            return
        
        if not project_data['measurement_index']:
            QMessageBox.warning(self, "Validation Error", "Please select at least one measurement index.")
            return
        
        # Get project ID
        project_id = self.project_data.get('project_id')
        if isinstance(project_id, bytes):
            project_id = project_id.decode('utf-8')
        
        # Update in database
        success, message = ProjectService.update_project(project_id, project_data)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", message)
