import os
from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QRadioButton,
    QButtonGroup, QFileDialog, QMessageBox, QListWidget
)

class DataImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_paths = []
        self.selected_folders = []  # Track folders separately for multi-add
        self.setWindowTitle("Data Import")
        self.resize(520, 420)
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
        self.format_combo.addItems(["csv"])
        self.form.addWidget(self.format_combo, 1, 3)

        self.form.addWidget(QLabel("path:"), 2, 0)
        self.path_edit = QLineEdit()
        # Allow manual typing (setReadOnly removed)
        self.form.addWidget(self.path_edit, 2, 1, 1, 2)

        self.btn_browse = QPushButton("Browse..." if self.rb_file.isChecked() else "Add Folder")
        self.form.addWidget(self.btn_browse, 2, 3)

        # Folder list widget (shown only in folder mode)
        self.folder_list_label = QLabel("Selected folders:")
        self.folder_list = QListWidget()
        self.folder_list.setMaximumHeight(80)
        self.btn_remove_folder = QPushButton("Remove Selected")
        self.btn_remove_folder.clicked.connect(self.on_remove_folder)
        
        self.form.addWidget(self.folder_list_label, 3, 0, 1, 4)
        self.form.addWidget(self.folder_list, 4, 0, 1, 4)
        self.form.addWidget(self.btn_remove_folder, 5, 0, 1, 4)
        
        # Initially hide folder list widgets
        self.folder_list_label.hide()
        self.folder_list.hide()
        self.btn_remove_folder.hide()

        main_layout.addLayout(self.form)

        # ---------- BUTTONS ----------
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")

        self.btn_ok.clicked.connect(self.on_ok)     # ✅ VALIDATION
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_browse.clicked.connect(self.on_browse_clicked)
        self.format_combo.currentTextChanged.connect(self.on_format_changed)

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(btn_layout)

    def _connect_radio_signals(self):
        """Connect radio button signals to update form visibility."""
        self.rb_file.toggled.connect(self._update_form_visibility)
        self.rb_folder.toggled.connect(self._update_form_visibility)

    def _update_form_visibility(self):
        """Update UI based on selected mode (file vs folder)."""
        is_folder_mode = self.rb_folder.isChecked()
        
        # Update button text
        self.btn_browse.setText("Add Folder" if is_folder_mode else "Browse...")
        
        # Show/hide folder list widgets
        if is_folder_mode:
            self.folder_list_label.show()
            self.folder_list.show()
            self.btn_remove_folder.show()
        else:
            self.folder_list_label.hide()
            self.folder_list.hide()
            self.btn_remove_folder.hide()
        
        self.separator_label.show()
        self.separator_edit.show()
        
    def on_browse_clicked(self):
        """Handle browse button click - open file or folder dialog based on selected radio button."""
        # 📄 File-based import - allow multiple file selection
        if self.rb_file.isChecked():
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Select data file(s)",
                "",
                "CSV Files (*.csv);;All Files (*)"
            )
            if file_paths:
                if len(file_paths) == 1:
                    self.path_edit.setText(file_paths[0])
                else:
                    # Show first file and count
                    first_file = os.path.basename(file_paths[0])
                    self.path_edit.setText(f"{first_file} and {len(file_paths)-1} more file(s)")
                self.selected_paths = file_paths

        # 📁 Folder-based import - use native dialog to add folders one at a time
        elif self.rb_folder.isChecked():
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select a folder",
                "",
                QFileDialog.Option.ShowDirsOnly
            )
            
            if folder_path:
                # Add folder to list if not already present
                if folder_path not in self.selected_folders:
                    self.selected_folders.append(folder_path)
                    self.folder_list.addItem(folder_path)
                    self._update_folder_summary()
                else:
                    QMessageBox.information(
                        self,
                        "Duplicate Folder",
                        "This folder has already been added."
                    )
    
    def on_remove_folder(self):
        """Remove selected folder(s) from the list."""
        selected_items = self.folder_list.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            folder_path = item.text()
            if folder_path in self.selected_folders:
                self.selected_folders.remove(folder_path)
            self.folder_list.takeItem(self.folder_list.row(item))
        
        self._update_folder_summary()
    
    def _update_folder_summary(self):
        """Update the summary in path_edit based on selected folders."""
        if not self.selected_folders:
            self.path_edit.clear()
            self.selected_paths = []
            return
        
        # Collect files from all selected folders
        fmt = self.format_combo.currentText().strip().lower()
        allowed = None
        if fmt and fmt != "all":
            allowed = {'.' + fmt}

        found = []
        for folder_path in self.selected_folders:
            for root, dirs, files in os.walk(folder_path):
                for f in files:
                    if allowed is None or os.path.splitext(f)[1].lower() in allowed:
                        found.append(os.path.join(root, f))

        self.selected_paths = found
        
        # Update path_edit with summary
        folder_count = len(self.selected_folders)
        file_count = len(found)
        
        if folder_count == 1:
            self.path_edit.setText(f"{self.selected_folders[0]} ({file_count} files)")
        else:
            self.path_edit.setText(f"{folder_count} folders selected ({file_count} files)")
        
        if file_count == 0:
            QMessageBox.information(
                self,
                "No files",
                "No files matching the selected format were found in the chosen folder(s)."
            )
    
    def on_format_changed(self):
        """Update folder summary when format selection changes."""
        if self.rb_folder.isChecked() and self.selected_folders:
            self._update_folder_summary()

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