from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QTextEdit,
    QSpinBox, QCheckBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QWidget
)


class SampleModifyDialog(QDialog):
    def __init__(self, sample_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sample Information")
        self.resize(750, 420)
        self.sample_data = sample_data
        self.substance_inputs = {}
        self._build_ui()
        self._load_data()

    # ---------------- UI ----------------
    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        
        main_layout = QHBoxLayout()

        # -------- LEFT FORM --------
        form = QGridLayout()
        row = 0

        self.sample_name = QLineEdit()
        form.addWidget(QLabel("Sample name:"), row, 0)
        form.addWidget(self.sample_name, row, 1)
        row += 1

        self.scan_qty = QSpinBox()
        self.scan_qty.setRange(1, 9999)
        form.addWidget(QLabel("Scanning quantity:"), row, 0)
        form.addWidget(self.scan_qty, row, 1)
        row += 1

        self.start_wl = QSpinBox()
        self.start_wl.setRange(0, 5000)
        form.addWidget(QLabel("Initial wavelength:"), row, 0)
        form.addWidget(self.start_wl, row, 1)
        row += 1

        self.end_wl = QSpinBox()
        self.end_wl.setRange(0, 5000)
        form.addWidget(QLabel("Terminal wavelength:"), row, 0)
        form.addWidget(self.end_wl, row, 1)
        row += 1

        self.wl_step = QSpinBox()
        self.wl_step.setRange(1, 100)
        form.addWidget(QLabel("Wavelength step:"), row, 0)
        form.addWidget(self.wl_step, row, 1)
        row += 1

        self.user_id = QLineEdit()
        form.addWidget(QLabel("User ID:"), row, 0)
        form.addWidget(self.user_id, row, 1)
        row += 1

        self.remark = QTextEdit()
        form.addWidget(QLabel("Remark:"), row, 0)
        form.addWidget(self.remark, row, 1)

        left_box = QVBoxLayout()
        left_box.addLayout(form)
        left_box.addStretch()

        main_layout.addLayout(left_box, 3)

        # -------- MIDDLE: SUBSTANCE CONTENT CHECKBOXES --------
        content_group = QGroupBox("Substance content:")
        content_layout = QVBoxLayout(content_group)

        self.content = {}
        # Load checkboxes dynamically from content_dictionary
        self._load_content_checkboxes(content_layout)
        
        content_layout.addStretch()

        main_layout.addWidget(content_group, 2)

        # -------- RIGHT: SUBSTANCE VALUE INPUTS (Dynamic) --------
        self.substance_values_container = QWidget()
        self.substance_values_layout = QGridLayout(self.substance_values_container)
        self.substance_values_layout.setContentsMargins(0, 0, 0, 0)
        
        main_layout.addWidget(self.substance_values_container, 2)
        
        outer_layout.addLayout(main_layout)

        # -------- BOTTOM BUTTONS --------
        bottom = QHBoxLayout()
        bottom.addStretch()

        self.batch = QCheckBox("Add in batches")
        bottom.addWidget(self.batch)

        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        bottom.addWidget(ok_btn)
        bottom.addWidget(cancel_btn)

        outer_layout.addLayout(bottom)
    
    def on_substance_checkbox_changed(self):
        """Show/hide input fields based on checked substances"""
        # Save current values before clearing
        current_values = {}
        for name, input_field in self.substance_inputs.items():
            value = input_field.text()
            if value:
                current_values[name] = value
        
        # Clear existing input fields
        for i in reversed(range(self.substance_values_layout.count())):
            widget = self.substance_values_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        self.substance_inputs.clear()
        
        # Add input fields for checked substances
        row = 0
        for name, checkbox in self.content.items():
            if checkbox.isChecked():
                label = QLabel(f"{name}:")
                input_field = QLineEdit()
                input_field.setPlaceholderText(f"Enter {name.lower()} value")
                
                # Restore previous value if it existed
                if name in current_values:
                    input_field.setText(current_values[name])
                
                self.substance_values_layout.addWidget(label, row, 0)
                self.substance_values_layout.addWidget(input_field, row, 1)
                
                self.substance_inputs[name] = input_field
                row += 1
    
    def _load_content_checkboxes(self, layout):
        """Load substance content checkboxes from database"""
        from database.db import get_connection
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT content_name FROM content_dictionary ORDER BY id")
            content_names = [row['content_name'] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            for name in content_names:
                cb = QCheckBox(name)
                cb.stateChanged.connect(self.on_substance_checkbox_changed)
                self.content[name] = cb
                layout.addWidget(cb)
        except Exception as e:
            print(f"Error loading content checkboxes: {e}")
            # Fallback to default checkboxes
            for name in ("Protein", "Oil", "Moisture", "Fat"):
                cb = QCheckBox(name)
                cb.stateChanged.connect(self.on_substance_checkbox_changed)
                self.content[name] = cb
                layout.addWidget(cb)

    # ---------------- LOAD DATA ----------------
    def _load_data(self):
        d = self.sample_data

        self.sample_name.setText(d.get("sample_name", ""))
        self.scan_qty.setValue(int(d.get("scan_quantity", 10)))
        self.start_wl.setValue(int(d.get("initial_wavelength", 900)))
        self.end_wl.setValue(int(d.get("terminal_wavelength", 1700)))
        self.wl_step.setValue(int(d.get("wavelength_step", 1)))
        self.user_id.setText(d.get("user_id", ""))
        
        # Load substance content values from database (all 10 properties)
        from database.db import get_connection
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, content_name FROM content_dictionary")
            id_to_name = {row['id']: row['content_name'] for row in cursor.fetchall()}
            cursor.close()
            conn.close()
            
            # Collect property values from all 10 property slots
            property_values = {}
            
            for i in range(1, 11):
                prop_name_key = f"property_name{i}"
                prop_value_key = f"property_value{i}"
                
                prop_name_id = d.get(prop_name_key)
                prop_value = d.get(prop_value_key)
                
                # Check if both property name ID and value exist (allow 0 as valid ID)
                if prop_name_id is not None and prop_value:
                    # Convert to int if it's a string (database returns string sometimes)
                    if isinstance(prop_name_id, str):
                        prop_name_id = int(prop_name_id)
                    
                    prop_name = id_to_name.get(prop_name_id, "")
                    if prop_name and prop_name in self.content:
                        property_values[prop_name] = str(prop_value)
            
            # Block signals and check the checkboxes for existing properties
            for prop_name in property_values.keys():
                if prop_name in self.content:
                    self.content[prop_name].blockSignals(True)
                    self.content[prop_name].setChecked(True)
                    self.content[prop_name].blockSignals(False)
            
            # Trigger on_substance_checkbox_changed to create input fields
            self.on_substance_checkbox_changed()
            
            # Now populate the input field values
            for prop_name, prop_value in property_values.items():
                if prop_name in self.substance_inputs:
                    self.substance_inputs[prop_name].setText(prop_value)
                    
        except Exception as e:
            print(f"Error loading substance content: {e}")
            import traceback
            traceback.print_exc()

    # ---------------- EXPORT DATA ----------------
    def get_data(self):
        return {
            "sample_name": self.sample_name.text(),
            "scan_quantity": self.scan_qty.value(),
            "initial_wavelength": self.start_wl.value(),
            "terminal_wavelength": self.end_wl.value(),
            "wavelength_step": self.wl_step.value(),
            "user_id": self.user_id.text(),
            "substance_content": {
                name: self.substance_inputs[name].text()
                for name in self.substance_inputs
                if self.substance_inputs[name].text().strip()
            }
        }
