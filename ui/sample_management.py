from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QDateEdit, QTableWidget, QTableWidgetItem,
    QCheckBox, QHeaderView, QMessageBox
)
from ui.custom_widgets import DateEditWithToday

# Sortable table item for proper numerical sorting
class SortableTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        # Use UserRole for sorting if available, else fallback to text
        try:
            my_data = self.data(Qt.ItemDataRole.UserRole)
            other_data = other.data(Qt.ItemDataRole.UserRole)
            # Try to compare as numbers if possible
            if isinstance(my_data, (int, float)) and isinstance(other_data, (int, float)):
                return my_data < other_data
            # Fallback to string comparison
            return str(my_data) < str(other_data)
        except Exception:
            return super().__lt__(other)

from PyQt6.QtCore import Qt, QDate, QRect, pyqtSignal
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.sample_service import SampleService

# 🔴 Dialog imports
from ui.dialogs.sample_add_dialog import SampleAddDialog
from ui.dialogs.sample_modify_dialog import SampleModifyDialog

# 👉 IMPORT SHARED SERVICE
from services.spectral_import_service import SpectralImportService


class CheckBoxHeader(QHeaderView):
    """Custom header with checkbox for select all functionality"""
    stateChanged = pyqtSignal(int)

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._checked = False
        self._rect = QRect()
        self.setSectionsClickable(True)

    def paintSection(self, painter, rect, logicalIndex):
        super().paintSection(painter, rect, logicalIndex)
        if logicalIndex == 0:
            from PyQt6.QtWidgets import QStyleOptionButton, QStyle
            option = QStyleOptionButton()
            option.rect = self._get_checkbox_rect(rect)
            option.state = QStyle.StateFlag.State_Enabled
            if self._checked:
                option.state |= QStyle.StateFlag.State_On
            else:
                option.state |= QStyle.StateFlag.State_Off
            self.style().drawControl(QStyle.ControlElement.CE_CheckBox, option, painter)
            self._rect = option.rect

    def mousePressEvent(self, event):
        if self._rect.contains(event.pos()):
            self._checked = not self._checked
            self.stateChanged.emit(self._checked)
            self.updateSection(0)
        else:
            super().mousePressEvent(event)

    def setChecked(self, checked):
        self._checked = checked
        self.updateSection(0)

    def isChecked(self):
        return self._checked

    def _get_checkbox_rect(self, rect):
        from PyQt6.QtWidgets import QStyleOptionButton
        opt = QStyleOptionButton()
        checkbox_size = self.style().subElementRect(
            self.style().SubElement.SE_CheckBoxIndicator, opt, None
        ).size()
        x = rect.x() + (rect.width() - checkbox_size.width()) // 2
        y = rect.y() + (rect.height() - checkbox_size.height()) // 2
        return QRect(x, y, checkbox_size.width(), checkbox_size.height())


class SampleManagementUI(QWidget):
    def __init__(self):
        super().__init__()
        self._inquiry_run = False  # Track if inquiry has been run at least once
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Visual polish only (no workflow or structure changes)
        self.setObjectName("sampleManagementRoot")
        self.setStyleSheet("""
            QWidget#sampleManagementRoot {
                background-color: #f6f8fb;
            }
            QLabel {
                color: #1f2937;
                font-size: 12px;
            }
            QLineEdit, QComboBox, QDateEdit {
                background-color: #ffffff;
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #7aa7ff;
            }
            QPushButton {
                background-color: #ffffff;
                color: #1f2937;
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 30px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f2f6ff;
                border-color: #aac2ef;
            }
            QPushButton:pressed {
                background-color: #e7efff;
            }
        """)

        # ---------------- FILTER AREA ----------------
        filter_layout = QGridLayout()
        filter_layout.setHorizontalSpacing(10)
        filter_layout.setVerticalSpacing(8)

        filter_layout.addWidget(QLabel("Sample name:"), 0, 0)
        self.sample_name = QLineEdit()
        filter_layout.addWidget(self.sample_name, 0, 1)

        filter_layout.addWidget(QLabel("Sample status:"), 0, 2)
        self.sample_status = QComboBox()
        self.sample_status.addItems([
            "all", "Not Collected", "Collected", "Completed"
        ])
        filter_layout.addWidget(self.sample_status, 0, 3)

        filter_layout.addWidget(QLabel("User ID:"), 0, 4)
        self.user_id = QLineEdit()
        # Set default value from Windows username, but allow editing
        import getpass
        self.user_id.setText(getpass.getuser())
        filter_layout.addWidget(self.user_id, 0, 5)

        filter_layout.addWidget(QLabel("Creation time:"), 0, 6)

        self.date_from = DateEditWithToday()
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd MMMM yyyy")

        self.date_to = DateEditWithToday()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd MMMM yyyy")

        filter_layout.addWidget(self.date_from, 0, 7)
        filter_layout.addWidget(self.date_to, 0, 8)

        main_layout.addLayout(filter_layout)

        # ---------------- BUTTON BAR ----------------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_inquiry = QPushButton("Inquiry")
        self.btn_add = QPushButton("Add")
        self.btn_modify = QPushButton("Modify")
        self.btn_delete = QPushButton("Delete")
        self.btn_tick = QPushButton("Tick")
        self.btn_clear_selection = QPushButton("Clear Selection")
        self.btn_batch_import = QPushButton("Batch import substance content")

        btn_layout.addWidget(self.btn_inquiry)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_modify)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_tick)
        btn_layout.addWidget(self.btn_clear_selection)
        btn_layout.addWidget(self.btn_batch_import)

        self.template_download = QLabel('<a href="#">template download</a>')
        self.template_download.setObjectName("templateDownloadLink")
        self.template_download.setTextFormat(Qt.TextFormat.RichText)
        self.template_download.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.template_download.setOpenExternalLinks(False)
        self.template_download.setStyleSheet("""
            QLabel#templateDownloadLink {
                color: #2563eb;
                font-weight: 600;
                border: none;
                background: transparent;
                padding-left: 6px;
            }
        """)

        btn_layout.addWidget(self.template_download)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # ---------------- TABLE ----------------
        self.table = QTableWidget(0, 13)
        self.table.setHorizontalHeaderLabels([
            "", "ID", "Sample Name", "Sample Quantity", 
            "Initial Wavelength", "Terminal Wavelength", "Wavelength Step",
            "Scanning Method", "Substance Content", "Scanned Number",
            "Sample Status", "User ID", "Creation Time"
        ])
        
        # Replace header with custom checkbox header
        self.checkbox_header = CheckBoxHeader(Qt.Orientation.Horizontal, self.table)
        self.table.setHorizontalHeader(self.checkbox_header)
        self.checkbox_header.stateChanged.connect(self.on_header_checkbox_changed)
        
        # Configure table
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setShowGrid(True)
        
        # Adjust column widths
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setDefaultSectionSize(120)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 30)  # Checkbox column
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Sample name stretches
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)  # Substance content stretches
        header.setSectionResizeMode(12, QHeaderView.ResizeMode.ResizeToContents)  # Creation Time auto-resizes
        header.setStretchLastSection(False)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8fbff;
                color: #111827;
                border: 1px solid #d8e1eb;
                border-radius: 6px;
                selection-background-color: #dbeafe;
                selection-color: #0f172a;
                gridline-color: #e5ebf2;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #eef3f9;
                color: #1f2937;
                padding: 7px 6px;
                border: 1px solid #d8e1eb;
                border-bottom: 1px solid #c9d6e5;
                font-weight: bold;
            }
        """)
        
        # Enable horizontal scrolling
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        
        # Install event filter to detect clicks on empty table space
        self.table.viewport().installEventFilter(self)
        
        main_layout.addWidget(self.table)

    # ---------------- SIGNALS ----------------
    def _connect_signals(self):
        self.btn_inquiry.clicked.connect(self.on_inquiry_clicked)
        self.btn_add.clicked.connect(self.open_data_import_dialog)  # Changed to import dialog
        self.btn_modify.clicked.connect(self.open_modify_dialog)
        self.btn_delete.clicked.connect(self.open_delete_dialog)
        self.btn_tick.clicked.connect(self.on_tick_clicked)
        self.btn_clear_selection.clicked.connect(self.on_clear_selection_clicked)
        self.btn_batch_import.clicked.connect(self.on_batch_import_clicked)
        self.template_download.linkActivated.connect(self.on_template_download_clicked)
    
    def keyPressEvent(self, event):
        """Handle key press events - Escape to clear selection"""
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Escape:
            self.table.clearSelection()
        else:
            super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        """Filter events to detect clicks on empty table space"""
        from PyQt6.QtCore import QEvent
        
        if obj == self.table.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            # Get the row at the click position
            index = self.table.indexAt(event.pos())
            
            # If clicked on empty space (no valid row), clear selection
            if not index.isValid():
                self.table.clearSelection()
                return True
        
        return super().eventFilter(obj, event)
    
    # ---------------- CHECKBOX HANDLERS ----------------
    def on_header_checkbox_changed(self, checked):
        """Handle header checkbox change - select/deselect all rows"""
        row_count = self.table.rowCount()
        for row_idx in range(row_count):
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget is not None:
                layout = cb_widget.layout()
                if layout is not None and layout.count() > 0:
                    checkbox = layout.itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox):
                        checkbox.blockSignals(True)
                        checkbox.setChecked(checked)
                        checkbox.blockSignals(False)
    
    def on_row_checkbox_changed(self):
        """Update header checkbox when individual row checkboxes change"""
        row_count = self.table.rowCount()
        all_checked = True
        for row_idx in range(row_count):
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget is not None:
                layout = cb_widget.layout()
                if layout is not None and layout.count() > 0:
                    checkbox = layout.itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox):
                        if not checkbox.isChecked():
                            all_checked = False
                            break
        self.checkbox_header.setChecked(all_checked)
    
    def on_template_download_clicked(self):
        """Export single row per grouped sample to Excel template with display IDs"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        # Collect ticked rows with display IDs and sample info
        template_data = []
        for row_idx in range(self.table.rowCount()):
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget is not None:
                layout = cb_widget.layout()
                if layout is not None and layout.count() > 0:
                    checkbox = layout.itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                        # Get display ID from column 1 and sample name from column 2
                        display_id_item = self.table.item(row_idx, 1)
                        sample_name_item = self.table.item(row_idx, 2)
                        
                        if display_id_item and sample_name_item:
                            model_id = display_id_item.text()  # Now contains real model_id
                            sample_name = sample_name_item.text()
                            
                            # Get sample IDs from merged samples data (for template export)
                            sample_ids = []
                            if hasattr(self, '_merged_samples'):
                                for merged_sample in self._merged_samples:
                                    if merged_sample.get('id') == model_id:
                                        # Get all sample_ids for this group (not model_ids)
                                        sample_ids = merged_sample.get('sample_ids', [])
                                        break
                            
                            if sample_ids:
                                # Use only the first sample_id (representative) for merged template
                                template_data.append({
                                    'model_id': model_id,  # Real database model_id
                                    'sample_name': sample_name,
                                    'actual_sample_id': sample_ids[0]  # Only first ID
                                })
        
        if not template_data:
            QMessageBox.information(self, "Template Download", "No rows ticked for download.")
            return
        
        # Show save file dialog with filename option
        csv_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template",
            "sample_template.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not csv_path:
            return
        
        # Fetch sample data from service and replace IDs with display IDs
        try:
            actual_ids = [item['actual_sample_id'] for item in template_data]
            sample_data = SampleService.get_samples_for_template(actual_ids)
            
            # Replace actual sample_id with model_id for VLOOKUP compatibility
            id_mapping = {item['actual_sample_id']: item['model_id'] for item in template_data}
            for sample in sample_data:
                actual_id = sample['sample_id']
                if actual_id in id_mapping:
                    sample['sample_id'] = id_mapping[actual_id]
            
            # Export to CSV via service
            success, message = SampleService.export_template_to_excel(sample_data, csv_path)
            
            if success:
                QMessageBox.information(self, "Template Download", 
                    f"{message}\nSaved to: {csv_path}")
            else:
                QMessageBox.critical(self, "Export Error", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export template:\n{str(e)}")
    
    def on_batch_import_clicked(self):
        """Import substance content values from CSV file"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        # Show file open dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File to Import",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Import via service layer - no sample filtering, will update all matching samples
        try:
            success, message, updated_count = SampleService.batch_import_substance_content(
                file_path, 
                selected_sample_ids=None
            )
            
            # Refresh table silently (don't show "Loaded X samples" message)
            self.on_inquiry_clicked(silent=True)
            
            # Only show the batch import result message
            if success and updated_count > 0:
                QMessageBox.information(self, "Import Complete", message)
            elif success and updated_count == 0:
                QMessageBox.warning(self, "Import Complete", message)
            else:
                QMessageBox.critical(self, "Import Error", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import data:\n{str(e)}")
    
    # ---------------- INQUIRY ----------------
    def on_inquiry_clicked(self, silent=False):
        """Fetch and display samples, grouped by sample_name + creation_time combination
        
        Args:
            silent (bool): If True, suppress the success message after loading samples
        """
        try:
            # Get date range from UI
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
            
            # Get filter values
            sample_name_filter = self.sample_name.text().strip()
            user_id_filter = self.user_id.text().strip()
            sample_status_filter = self.sample_status.currentText()
            
            # Fetch data from service layer with filters
            samples = SampleService.get_samples_by_date(
                date_from, 
                date_to,
                sample_name=sample_name_filter if sample_name_filter else None,
                user_id=user_id_filter if user_id_filter else None,
                sample_status=sample_status_filter if sample_status_filter else None
            )
            
            # Store original samples for template download
            self._original_samples = samples
            
            # Group samples by (sample_name, creation_time) combination
            grouped_samples = {}
            for sample in samples:
                sample_name = sample.get('sample_name', '')
                creation_time = sample.get('creation_time', '')
                
                # Truncate creation_time to minute precision (ignore seconds)
                # "2026-02-10 17:34:31" -> "2026-02-10 17:34"
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
                    
                    # Update substance_content: prefer current if it's longer/more complete
                    current_substance = sample.get('substance_content', '').strip()
                    existing_substance = grouped_samples[group_key].get('substance_content', '').strip()
                    
                    if current_substance and len(current_substance) > len(existing_substance):
                        grouped_samples[group_key]['substance_content'] = current_substance
                    
                    # Update scanned_number to sum all scans at this time
                    grouped_samples[group_key]['scanned_number'] = str(
                        int(grouped_samples[group_key].get('scanned_number', 0)) + 
                        int(sample.get('scanned_number', 0))
                    )
            
            # Convert back to list - use first model_id as group ID (stable database ID)
            merged_samples = []
            for group_key, sample_data in grouped_samples.items():
                # Use first model_id from the group as the representative ID
                model_ids = sample_data.get('model_ids', [])
                if model_ids:
                    sample_data['id'] = str(model_ids[0])  # Use real database model_id
                merged_samples.append(sample_data)
            
            # Sort by creation_time descending (newest first)
            merged_samples.sort(key=lambda x: x.get('creation_time', ''), reverse=True)
            
            # Store merged samples for template download
            self._merged_samples = merged_samples
            
            # Clear and populate table with merged data
            self._populate_table(merged_samples)
            
            # Mark that inquiry has been run at least once
            self._inquiry_run = True
            
            # Only show message if not silent mode
            if not silent:
                if merged_samples:
                    QMessageBox.information(self, "Success", f"Loaded {len(merged_samples)} unique import(s) from {len(samples)} total records")
                else:
                    QMessageBox.information(self, "No Results", "No samples found for the selected date range.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error fetching samples:\n{str(e)}")
    
    def _populate_table(self, samples):
        """Populate table with sample data - UI logic only"""
        self.table.setRowCount(0)
        
        for row_idx, sample in enumerate(samples):
            self.table.insertRow(row_idx)
            
            # Column 0: Checkbox
            checkbox = QCheckBox()
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.addWidget(checkbox)
            self.table.setCellWidget(row_idx, 0, cb_widget)
            checkbox.stateChanged.connect(self.on_row_checkbox_changed)
            
            # Data columns
            creation_time_raw = sample.get('creation_time', '')
            # Clean up creation time - handle byte strings and invalid formats
            creation_time = self._format_creation_time(creation_time_raw)
            
            columns = [
                str(sample.get('id', '')),
                str(sample.get('sample_name', '')),
                str(sample.get('sample_quantity', '0')),
                str(sample.get('initial_wavelength', '900')),
                str(sample.get('terminal_wavelength', '1700')),
                str(sample.get('wavelength_step', '1')),
                str(sample.get('scanning_method', '0')),
                str(sample.get('substance_content', '')),
                str(sample.get('scanned_number', '0')),
                str(sample.get('sample_status', 'Not collected')),
                str(sample.get('user_id', '')),
                creation_time
            ]
            
            # Numeric columns for sorting
            numeric_columns = [0, 2, 3, 4, 5, 6, 8]
            
            for col_idx, value in enumerate(columns):
                item = SortableTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Set UserRole data for proper sorting
                if col_idx in numeric_columns:
                    try:
                        item.setData(Qt.ItemDataRole.UserRole, int(value))
                    except ValueError:
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, float(value))
                        except ValueError:
                            item.setData(Qt.ItemDataRole.UserRole, 0)
                else:
                    item.setData(Qt.ItemDataRole.UserRole, value)
                
                self.table.setItem(row_idx, col_idx + 1, item)
    
    def _format_creation_time(self, time_value):
        """Format creation time, handling invalid formats like b'   ' or empty values"""
        if not time_value:
            return ''
        
        # Convert to string if it's bytes
        if isinstance(time_value, bytes):
            try:
                time_value = time_value.decode('utf-8').strip()
            except Exception:
                return ''
        
        # Convert to string
        time_str = str(time_value).strip()
        
        # Check if it's empty or just whitespace
        if not time_str or time_str in ['None', 'null', 'NULL']:
            return ''
        
        # Check if it looks like a byte string representation (e.g., "b'   '")
        if time_str.startswith("b'") or time_str.startswith('b"'):
            try:
                # Extract content between quotes
                content = time_str[2:-1].strip()
                if not content or content == '   ':
                    return ''
                return content
            except Exception:
                return ''
        
        # Return cleaned string
        return time_str
    
    # ---------------- TICK & SELECTION ----------------
    def on_tick_clicked(self):
        """Toggle checkbox for selected rows"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Info", "Please select rows first")
            return
        
        for row_index in selected_rows:
            row_idx = row_index.row()
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget:
                checkbox = cb_widget.layout().itemAt(0).widget()
                if isinstance(checkbox, QCheckBox):
                    checkbox.setChecked(not checkbox.isChecked())
        
        self.table.clearSelection()
    
    def on_clear_selection_clicked(self):
        """Clear all row selections"""
        self.table.clearSelection()

    # ---------------- ADD (Now uses Data Import) ----------------
    def open_data_import_dialog(self):
        """Open data import dialog to add samples with spectral data"""
        from ui.dialogs.data_import_dialog import DataImportDialog
        
        dialog = DataImportDialog(self)
        if dialog.exec():
            import_data = dialog.get_data()
            
            # Check for both 'file_paths' and 'paths' (different dialogs use different keys)
            file_paths = import_data.get('file_paths') or import_data.get('paths', [])
            if not import_data or not file_paths:
                QMessageBox.warning(self, "Warning", "No files selected for import")
                return
            
            # Normalize the key to 'file_paths' for consistent processing
            import_data['file_paths'] = file_paths
            
            # Import files using the same logic as data management
            self.import_spectral_files(import_data)
    
    def import_spectral_files(self, import_data):
        """Import spectral data files and create sample + model_data entries - matches data_management logic"""
        from datetime import datetime
        import os
        import pandas as pd
        
        # Capture import start time - will be used for ALL files in this batch
        batch_import_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"Batch import started at: {batch_import_time}")
        
        try:
            file_paths = import_data.get('file_paths', [])
            separator = import_data.get('separator', '_')
            instrument = import_data.get('instrument', 'Unknown')
            file_format = import_data.get('format', 'csv')
            mode = import_data.get('mode', '').lower()
            
            conn = self._get_db_connection()
            if not conn:
                QMessageBox.critical(self, "Database Error", "Failed to connect to database")
                return
            
            cursor = conn.cursor()
            
            imported_count = 0
            failed_files = []
            
            for file_path in file_paths:
                try:
                    print(f"Processing file: {file_path}")
                    
                    # Skip non-CSV files
                    if not file_path.lower().endswith('.csv'):
                        print(f"Skipping non-CSV file: {file_path}")
                        continue
                    
                    # Read CSV header rows (1-18) to extract metadata
                    header_data = SpectralImportService.extract_csv_header_metadata(file_path)
                    
                    # Read CSV file - skip first 18 rows (header/metadata)
                    print(f"Reading CSV file (skipping first 18 rows)...")
                    try:
                        data_df = pd.read_csv(file_path, skiprows=18, on_bad_lines='skip')
                        print(f"Successfully read CSV with skiprows=18")
                    except Exception as e:
                        print(f"Fallback: trying with engine='python'...")
                        data_df = pd.read_csv(file_path, skiprows=18, engine='python', on_bad_lines='skip')
                        print(f"Successfully read CSV with python engine")
                    
                    # Use sample name only during import; elsewhere, always use DB value

                    # Always use file name without extension as base
                    filename = os.path.basename(file_path)
                    base_name, _ = os.path.splitext(filename)

                    # Try to extract sample_name using logic, fallback to base_name
                    sample_name = ''
                    parts = base_name.split('_')
                    # Example logic: use part after 2nd underscore if possible, else fallback
                    if len(parts) > 2 and len(parts[2]) > 14:
                        sample_name = parts[2][:-14]
                    elif len(parts) > 2:
                        sample_name = parts[2]
                    elif len(parts) > 1:
                        sample_name = parts[1]
                    else:
                        sample_name = base_name

                    # Final fallback: if sample_name is empty or whitespace, use base_name
                    if not sample_name or not sample_name.strip():
                        sample_name = base_name

                    # Guarantee: if still empty, use 'sample_' + a unique suffix (timestamp)
                    if not sample_name or not sample_name.strip():
                        from datetime import datetime
                        sample_name = f"sample_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

                    # Truncate sample name to 50 characters (database limit: VARCHAR(50))
                    MAX_SAMPLE_NAME_LENGTH = 50
                    if len(sample_name) > MAX_SAMPLE_NAME_LENGTH:
                        # Keep first 40 chars + last 10 chars to preserve uniqueness
                        sample_name = sample_name[:40] + sample_name[-10:]
                        print(f"Sample name truncated to {MAX_SAMPLE_NAME_LENGTH} chars: {sample_name}")

                    print(f"Sample name: {sample_name}, Columns: {list(data_df.columns)}")
                    
                    # Extract wavelength and absorbance data
                    wavelength_str = ""
                    absorbance_str = ""
                    absorb_points = 0
                    
                    if 'Wavelength' in data_df.columns and 'Absorbance' in data_df.columns:
                        wavelength_str = ",".join(data_df['Wavelength'].astype(str).tolist())
                        absorbance_str = ",".join(data_df['Absorbance'].astype(str).tolist())
                        absorb_points = len(data_df)
                        print(f"Found wavelength and absorbance data. Points: {absorb_points}")
                    else:
                        print(f"Warning: Could not find Wavelength/Absorbance columns. Available: {list(data_df.columns)}")
                    
                    # Get detector temperature and humidity from header metadata
                    detector_temp = header_data.get('detector_temp', '0')
                    humidity = header_data.get('humidity', '0')
                    creation_time = header_data.get('creation_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    
                    # Extract lot number based on mode
                    if 'folder' in mode:
                        folder_path = os.path.dirname(file_path)
                        folder_name = os.path.basename(folder_path)
                        if separator in folder_name:
                            lot_number = folder_name.split(separator)[0]  # Get text before separator
                        else:
                            lot_number = folder_name
                    else:
                        lot_number = ''
                    
                    # Double-check sample_name length before insert (safety check)
                    if len(sample_name) > 50:
                        print(f"WARNING: sample_name still too long ({len(sample_name)} chars), forcing truncation")
                        sample_name = sample_name[:50]
                    
                    # Insert into database using shared service
                    sample_id = SpectralImportService.insert_sample_to_db(
                        conn, sample_name, instrument, lot_number, absorb_points,
                        wavelength_str, absorbance_str, data_df,
                        detector_temp, humidity, batch_import_time
                    )
                    
                    if sample_id:
                        imported_count += 1
                        print(f"✓ Successfully imported: {sample_id} - {sample_name}")
                    else:
                        failed_files.append(f"{os.path.basename(file_path)}: Database insertion failed")
                        print(f"✗ Failed to insert: {sample_name}")
                    
                except Exception as e:
                    failed_files.append(f"{os.path.basename(file_path)}: {str(e)}")
                    print(f"✗ Error processing {file_path}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Show result message
            message = f"Successfully imported {imported_count} file(s)"
            if failed_files:
                message += f"\n\nFailed files ({len(failed_files)}):\n" + "\n".join(failed_files[:5])
                if len(failed_files) > 5:
                    message += f"\n... and {len(failed_files) - 5} more"
            
            QMessageBox.information(self, "Import Complete", message)
            
            # Refresh table
            self.on_inquiry_clicked()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")
            print(f"Error in import: {e}")
            import traceback
            traceback.print_exc()
    
    # Removed: _generate_sample_id - now using SpectralImportService.generate_sample_id()
    # Removed: _parse_spectral_file - dead code, never called
    
    def _get_db_connection(self):
        """Get database connection with READ COMMITTED isolation level for data visibility."""
        import pymysql
        from config import DB_CONFIG
        
        try:
            conn = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                port=DB_CONFIG['port'],
                charset=DB_CONFIG['charset'],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            # Set transaction isolation to READ COMMITTED to see latest committed data
            cursor = conn.cursor()
            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
            cursor.close()
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

    # ---------------- MODIFY ----------------
    def open_modify_dialog(self):
        # Count ticked rows (grouped samples), not total sample IDs
        ticked_rows = []
        for row_idx in range(self.table.rowCount()):
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget is not None:
                layout = cb_widget.layout()
                if layout is not None and layout.count() > 0:
                    checkbox = layout.itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                        ticked_rows.append(row_idx)
        
        if not ticked_rows:
            QMessageBox.information(self, "Information", "Please tick a sample to modify!")
            return
        
        if len(ticked_rows) > 1:
            QMessageBox.information(self, "Information", "Please tick only one sample to modify!")
            return
        
        # Get the model_id and find corresponding sample_id
        row_idx = ticked_rows[0]
        model_id_item = self.table.item(row_idx, 1)  # Column 1 has model_id
        if not model_id_item:
            QMessageBox.warning(self, "Error", "Failed to get sample information")
            return
        
        model_id = model_id_item.text()
        
        # Get the first sample_id for this model_id from merged samples
        sample_id = None
        if hasattr(self, '_merged_samples'):
            for merged_sample in self._merged_samples:
                if merged_sample.get('id') == model_id:
                    sample_ids = merged_sample.get('sample_ids', [])
                    if sample_ids:
                        sample_id = sample_ids[0]  # Use first sample_id
                    break
        
        if not sample_id:
            QMessageBox.warning(self, "Error", "Failed to get sample ID")
            return
        
        # Fetch sample data from service
        sample_data = SampleService.get_sample_by_id(sample_id)
        
        if not sample_data:
            QMessageBox.warning(self, "Error", "Failed to fetch sample data")
            return
        
        # Open modify dialog
        dialog = SampleModifyDialog(sample_data, self)
        if dialog.exec():
            updated_data = dialog.get_data()
            # Update sample via service layer
            success, message = SampleService.update_sample(sample_id, updated_data)
            
            if success:
                QMessageBox.information(self, "Success", message)
                # Refresh table
                self.on_inquiry_clicked()
            else:
                QMessageBox.critical(self, "Error", message)
    
    # ---------------- DELETE ----------------
    def open_delete_dialog(self):
        # Get ticked samples
        sample_ids = self._get_ticked_sample_ids()
        
        if not sample_ids:
            QMessageBox.information(self, "Information", "Please tick the rows to be deleted")
            return
        
        # Check if samples have spectrogram data
        has_spectral_data, spectral_message = SampleService.check_spectral_data(sample_ids)
        
        if has_spectral_data:
            QMessageBox.warning(
                self,
                "Warning",
                "The sample to be deleted has the spectrogram data, please delete the spectrogram data first !"
            )
            return
        
        # Delete samples (no spectrogram data found - safe to delete)
        success, message = SampleService.delete_samples(sample_ids)
        
        if success:
            QMessageBox.information(self, "Success", message)
            # Refresh table
            self.on_inquiry_clicked()
        else:
            QMessageBox.critical(self, "Error", message)
    
    def _get_ticked_sample_ids(self):
        """Helper to get list of actual database sample IDs from ticked rows (handles grouped view)"""
        sample_ids = []
        for row_idx in range(self.table.rowCount()):
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget is not None:
                layout = cb_widget.layout()
                if layout is not None and layout.count() > 0:
                    checkbox = layout.itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                        # Get model ID (now real database ID)
                        model_id_item = self.table.item(row_idx, 1)
                        if model_id_item and hasattr(self, '_merged_samples'):
                            model_id = model_id_item.text()
                            # Find the merged sample with this model_id
                            for merged_sample in self._merged_samples:
                                if merged_sample.get('id') == model_id:
                                    # Get all sample_ids for this group
                                    group_sample_ids = merged_sample.get('sample_ids', [])
                                    sample_ids.extend(group_sample_ids)
                                    break
        return sample_ids

