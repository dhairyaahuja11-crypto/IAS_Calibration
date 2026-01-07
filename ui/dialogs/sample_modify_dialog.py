from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QTextEdit,
    QSpinBox, QCheckBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox
)


class SampleModifyDialog(QDialog):
    def __init__(self, sample_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sample Information")
        self.resize(650, 420)
        self.sample_data = sample_data
        self._build_ui()
        self._load_data()

    # ---------------- UI ----------------
    def _build_ui(self):
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

        # -------- SUBSTANCE CONTENT --------
        content_group = QGroupBox("Substance content")
        content_layout = QVBoxLayout()

        self.content = {}
        for name in ("Protein", "Oil", "Moisture"):
            cb = QCheckBox(name)
            self.content[name] = cb
            content_layout.addWidget(cb)

        content_group.setLayout(content_layout)
        main_layout.addWidget(content_group, 2)

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

        wrapper = QVBoxLayout(self)
        wrapper.addLayout(main_layout)
        wrapper.addLayout(bottom)

    # ---------------- LOAD DATA ----------------
    def _load_data(self):
        d = self.sample_data

        self.sample_name.setText(d.get("sample_name", ""))
        self.scan_qty.setValue(d.get("scan_quantity", 10))
        self.start_wl.setValue(d.get("initial_wavelength", 900))
        self.end_wl.setValue(d.get("terminal_wavelength", 1700))
        self.wl_step.setValue(d.get("wavelength_step", 1))
        self.user_id.setText(d.get("user_id", ""))
        self.remark.setPlainText(d.get("remark", ""))

        selected = set(d.get("substance_content", []))
        for name, cb in self.content.items():
            cb.setChecked(name in selected)

        self.batch.setChecked(d.get("batch", False))

    # ---------------- EXPORT DATA ----------------
    def get_data(self):
        return {
            "sample_name": self.sample_name.text(),
            "scan_quantity": self.scan_qty.value(),
            "initial_wavelength": self.start_wl.value(),
            "terminal_wavelength": self.end_wl.value(),
            "wavelength_step": self.wl_step.value(),
            "user_id": self.user_id.text(),
            "remark": self.remark.toPlainText(),
            "substance_content": [
                k for k, v in self.content.items() if v.isChecked()
            ],
            "batch": self.batch.isChecked()
        }
