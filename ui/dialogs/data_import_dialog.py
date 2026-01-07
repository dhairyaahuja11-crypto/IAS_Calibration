from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QRadioButton,
    QButtonGroup
)


class DataImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data Import")
        self.resize(520, 260)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------- TOP RADIO OPTIONS ----------
        radio_layout = QGridLayout()

        self.rb_choose = QRadioButton("choose a sample")
        self.rb_add = QRadioButton("add a sample")
        self.rb_file = QRadioButton("add new samples named after file names")
        self.rb_folder = QRadioButton("add new samples named after folder")

        self.rb_choose.setChecked(True)

        self.radio_group = QButtonGroup(self)
        for rb in [self.rb_choose, self.rb_add, self.rb_file, self.rb_folder]:
            self.radio_group.addButton(rb)

        radio_layout.addWidget(self.rb_choose, 0, 0)
        radio_layout.addWidget(self.rb_add, 0, 1)
        radio_layout.addWidget(self.rb_file, 1, 0)
        radio_layout.addWidget(self.rb_folder, 1, 1)

        main_layout.addLayout(radio_layout)

        # ---------- FORM ----------
        form = QGridLayout()

        form.addWidget(QLabel("sample name:"), 0, 0)
        self.sample_combo = QComboBox()
        self.sample_combo.addItems(["emam-700-280622"])
        form.addWidget(self.sample_combo, 0, 1)

        form.addWidget(QLabel("lot number:"), 0, 2)
        self.lot_edit = QLineEdit()
        form.addWidget(self.lot_edit, 0, 3)

        form.addWidget(QLabel("instrument:"), 1, 0)
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(["3120", "5100", "5200"])
        form.addWidget(self.instrument_combo, 1, 1)

        form.addWidget(QLabel("file format:"), 1, 2)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["", "csv", "txt", "dat"])
        form.addWidget(self.format_combo, 1, 3)

        form.addWidget(QLabel("path:"), 2, 0)
        self.path_edit = QLineEdit()
        form.addWidget(self.path_edit, 2, 1, 1, 2)

        self.btn_browse = QPushButton("...")
        form.addWidget(self.btn_browse, 2, 3)

        main_layout.addLayout(form)

        # ---------- BUTTONS ----------
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(btn_layout)
