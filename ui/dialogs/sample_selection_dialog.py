from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget,
    QTableWidgetItem, QCheckBox, QDateEdit, QHeaderView, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QDate
from datetime import datetime
from ui.custom_widgets import DateEditWithToday


class SampleSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("sample selection")
        self.resize(1200, 700)
        self.selected_samples = []
        self._build_ui()
        self._connect_signals()
        # Auto-load samples when dialog opens
        self.load_samples()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------------- FILTER SECTION ----------------
        filter_group = QGridLayout()
        
        filter_label = QLabel("filter")
        filter_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(filter_label)

        # Row 0
        filter_group.addWidget(QLabel("sample name:"), 0, 0)
        self.sample_name_edit = QLineEdit()
        filter_group.addWidget(self.sample_name_edit, 0, 1)

        filter_group.addWidget(QLabel("sample status:"), 0, 2)
        self.sample_status_combo = QComboBox()
        self.sample_status_combo.addItems(["all", "Not collected", "Collected"])
        filter_group.addWidget(self.sample_status_combo, 0, 3)

        filter_group.addWidget(QLabel("User ID:"), 0, 4)
        self.user_id_edit = QLineEdit()
        filter_group.addWidget(self.user_id_edit, 0, 5)

        filter_group.addWidget(QLabel("creation time:"), 0, 6)
        
        # Date range
        self.date_from = DateEditWithToday(QDate.currentDate().addMonths(-3))
        self.date_from.setDisplayFormat("d MMMM, yyyy")
        filter_group.addWidget(self.date_from, 0, 7)

        filter_group.addWidget(QLabel("-"), 0, 8)

        self.date_to = DateEditWithToday(QDate.currentDate())
        self.date_to.setDisplayFormat("d MMMM, yyyy")
        filter_group.addWidget(self.date_to, 0, 9)

        # Display by merged sample checkbox
        self.merged_sample_checkbox = QCheckBox("display by merged sample")
        filter_group.addWidget(self.merged_sample_checkbox, 0, 10)

        # Inquiry button
        self.inquiry_btn = QPushButton("inquiry")
        filter_group.addWidget(self.inquiry_btn, 0, 11)

        main_layout.addLayout(filter_group)

        # ---------------- SAMPLE TABLE ----------------
        self.sample_table = QTableWidget(0, 10)
        
        # Create header labels
        header_labels = [
            "", "new sample name", "sample name", "sample quantity",
            "scanned number", "substance content", "scanning method",
            "sample status", "User ID", "creation time"
        ]
        self.sample_table.setHorizontalHeaderLabels(header_labels)
        
        # Set column widths
        header = self.sample_table.horizontalHeader()
        self.sample_table.setColumnWidth(0, 50)  # Checkbox column
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)

        # Enable sorting
        self.sample_table.setSortingEnabled(True)
        
        # Enable selection
        self.sample_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        main_layout.addWidget(self.sample_table)
        
        # Add select all checkbox to header after table is added
        self.select_all_checkbox = QCheckBox()
        self.select_all_checkbox.stateChanged.connect(self.on_select_all_changed)
        
        # Get the header's viewport and add checkbox
        header_widget = QWidget(header)
        header_layout = QHBoxLayout(header_widget)
        header_layout.addWidget(self.select_all_checkbox)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_widget.setGeometry(0, 0, 50, header.height())
        header_widget.show()

        # ---------------- BOTTOM BUTTONS ----------------
        btn_layout = QHBoxLayout()

        self.merge_btn = QPushButton("merge")
        self.cancel_merge_btn = QPushButton("Cancel the merger")
        self.tick_btn = QPushButton("tick")

        btn_layout.addWidget(self.merge_btn)
        btn_layout.addWidget(self.cancel_merge_btn)
        btn_layout.addWidget(self.tick_btn)
        btn_layout.addStretch()

        self.ok_btn = QPushButton("include")
        self.cancel_btn = QPushButton("cancel")

        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(btn_layout)

    def _connect_signals(self):
        """Connect button signals"""
        self.inquiry_btn.clicked.connect(self.load_samples)
        self.ok_btn.clicked.connect(self.on_ok_clicked)
        self.cancel_btn.clicked.connect(self.reject)
        self.merge_btn.clicked.connect(self.merge_samples)
        self.cancel_merge_btn.clicked.connect(self.cancel_merge)
        self.tick_btn.clicked.connect(self.tick_all)

    def load_samples(self):
        """Load samples based on filter criteria"""
        try:
            from services.sample_service import SampleService
            
            # Get filter values
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
            sample_name = self.sample_name_edit.text().strip()
            sample_status = self.sample_status_combo.currentText()
            user_id = self.user_id_edit.text().strip()
            
            print(f"Loading samples from {date_from} to {date_to}")
            
            # Fetch samples from database with filters
            samples = SampleService.get_samples_by_date(
                date_from, 
                date_to,
                sample_name=sample_name if sample_name else None,
                user_id=user_id if user_id else None
            )
            
            print(f"Fetched {len(samples)} samples from database")
            
            # Apply additional filters (sample_status is not in database query)
            # Note: sample_name and user_id are now filtered at database level
            
            if sample_status != "all":
                samples = [s for s in samples if s.get('sample_status') == sample_status]
                print(f"After status filter: {len(samples)} samples")
            
            # Store original samples for reference
            self._original_samples = samples
            
            # Group samples by (sample_name, creation_time) combination - same as sample management
            grouped_samples = {}
            for sample in samples:
                sample_name = sample.get('sample_name', '')
                creation_time = sample.get('creation_time', '')
                
                # Truncate creation_time to minute precision (ignore seconds)
                creation_time_minute = creation_time[:16] if len(creation_time) >= 16 else creation_time
                
                # Create unique key using sample_name and time up to minute
                group_key = (sample_name, creation_time_minute)
                
                if group_key not in grouped_samples:
                    # First occurrence - use this as representative
                    grouped_samples[group_key] = sample.copy()
                    grouped_samples[group_key]['model_ids'] = [sample.get('id', '')]  # For display/operations
                    grouped_samples[group_key]['sample_ids'] = [sample.get('sample_id', '')]  # For template export
                    grouped_samples[group_key]['replicate_count'] = 1
                else:
                    # Additional replicate at same time - update count and IDs
                    grouped_samples[group_key]['model_ids'].append(sample.get('id', ''))
                    grouped_samples[group_key]['sample_ids'].append(sample.get('sample_id', ''))
                    grouped_samples[group_key]['replicate_count'] += 1
                    
                    # Always update substance_content if current sample has it (prefer non-empty)
                    current_substance = sample.get('substance_content', '').strip()
                    existing_substance = grouped_samples[group_key].get('substance_content', '').strip()
                    
                    if current_substance and not existing_substance:
                        # Current has content but existing doesn't - use current
                        grouped_samples[group_key]['substance_content'] = current_substance
                    elif current_substance and existing_substance and len(current_substance) > len(existing_substance):
                        # Both have content - use the longer/more complete one
                        grouped_samples[group_key]['substance_content'] = current_substance
                    
                    # Update scanned_number to sum all scans at this time
                    grouped_samples[group_key]['scanned_number'] = str(
                        int(grouped_samples[group_key].get('scanned_number', 0)) + 
                        int(sample.get('scanned_number', 0))
                    )
            
            # Convert back to list and use first model_id as group ID
            grouped_list = []
            for group_key, sample_data in grouped_samples.items():
                # Use first model_id from the group as the representative ID
                model_ids = sample_data.get('model_ids', [])
                if model_ids:
                    sample_data['id'] = str(model_ids[0])  # Use real database model_id
                grouped_list.append(sample_data)
            
            # Sort by creation_time descending (newest first)
            grouped_list.sort(key=lambda x: x.get('creation_time', ''), reverse=True)
            
            # Populate table with grouped samples
            self.populate_table(grouped_list)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load samples: {str(e)}")

    def populate_table(self, samples):
        """Populate the table with sample data"""
        print(f"Populating table with {len(samples)} samples")
        
        self.sample_table.setRowCount(0)
        self.sample_table.setSortingEnabled(False)
        
        # Set the select all checkbox in the header
        self.sample_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header = self.sample_table.horizontalHeader()
        
        for idx, sample in enumerate(samples):
            print(f"Adding sample {idx}: {sample.get('sample_name', 'N/A')}")
            
            row = self.sample_table.rowCount()
            self.sample_table.insertRow(row)
            
            # Checkbox column
            checkbox = QCheckBox()
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.sample_table.setCellWidget(row, 0, checkbox_widget)
            
            # Store ALL sample IDs (for grouped samples) in checkbox for later retrieval
            sample_ids = sample.get('sample_ids', [sample.get('id')])
            checkbox.setProperty("sample_id", sample_ids[0])  # Store first ID
            checkbox.setProperty("sample_ids", sample_ids)  # Store all IDs for grouped samples
            
            # Data columns
            # Fix creation_time if it's bytes
            creation_time = sample.get('creation_time', '')
            if isinstance(creation_time, bytes):
                creation_time = creation_time.decode('utf-8')
            
            substance_content = sample.get('substance_content', '')
            if isinstance(substance_content, bytes):
                substance_content = substance_content.decode('utf-8')
            
            user_id = sample.get('user_id', '')
            if isinstance(user_id, bytes):
                user_id = user_id.decode('utf-8')
            
            sample_name = sample.get('sample_name', '')
            if isinstance(sample_name, bytes):
                sample_name = sample_name.decode('utf-8')
            
            columns = [
                '',  # new_sample_name - empty for now, used for merged samples
                str(sample_name),
                str(sample.get('sample_quantity', '0')),
                str(sample.get('scanned_number', '0')),
                str(substance_content),
                str(sample.get('scanning_method', '0')),
                str(sample.get('sample_status', 'Not collected')),
                str(user_id),
                str(creation_time)
            ]
            
            for col, value in enumerate(columns, start=1):
                item = QTableWidgetItem(value if value else '')
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.sample_table.setItem(row, col, item)
        
        self.sample_table.setSortingEnabled(True)
        print(f"Table population complete. Row count: {self.sample_table.rowCount()}")

    def get_selected_samples(self):
        """Get list of selected sample IDs (includes ALL replicates)"""
        selected = []
        
        for row in range(self.sample_table.rowCount()):
            checkbox_widget = self.sample_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    # Get all sample IDs (for grouped samples, this includes all replicates)
                    sample_ids = checkbox.property("sample_ids")
                    if not sample_ids:
                        # Fallback to single ID if sample_ids not set
                        sample_ids = [checkbox.property("sample_id")]
                    
                    # Add ALL replicate sample IDs
                    for sample_id in sample_ids:
                        sample_data = {
                            'id': sample_id,
                            'sample_name': self.sample_table.item(row, 2).text() if self.sample_table.item(row, 2) else '',
                            'sample_quantity': self.sample_table.item(row, 3).text() if self.sample_table.item(row, 3) else '0',
                            'scanned_number': self.sample_table.item(row, 4).text() if self.sample_table.item(row, 4) else '0',
                            'substance_content': self.sample_table.item(row, 5).text() if self.sample_table.item(row, 5) else '',
                            'scanning_method': self.sample_table.item(row, 6).text() if self.sample_table.item(row, 6) else '',
                            'sample_status': self.sample_table.item(row, 7).text() if self.sample_table.item(row, 7) else '',
                            'user_id': self.sample_table.item(row, 8).text() if self.sample_table.item(row, 8) else '',
                            'creation_time': self.sample_table.item(row, 9).text() if self.sample_table.item(row, 9) else ''
                        }
                        selected.append(sample_data)
        return selected

    def on_ok_clicked(self):
        """Handle OK button click"""
        self.selected_samples = self.get_selected_samples()
        if not self.selected_samples:
            QMessageBox.warning(self, "Warning", "Please select at least one sample.")
            return
        self.accept()

    def merge_samples(self):
        """Merge selected samples"""
        selected = self.get_selected_samples()
        if len(selected) < 2:
            QMessageBox.warning(self, "Warning", "Please select at least 2 samples to merge.")
            return
        
        # TODO: Implement merge logic
        QMessageBox.information(self, "Info", f"Merging {len(selected)} samples...")

    def cancel_merge(self):
        """Cancel merge operation"""
        # TODO: Implement cancel merge logic
        QMessageBox.information(self, "Info", "Merge cancelled.")
    
    def tick_all(self):
        """Toggle checkboxes for SELECTED rows only"""
        selected_rows = set()
        for item in self.sample_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            # If no rows selected, show warning
            QMessageBox.warning(self, "Warning", "Please select rows first by clicking on them.")
            return
        
        # Check if any of the selected rows have checked checkbox
        any_checked = False
        for row in selected_rows:
            checkbox_widget = self.sample_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    any_checked = True
                    break
        
        # Toggle checkboxes for selected rows only
        new_state = not any_checked
        for row in selected_rows:
            checkbox_widget = self.sample_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(new_state)
    
    def on_select_all_changed(self, state):
        """Handle select all checkbox in header - checks/unchecks all row checkboxes"""
        is_checked = (state == Qt.CheckState.Checked.value)
        for row in range(self.sample_table.rowCount()):
            checkbox_widget = self.sample_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(is_checked)
