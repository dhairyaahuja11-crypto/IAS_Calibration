from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QTextEdit,
    QSpinBox, QCheckBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QWidget
)


class SampleAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sample Information")
        self.resize(750, 420)
        self.substance_inputs = {}
        self.build_ui()

    def build_ui(self):
        outer_layout = QVBoxLayout(self)
        
        main_layout = QHBoxLayout()

        # ---------- LEFT FORM ----------
        form_layout = QGridLayout()
        row = 0

        self.sample_name = QLineEdit()
        form_layout.addWidget(QLabel("Sample name:"), row, 0)
        form_layout.addWidget(self.sample_name, row, 1)
        row += 1

        self.scanning_quantity = QSpinBox()
        self.scanning_quantity.setRange(1, 9999)
        self.scanning_quantity.setValue(10)
        form_layout.addWidget(QLabel("Scanning quantity:"), row, 0)
        form_layout.addWidget(self.scanning_quantity, row, 1)
        row += 1

        self.initial_wavelength = QSpinBox()
        self.initial_wavelength.setRange(0, 5000)
        self.initial_wavelength.setValue(900)
        form_layout.addWidget(QLabel("Initial wavelength:"), row, 0)
        form_layout.addWidget(self.initial_wavelength, row, 1)
        row += 1

        self.terminal_wavelength = QSpinBox()
        self.terminal_wavelength.setRange(0, 5000)
        self.terminal_wavelength.setValue(1700)
        form_layout.addWidget(QLabel("Terminal wavelength:"), row, 0)
        form_layout.addWidget(self.terminal_wavelength, row, 1)
        row += 1

        self.wavelength_step = QSpinBox()
        self.wavelength_step.setRange(1, 100)
        self.wavelength_step.setValue(1)
        form_layout.addWidget(QLabel("Wavelength step:"), row, 0)
        form_layout.addWidget(self.wavelength_step, row, 1)
        row += 1

        self.user_id = QLineEdit()
        form_layout.addWidget(QLabel("User ID:"), row, 0)
        form_layout.addWidget(self.user_id, row, 1)
        row += 1

        self.remark = QTextEdit()
        form_layout.addWidget(QLabel("Remark:"), row, 0)
        form_layout.addWidget(self.remark, row, 1)
        row += 1

        left_container = QVBoxLayout()
        left_container.addLayout(form_layout)
        left_container.addStretch()

        main_layout.addLayout(left_container, 3)

        # ---------- MIDDLE: SUBSTANCE CONTENT CHECKBOXES ----------
        substance_group = QGroupBox("Substance content:")
        substance_layout = QVBoxLayout(substance_group)

        self.substance_checkboxes = {}
        for name in ["Protein", "Oil", "Moisture"]:
            cb = QCheckBox(name)
            cb.stateChanged.connect(self.on_substance_checkbox_changed)
            substance_layout.addWidget(cb)
            self.substance_checkboxes[name] = cb
        
        substance_layout.addStretch()

        main_layout.addWidget(substance_group, 2)

        # ---------- RIGHT: SUBSTANCE VALUE INPUTS (Dynamic) ----------
        self.substance_values_container = QWidget()
        self.substance_values_layout = QGridLayout(self.substance_values_container)
        self.substance_values_layout.setContentsMargins(0, 0, 0, 0)
        
        main_layout.addWidget(self.substance_values_container, 2)
        
        outer_layout.addLayout(main_layout)

        # ---------- BOTTOM ----------
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.batch_checkbox = QCheckBox("Add in batches")
        bottom_layout.addWidget(self.batch_checkbox)

        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")

        self.btn_ok.clicked.connect(self.validate_and_accept)
        self.btn_cancel.clicked.connect(self.reject)

        bottom_layout.addWidget(self.btn_ok)
        bottom_layout.addWidget(self.btn_cancel)

        outer_layout.addLayout(bottom_layout)
    
    def on_substance_checkbox_changed(self):
        """Show/hide input fields based on checked substances"""
        # Clear existing input fields
        for i in reversed(range(self.substance_values_layout.count())):
            widget = self.substance_values_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        self.substance_inputs.clear()
        
        # Add input fields for checked substances
        row = 0
        for name, checkbox in self.substance_checkboxes.items():
            if checkbox.isChecked():
                label = QLabel(f"{name}:")
                input_field = QLineEdit()
                input_field.setPlaceholderText(f"Enter {name.lower()} value")
                
                self.substance_values_layout.addWidget(label, row, 0)
                self.substance_values_layout.addWidget(input_field, row, 1)
                
                self.substance_inputs[name] = input_field
                row += 1

    def validate_and_accept(self):
        """Validate form before accepting"""
        from PyQt6.QtWidgets import QMessageBox
        
        if not self.sample_name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Sample name is required!")
            self.sample_name.setFocus()
            return
        
        self.accept()

    # ---------- DATA ACCESS ----------
    def get_data(self):
        return {
            "sample_name": self.sample_name.text(),
            "scanning_quantity": self.scanning_quantity.value(),
            "initial_wavelength": self.initial_wavelength.value(),
            "terminal_wavelength": self.terminal_wavelength.value(),
            "wavelength_step": self.wavelength_step.value(),
            "user_id": self.user_id.text(),
            "remark": self.remark.toPlainText(),
            "substance_content": {
                name: self.substance_inputs[name].text()
                for name in self.substance_inputs
                if self.substance_inputs[name].text().strip()
            },
            "add_in_batches": self.batch_checkbox.isChecked()
        }
