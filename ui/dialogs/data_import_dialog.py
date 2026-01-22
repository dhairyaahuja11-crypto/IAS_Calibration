import os
from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QRadioButton,
    QButtonGroup, QFileDialog, QMessageBox
)

class DataImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_paths = []
        self.setWindowTitle("Data Import")
        self.resize(520, 310)
        self._build_ui()
        self._connect_radio_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------- TOP RADIO OPTIONS ----------
        radio_layout = QGridLayout()


        self.rb_file = QRadioButton("add new samples named after file names")
        self.rb_folder = QRadioButton("add new samples named after folder")
        self.rb_file.setChecked(True)
        self.radio_group = QButtonGroup(self)
        for rb in [self.rb_file, self.rb_folder]:
            self.radio_group.addButton(rb)
        radio_layout.addWidget(self.rb_file, 0, 0)
        radio_layout.addWidget(self.rb_folder, 0, 1)

        main_layout.addLayout(radio_layout)

        # ---------- FORM ----------
        self.form = QGridLayout()


        # Separator character (always shown)
        self.separator_label = QLabel("use the text before the file or folder name '_' as the sar lot number:")
        self.separator_edit = QLineEdit("_")
        self.separator_edit.setMaximumWidth(100)
        self.form.addWidget(self.separator_label, 0, 0, 1, 3)
        self.form.addWidget(self.separator_edit, 0, 3)

        self.form.addWidget(QLabel("instrument:"), 1, 0)
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItem("(none)")
        self.instrument_combo.addItems(["3120", "5100", "5200", "AG9170", "AG6011"])
        self.form.addWidget(self.instrument_combo, 1, 1)

        self.form.addWidget(QLabel("file format:"), 1, 2)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["csv", "txt", "dat"])
        self.form.addWidget(self.format_combo, 1, 3)

        self.form.addWidget(QLabel("path:"), 2, 0)
        self.path_edit = QLineEdit()
        # Allow manual typing (setReadOnly removed)
        self.form.addWidget(self.path_edit, 2, 1, 1, 2)

        self.btn_browse = QPushButton("...")
        self.form.addWidget(self.btn_browse, 2, 3)

        main_layout.addLayout(self.form)

        # ---------- BUTTONS ----------
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")

        self.btn_ok.clicked.connect(self.on_ok)     # ✅ VALIDATION
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_browse.clicked.connect(self.on_browse_clicked)

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(btn_layout)

    def _connect_radio_signals(self):
        """Connect radio button signals to update form visibility."""
        self.rb_file.toggled.connect(self._update_form_visibility)
        self.rb_folder.toggled.connect(self._update_form_visibility)

    def _update_form_visibility(self):
        """Show only separator fields for both options."""
        self.separator_label.show()
        self.separator_edit.show()
        
    def on_browse_clicked(self):
        """Handle browse button click - open file or folder dialog based on selected radio button."""
        # 📄 File-based import
        if self.rb_file.isChecked():
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select data file",
                "",
                "Data Files (*.csv *.txt *.dat);;All Files (*)"
            )
            if file_path:
                self.path_edit.setText(file_path)
                self.selected_paths = [file_path]

        # 📁 Folder-based import
        elif self.rb_folder.isChecked():
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select data folder",
                ""
            )
            if folder_path:
                # collect files under the folder (recursively) matching selected format
                fmt = self.format_combo.currentText().strip().lower()
                allowed = None
                if fmt and fmt != "all":
                    allowed = {'.' + fmt}

                found = []
                for root, dirs, files in os.walk(folder_path):
                    for f in files:
                        if allowed is None or os.path.splitext(f)[1].lower() in allowed:
                            found.append(os.path.join(root, f))

                self.selected_paths = found
                if found:
                    self.path_edit.setText(folder_path + f" ({len(found)} files)")
                else:
                    self.path_edit.setText(folder_path)
                    QMessageBox.information(
                        self,
                        "No files",
                        "No files matching the selected format were found in the chosen folder."
                    )
        # Always update selected_paths if user types manually
        else:
            manual_path = self.path_edit.text().strip()
            if manual_path:
                self.selected_paths = [manual_path]

    # ================= OK HANDLER =================
    def on_ok(self):
        if not self.selected_paths:
            QMessageBox.warning(
                self,
                "Missing file",
                "Please select a file or folder to import."
            )
            return

        self.accept()

    # ================= DATA ACCESS =================
    def get_data(self):
        return {
            "mode": self.radio_group.checkedButton().text(),
            "instrument": self.instrument_combo.currentText(),
            "format": self.format_combo.currentText(),
            "path": self.path_edit.text(),
            "paths": self.selected_paths,
            "separator": self.separator_edit.text()
        }