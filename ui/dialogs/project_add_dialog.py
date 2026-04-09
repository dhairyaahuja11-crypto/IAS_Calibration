from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QListWidget,
    QListWidgetItem, QTableWidget, QTableWidgetItem, QWidget, QMessageBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt
from ui.dialogs.sample_selection_dialog import SampleSelectionDialog
from services.project_service import ProjectService
from services.data_selection_service import DataSelectionService


class ProjectAddDialog(QDialog):
    # _on_measurement_index_clicked is no longer needed with radio buttons
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("project name")
        self.resize(900, 600)
        self.selected_samples = []  # Store selected samples
        self._build_ui()
        self._connect_signals()


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

        form_layout.addWidget(QLabel("instrument:"), 0, 4)
        self.instrument_combo = QComboBox()
        self.instrument_combo.setEditable(True)
        form_layout.addWidget(self.instrument_combo, 0, 5)

        form_layout.addWidget(QLabel("measurement type:"), 1, 0)
        self.measurement_type_combo = QComboBox()
        self.measurement_type_combo.addItems(["Qualitative", "Quantitative"])
        form_layout.addWidget(self.measurement_type_combo, 1, 1)

        form_layout.addWidget(QLabel("measurement index:"), 1, 2)
        self.measurement_index_list = QListWidget()
        form_layout.addWidget(self.measurement_index_list, 1, 3, 3, 1)
        # Button group for exclusive radio selection
        self.measurement_radio_group = QButtonGroup(self)
        self.measurement_radio_group.setExclusive(True)

        form_layout.addWidget(QLabel("remark:"), 2, 0)
        self.remark_edit = QLineEdit()
        form_layout.addWidget(self.remark_edit, 2, 1)

        form_layout.addWidget(QLabel("User ID:"), 3, 0)
        self.user_id_edit = QLineEdit()
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
        self.save_btn.clicked.connect(self.save_project)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(btn_layout)

        # Try to load measurement indexes, but don't let it break UI
        try:
            self.load_instruments()
            self.load_measurement_indexes()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load measurement indexes:\n{e}")

    def _connect_signals(self):
        """Connect signals for buttons"""
        if hasattr(self, 'sample_select_btn'):
            self.sample_select_btn.clicked.connect(self.open_sample_selection)
    
    def load_measurement_indexes(self):
        """Load measurement indexes dynamically from content_dictionary table and use radio buttons"""
        try:
            from database.db import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT content_name FROM content_dictionary ORDER BY content_name")
            parameters = cursor.fetchall()
            cursor.close()
            self.measurement_index_list.clear()
            self.measurement_radio_group = QButtonGroup(self)
            self.measurement_radio_group.setExclusive(True)
            if parameters:
                for idx, param in enumerate(parameters):
                    param_name = param['content_name']
                    item = QListWidgetItem()
                    radio = QRadioButton(param_name)
                    self.measurement_index_list.addItem(item)
                    self.measurement_index_list.setItemWidget(item, radio)
                    self.measurement_radio_group.addButton(radio, idx)
            else:
                for idx, text in enumerate(["Protein", "Oil", "Moisture"]):
                    item = QListWidgetItem()
                    radio = QRadioButton(text)
                    self.measurement_index_list.addItem(item)
                    self.measurement_index_list.setItemWidget(item, radio)
                    self.measurement_radio_group.addButton(radio, idx)
        except Exception as e:
            self.measurement_index_list.clear()
            self.measurement_radio_group = QButtonGroup(self)
            self.measurement_radio_group.setExclusive(True)
            for idx, text in enumerate(["Protein", "Oil", "Moisture"]):
                item = QListWidgetItem()
                radio = QRadioButton(text)
                self.measurement_index_list.addItem(item)
                self.measurement_index_list.setItemWidget(item, radio)
                self.measurement_radio_group.addButton(radio, idx)
                self.measurement_index_list.addItem(item)

    def _connect_signals(self):
        """Connect signals for buttons"""
        self.sample_select_btn.clicked.connect(self.open_sample_selection)

    def open_sample_selection(self):
        """Open sample selection dialog"""
        dialog = SampleSelectionDialog(self)
        if dialog.exec():
            # Get selected samples and populate the table
            self.selected_samples = dialog.selected_samples
            self.populate_sample_table(self.selected_samples)
            self._sync_instrument_from_samples()

    def load_instruments(self):
        """Load available instruments into the display combo."""
        self.instrument_combo.clear()
        self.instrument_combo.addItem("")
        try:
            for instrument in DataSelectionService.get_instruments():
                value = str(instrument).strip()
                if value:
                    self.instrument_combo.addItem(value)
        except Exception:
            pass

    def _sync_instrument_from_samples(self):
        """Reflect the selected samples' instruments in the combo."""
        values = []
        for sample in self.selected_samples:
            value = sample.get('instrument', '') if isinstance(sample, dict) else ''
            value = '' if value is None else str(value).strip()
            if value and value not in values:
                values.append(value)
        summary = ", ".join(values)
        self.instrument_combo.setCurrentText(summary)

    def populate_sample_table(self, samples):
        """Populate the sample table with selected samples"""
        self.sample_table.setRowCount(0)
        for sample in samples:
            row = self.sample_table.rowCount()
            self.sample_table.insertRow(row)
            # Always use the user_id from the sample dict, fallback to 'Unknown' if missing
            user_id = sample.get('user_id', None)
            if not user_id:
                user_id = 'Unknown'
            columns = [
                sample.get('sample_name', ''),
                sample.get('sample_status', ''),
                sample.get('sample_quantity', '0'),
                sample.get('scanning_method', ''),
                user_id,
                sample.get('creation_time', '')
            ]
            for col, value in enumerate(columns):
                item = QTableWidgetItem(str(value))
                self.sample_table.setItem(row, col, item)

    # ---------------- DATA ACCESS ----------------
    def get_data(self):
        # Only one radio button can be selected
        checked_id = self.measurement_radio_group.checkedId()
        checked_text = None
        if checked_id != -1:
            checked_button = self.measurement_radio_group.button(checked_id)
            checked_text = checked_button.text()
        measurement_indexes = [checked_text] if checked_text else []
        return {
            "project_name": self.project_name_edit.text(),
            "sample_type": self.sample_type_combo.currentText(),
            "instrument": self.instrument_combo.currentText().strip(),
            "measurement_type": self.measurement_type_combo.currentText(),
            "measurement_index": measurement_indexes,
            "remark": self.remark_edit.text(),
            "user_id": self.user_id_edit.text(),
        }
    def save_project(self):
        """Save the project with all form data and selected samples"""
        # Get form data
        project_data = self.get_data()
        project_name = project_data['project_name'].strip()
        
        # Validate inputs
        if not project_name:
            QMessageBox.warning(self, "Validation Error", "Please enter a project name.")
            return

        if ProjectService.project_name_exists(project_name):
            QMessageBox.warning(
                self,
                "Duplicate Project Name",
                f"Project name '{project_name}' already exists. Please enter a different project name."
            )
            return
        
        if not self.selected_samples:
            QMessageBox.warning(self, "Validation Error", "Please select at least one sample.")
            return
        
        if not project_data['measurement_index']:
            QMessageBox.warning(self, "Validation Error", "Please select at least one measurement index.")
            return
        
        # Validate that all selected samples have substance content (lab value)
        missing_lab_value = False
        for sample in self.selected_samples:
            # Accept both dict and object with attribute
            lab_value = sample.get('substance_content', '') if isinstance(sample, dict) else getattr(sample, 'substance_content', '')
            if not lab_value or str(lab_value).strip() == '' or str(lab_value).lower() == 'not collected':
                missing_lab_value = True
                break

        if missing_lab_value:
            QMessageBox.warning(self, "Lab Value Missing", "Lab values missing")
            return

        try:
            success, message, project_id = ProjectService.create_project(
                project_data, 
                self.selected_samples
            )
            if success:
                QMessageBox.information(self, "Success", message)
                self.accept()  # Close dialog with success
            else:
                QMessageBox.critical(self, "Error", message)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")
            import traceback
            traceback.print_exc()
