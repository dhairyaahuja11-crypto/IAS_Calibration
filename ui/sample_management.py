from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QDateEdit, QTableWidget, QTableWidgetItem,
    QCheckBox, QHeaderView, QMessageBox
)

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
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------------- FILTER AREA ----------------
        filter_layout = QGridLayout()

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
        filter_layout.addWidget(self.user_id, 0, 5)

        filter_layout.addWidget(QLabel("Creation time:"), 0, 6)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd MMMM yyyy")

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd MMMM yyyy")

        filter_layout.addWidget(self.date_from, 0, 7)
        filter_layout.addWidget(self.date_to, 0, 8)

        main_layout.addLayout(filter_layout)

        # ---------------- BUTTON BAR ----------------
        btn_layout = QHBoxLayout()

        self.btn_inquiry = QPushButton("Inquiry")
        self.btn_add = QPushButton("Add")
        self.btn_modify = QPushButton("Modify")
        self.btn_delete = QPushButton("Delete")
        self.btn_tick = QPushButton("Tick")
        self.btn_batch_import = QPushButton("Batch import substance content")

        btn_layout.addWidget(self.btn_inquiry)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_modify)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_tick)
        btn_layout.addWidget(self.btn_batch_import)

        self.template_download = QLabel('<a href="#">template download</a>')
        self.template_download.setTextFormat(Qt.TextFormat.RichText)
        self.template_download.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.template_download.setOpenExternalLinks(False)

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
        
        # Adjust column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 30)  # Checkbox column
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Sample name
        
        main_layout.addWidget(self.table)

    # ---------------- SIGNALS ----------------
    def _connect_signals(self):
        self.btn_inquiry.clicked.connect(self.on_inquiry_clicked)
        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_modify.clicked.connect(self.open_modify_dialog)
        self.btn_delete.clicked.connect(self.open_delete_dialog)
        self.btn_tick.clicked.connect(self.on_tick_clicked)
        self.btn_batch_import.clicked.connect(self.on_batch_import_clicked)
        self.template_download.linkActivated.connect(self.on_template_download_clicked)
    
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
        """Export ticked rows to Excel template with specific headers"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        # Collect ticked sample IDs from table
        sample_ids = []
        for row_idx in range(self.table.rowCount()):
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget is not None:
                layout = cb_widget.layout()
                if layout is not None and layout.count() > 0:
                    checkbox = layout.itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                        # Get sample ID from column 1
                        sample_id_item = self.table.item(row_idx, 1)
                        if sample_id_item:
                            try:
                                sample_ids.append(int(sample_id_item.text()))
                            except ValueError:
                                pass
        
        if not sample_ids:
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
        
        # Fetch sample data from service
        try:
            sample_data = SampleService.get_samples_for_template(sample_ids)
            
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
        
        # Import via service layer
        try:
            success, message, updated_count = SampleService.batch_import_substance_content(file_path)
            
            # Always refresh table to show any updates
            self.on_inquiry_clicked()
            
            if success and updated_count > 0:
                QMessageBox.information(self, "Import Complete", message)
            elif success and updated_count == 0:
                QMessageBox.warning(self, "Import Complete", message)
            else:
                QMessageBox.critical(self, "Import Error", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import data:\n{str(e)}")
    
    # ---------------- INQUIRY ----------------
    def on_inquiry_clicked(self):
        """Fetch and display samples based on date range"""
        try:
            # Get date range from UI
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
            
            # Fetch data from service layer
            samples = SampleService.get_samples_by_date(date_from, date_to)
            
            # Clear and populate table with UI logic only
            self._populate_table(samples)
            
            if samples:
                QMessageBox.information(self, "Success", f"Loaded {len(samples)} sample(s)")
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
                str(sample.get('creation_time', ''))
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
    
    # ---------------- TICK ----------------
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

    # ---------------- ADD ----------------
    def open_add_dialog(self):
        dialog = SampleAddDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            # Add sample via service layer
            success, message, sample_id = SampleService.add_sample(data)
            
            if success:
                QMessageBox.information(self, "Success", message)
                # Refresh table to show new sample
                self.on_inquiry_clicked()
            else:
                QMessageBox.critical(self, "Error", message)

    # ---------------- MODIFY ----------------
    def open_modify_dialog(self):
        # Get ticked samples
        ticked_sample_ids = self._get_ticked_sample_ids()
        
        if not ticked_sample_ids:
            QMessageBox.information(self, "Information", "Please tick a sample to modify!")
            return
        
        if len(ticked_sample_ids) > 1:
            QMessageBox.information(self, "Information", "Please tick only one sample to modify!")
            return
        
        # Fetch sample data from service
        sample_id = ticked_sample_ids[0]
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
        
        # Delete samples directly (no spectrogram data found)
        success, message = SampleService.delete_samples(sample_ids)
        
        if success:
            QMessageBox.information(self, "Success", message)
            # Refresh table
            self.on_inquiry_clicked()
        else:
            QMessageBox.critical(self, "Error", message)
    
    def _get_ticked_sample_ids(self):
        """Helper to get list of ticked sample IDs from table"""
        sample_ids = []
        for row_idx in range(self.table.rowCount()):
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget is not None:
                layout = cb_widget.layout()
                if layout is not None and layout.count() > 0:
                    checkbox = layout.itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                        sample_id_item = self.table.item(row_idx, 1)
                        if sample_id_item:
                            # Sample IDs can be strings (timestamp-based) or integers
                            sample_id = sample_id_item.text().strip()
                            if sample_id:
                                sample_ids.append(sample_id)
        return sample_ids

