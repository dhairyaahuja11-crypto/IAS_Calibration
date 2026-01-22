
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget,
    QSplitter, QDateEdit, QMessageBox, QTableWidgetItem, QCheckBox, QHeaderView
)

# Ensure QTableWidgetItem is imported before subclassing

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

from PyQt6.QtCore import Qt, QDate, QObject, QEvent, QRect, pyqtSignal
import pandas as pd
import os
import re
import pymysql
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG
from ui.plot_widget import PlotWidget

# 👉 IMPORT THE DIALOG
from ui.dialogs.data_import_dialog import DataImportDialog


class CustomTableWidget(QTableWidget):
    """Custom QTableWidget that deselects rows when clicking empty areas."""
    def mousePressEvent(self, event):
        # Check if click is on an item
        item = self.itemAt(event.pos())
        
        # If clicking on empty area, clear selection
        if item is None:
            self.clearSelection()
        else:
            # Otherwise, proceed with normal selection behavior
            super().mousePressEvent(event)


class CheckBoxHeader(QHeaderView):
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


class DataManagementUI(QWidget):
    def __init__(self):
        super().__init__()
        self.import_dialog = None  # ✅ persistent reference
        self.db_config = DB_CONFIG
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------------- FILTER AREA ----------------
        filter_layout = QGridLayout()
        filter_layout.setHorizontalSpacing(5)
        filter_layout.setColumnStretch(1, 1)
        filter_layout.setColumnStretch(5, 1)
        filter_layout.setColumnStretch(7, 1)
        filter_layout.setColumnStretch(11, 1)

        filter_layout.addWidget(QLabel("Creation time:"), 0, 0)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setDisplayFormat("dd MMMM yyyy")
        self.date_from.setMinimumWidth(150)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd MMMM yyyy")
        self.date_to.setMinimumWidth(150)

        filter_layout.addWidget(self.date_from, 0, 1)
        filter_layout.addWidget(QLabel("~"), 0, 2)
        filter_layout.addWidget(self.date_to, 0, 3)

        filter_layout.addWidget(QLabel("Instrument:"), 0, 4)
        self.instrument = QComboBox()
        self.instrument.addItem("all")
        self.instrument.addItem("AG9170")
        self.instrument.addItem("AG6011")
        self.instrument.addItem("5100")
        self.instrument.addItem("5200")
        self.instrument.addItem("3120")
        self.instrument.setMinimumWidth(100)
        filter_layout.addWidget(self.instrument, 0, 5)

        filter_layout.addWidget(QLabel("Project:"), 0, 6)
        self.project = QComboBox()
        self.project.addItem("all")
        self.project.setMinimumWidth(100)
        filter_layout.addWidget(self.project, 0, 7)

        filter_layout.addWidget(QLabel("Sample name:"), 1, 0)
        self.sample_name = QLineEdit()
        self.sample_name.setMinimumWidth(150)
        filter_layout.addWidget(self.sample_name, 1, 1, 1, 2)

        filter_layout.addWidget(QLabel("Lot number:"), 1, 3)
        self.lot_number = QLineEdit()
        self.lot_number.setMinimumWidth(150)
        filter_layout.addWidget(self.lot_number, 1, 4, 1, 4)

        main_layout.addLayout(filter_layout)

        # ---------------- BUTTON BAR ----------------
        btn_layout = QHBoxLayout()

        self.btn_inquiry = QPushButton("Inquiry")
        self.btn_batch_delete = QPushButton("Batch Deletion")
        self.btn_tick = QPushButton("Tick")
        self.btn_export = QPushButton("Data Export")
        self.btn_import = QPushButton("Data Import")
        self.btn_spectrogram = QPushButton("Spectrogram Display")

        btn_layout.addWidget(self.btn_inquiry)
        btn_layout.addWidget(self.btn_batch_delete)
        btn_layout.addWidget(self.btn_tick)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_import)
        btn_layout.addWidget(self.btn_spectrogram)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # ---------------- MAIN CONTENT ----------------
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = CustomTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels([
            "", "ID", "Sample Name", "Instrument", "Lot Number", "Wavelength Points",
            "Wavelength", "Absorbance", "Detector Temp", "Humidity", "Creation Time"
        ])
        
        # Advanced: Replace header with custom checkbox header
        self.checkbox_header = CheckBoxHeader(Qt.Orientation.Horizontal, self.table)
        self.table.setHorizontalHeader(self.checkbox_header)
        self.checkbox_header.stateChanged.connect(self.on_header_checkbox_changed)
        
        # Enable row selection by clicking any cell
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Enable simple sorting for all columns
        self.table.setSortingEnabled(True)
        
        # Disable hover effects - make selection simple click only
        self.table.setMouseTracking(False)
        self.table.setStyleSheet("""
            QTableWidget {
                selection-background-color: palette(highlight);
                gridline-color: #d0d0d0;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #d0d0d0;
                border-bottom: 2px solid #808080;
                font-weight: bold;
            }
        """)
        
        splitter.addWidget(self.table)


        # Right side: Spectrogram display (matplotlib)
        self.plot = PlotWidget()
        splitter.addWidget(self.plot)

        splitter.setSizes([900, 600])
        main_layout.addWidget(splitter)

    # ---------------- SIGNALS ----------------
    def _connect_signals(self):
        self.btn_import.clicked.connect(self.open_data_import_dialog)
        self.btn_inquiry.clicked.connect(self.on_inquiry_clicked)
        self.btn_tick.clicked.connect(self.on_tick_clicked)
        self.btn_batch_delete.clicked.connect(self.on_batch_delete_clicked)
        self.btn_export.clicked.connect(self.on_export_clicked)
        self.btn_spectrogram.clicked.connect(self.on_spectrogram_display_clicked)

    def on_spectrogram_display_clicked(self):
        """Universal spectrogram display: select file or folder, ignore case, plot all valid CSVs."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import pandas as pd
        import matplotlib.pyplot as plt
        import os

        # Only allow folder selection
        folder_path = QFileDialog.getExistingDirectory(self, "Select a folder of CSVs")
        if not folder_path:
            return

        import numpy as np
        all_wavelengths = []
        all_absorbances = []
        import matplotlib.cm as cm
        color_map = cm.get_cmap('tab10')
        file_count = 0
        for fname in os.listdir(folder_path):
            if fname.lower().endswith('.csv'):
                path = os.path.join(folder_path, fname)
                try:
                    df = pd.read_csv(path, skiprows=18, on_bad_lines='skip')
                except Exception as e:
                    QMessageBox.critical(self, "File Error", f"Failed to read file {path}:\n{e}")
                    continue
                cols = {c.lower(): c for c in df.columns}
                if 'wavelength' in cols and 'absorbance' in cols:
                    wavelength = df[cols['wavelength']].values
                    absorbance = df[cols['absorbance']].values
                    all_wavelengths.append(wavelength)
                    all_absorbances.append(absorbance)
                    file_count += 1
                else:
                    QMessageBox.warning(self, "Data Error", f"{os.path.basename(path)}: CSV must contain 'Wavelength' and 'Absorbance' columns (case-insensitive).")

        # Plot all in the embedded UI graph (self.plot)
        self.plot.clear()
        if file_count == 0:
            QMessageBox.warning(self, "No Data", "No valid CSVs found in the selected folder.")
            return
        for i, (wavelength, absorbance) in enumerate(zip(all_wavelengths, all_absorbances)):
            color = color_map(i % 10)
            self.plot.ax.plot(wavelength, absorbance, marker='o', markersize=0.5, linestyle='-', color=color, linewidth=1)
        self.plot.ax.set_xlabel('Wavelength (nm)')
        self.plot.ax.set_ylabel('Absorbance')
        self.plot.ax.set_title('Spectrogram Display (All Files)')
        self.plot.ax.grid(True, alpha=0.3)
        # Remove legend to avoid file name box
        self.plot.figure.tight_layout()
        self.plot.canvas.draw()
    def on_export_clicked(self):
        """Export ticked rows to CSV after user selects location."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import csv, os

        # Open file dialog for folder selection or new folder creation
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            return  # User cancelled

        # Get ticked rows only
        ticked_rows = []
        for row_idx in range(self.table.rowCount()):
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget is not None:
                layout = cb_widget.layout()
                if layout is not None and layout.count() > 0:
                    checkbox = layout.itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                        row_data = []
                        for col_idx in range(1, self.table.columnCount()):
                            item = self.table.item(row_idx, col_idx)
                            row_data.append(item.text() if item else "")
                        ticked_rows.append(row_data)

        print(f"Export: Found {len(ticked_rows)} ticked rows")
        
        if not ticked_rows:
            QMessageBox.information(self, "Export", "No rows ticked for export.")
            return
        # Only export ticked rows
        export_rows = ticked_rows

        # Prepare CSV file path
        csv_path = os.path.join(folder, "exported_data.csv")
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(1, self.table.columnCount())]

        # Write to CSV
        try:
            print(f"Export: Writing to {csv_path}")
            with open(csv_path, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(export_rows)
            print(f"Export: Successfully wrote {len(export_rows)} rows")
            QMessageBox.information(self, "Export", f"Exported {len(export_rows)} rows to {csv_path}")
        except Exception as e:
            print(f"Export: Error occurred - {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    # ============= ACTIONS ============
    def on_header_checkbox_changed(self, checked):
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

    def on_inquiry_clicked(self):
        """Query database and display data based on date filters."""
        try:
            # Get date range from filters
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
            selected_instrument = self.instrument.currentText()
            selected_project = self.project.currentText()

            print(f"Inquiry: Fetching data from {date_from} to {date_to}, Instrument: {selected_instrument}, Project: {selected_project}")

            # Connect to database
            conn = self._get_db_connection()
            if not conn:
                QMessageBox.critical(self, "Database Error", "Failed to connect to database")
                return

            cursor = conn.cursor()

            # Build query with optional instrument/project filters
            query = """
            SELECT 
                s.sample_id as id,
                s.sample_name as sample_name,
                md.device_id as instrument,
                md.model_sno as lot_number,
                md.model_sno as serial_number,
                md.model_length as wavelength_points,
                md.wave as wavelength,
                md.absorb as absorbance,
                '0' as detector_temp,
                '0' as humidity,
                s.create_time as creation_time
            FROM sample s
            LEFT JOIN model_data md ON s.sample_id = md.sample_id
            WHERE DATE(s.create_time) BETWEEN %s AND %s
            """
            params = [date_from, date_to]
            if selected_instrument and selected_instrument.lower() != "all" and selected_instrument.lower() != "(none)":
                query += " AND md.device_id = %s"
                params.append(selected_instrument)
            if selected_project and selected_project.lower() != "all":
                query += " AND s.sample_name = %s"
                params.append(selected_project)
            query += " ORDER BY s.create_time DESC"

            cursor.execute(query, tuple(params))
            results = cursor.fetchall()

            cursor.close()
            conn.close()
            
            # Clear table
            self.table.setRowCount(0)
            
            if not results:
                QMessageBox.information(self, "No Results", "No data found for the selected date range.")
                return
            
            # Populate table with results
            for row_idx, row_data in enumerate(results):
                self.table.insertRow(row_idx)
                # Add checkbox in the first column (index 0)
                from PyQt6.QtWidgets import QWidget, QHBoxLayout
                checkbox = QCheckBox()
                checkbox.stateChanged.connect(self.on_row_checkbox_changed)
                cb_widget = QWidget()
                cb_layout = QHBoxLayout(cb_widget)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cb_layout.addWidget(checkbox)
                cb_widget.setLayout(cb_layout)
                self.table.setCellWidget(row_idx, 0, cb_widget)
                # Convert ID to int if possible
                try:
                    row_data['id'] = int(row_data['id'])
                except Exception:
                    row_data['id'] = 0
                # Set each column in the order: ID, Sample Name, Instrument, Lot Number, Serial Number, Wavelength Points, Wavelength, Absorbance, Detector Temp, Humidity, Creation Time
                columns = [
                    row_data['id'],
                    row_data['sample_name'],
                    row_data['instrument'],
                    row_data['lot_number'],
                    row_data['wavelength_points'],
                    row_data['wavelength'],
                    row_data['absorbance'],
                    row_data['detector_temp'],
                    row_data['humidity'],
                    str(row_data['creation_time'])
                ]

                # Set UserRole for correct sorting (ID and Wavelength Points as int, others as float/string as needed)
                numeric_columns = [0, 4]  # ID and Wavelength Points
                float_columns = [5, 6, 7, 8]  # Wavelength, Absorbance, Detector Temp, Humidity
                for col_idx, value in enumerate(columns):
                    item = SortableTableWidgetItem(str(value) if value is not None else "")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if col_idx in numeric_columns:
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, int(value))
                        except Exception:
                            item.setData(Qt.ItemDataRole.UserRole, 0)
                    elif col_idx in float_columns:
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, float(value))
                        except Exception:
                            item.setData(Qt.ItemDataRole.UserRole, 0.0)
                    else:
                        item.setData(Qt.ItemDataRole.UserRole, str(value) if value is not None else "")
                    self.table.setItem(row_idx, col_idx + 1, item)
            
            QMessageBox.information(self, "Success", f"Loaded {len(results)} record(s) from database.")
            print(f"Successfully loaded {len(results)} records")
            
        except Exception as e:
            print(f"Error in inquiry: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error during inquiry:\n{str(e)}")

    def on_tick_clicked(self):
        """Toggle checkbox state for all selected rows."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Info", "Please select rows first")
            return
        ticked_count = 0
        unticked_count = 0
        for row_index in selected_rows:
            row_idx = row_index.row()
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget is not None:
                layout = cb_widget.layout()
                if layout is not None and layout.count() > 0:
                    checkbox = layout.itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox):
                        current_state = checkbox.isChecked()
                        checkbox.setChecked(not current_state)
                        if not current_state:
                            ticked_count += 1
                        else:
                            unticked_count += 1
        # Clear selection after ticking
        self.table.clearSelection()
        print(f"Toggled {len(selected_rows)} row(s): Ticked {ticked_count}, Unticked {unticked_count}")

    def on_batch_delete_clicked(self):
        """Delete rows from database and table - works for both selected rows AND ticked rows."""
        ticked_rows = []
        row_count = self.table.rowCount()
        for row_idx in range(row_count):
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget is not None:
                layout = cb_widget.layout()
                if layout is not None and layout.count() > 0:
                    checkbox = layout.itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox):
                        if checkbox.isChecked():
                            ticked_rows.append(row_idx)
        if not ticked_rows:
            QMessageBox.information(self, "Info", "Please tick rows to delete.")
            return
        rows_to_delete = ticked_rows
        
        if not rows_to_delete:
            QMessageBox.information(self, "Info", "Please select rows to delete or tick rows")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {len(rows_to_delete)} row(s)? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Collect sample IDs from rows to delete (ID is in hidden column 1)
        sample_ids = []
        for row_idx in rows_to_delete:
            id_item = self.table.item(row_idx, 1)
            if id_item:
                sample_ids.append(id_item.text())
        
        if not sample_ids:
            QMessageBox.warning(self, "Error", "Could not retrieve sample IDs")
            return
        
        try:
            # Connect to database
            conn = self._get_db_connection()
            if not conn:
                QMessageBox.critical(self, "Database Error", "Failed to connect to database")
                return
            
            cursor = conn.cursor()
            
            # Delete from database (Option 1: Delete from both tables)
            deleted_count = 0
            for sample_id in sample_ids:
                try:
                    # Delete from model_data table first (contains spectral data)
                    cursor.execute("DELETE FROM model_data WHERE sample_id = %s", (sample_id,))
                    
                    # Delete from sample table (contains sample metadata)
                    cursor.execute("DELETE FROM sample WHERE sample_id = %s", (sample_id,))
                    
                    deleted_count += 1
                    print(f"Deleted sample_id: {sample_id} from both sample and model_data tables")
                except Exception as e:
                    print(f"Error deleting sample_id {sample_id}: {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Remove rows from table (remove in reverse order to avoid index shifting)
            for row_idx in sorted(rows_to_delete, reverse=True):
                self.table.removeRow(row_idx)
            
            # Clear selection
            self.table.clearSelection()
            
            # Uncheck header checkbox (now managed by CheckBoxHeader)
            self.checkbox_header.setChecked(False)
            
            QMessageBox.information(self, "Success", f"Successfully deleted {deleted_count} record(s) from database")
            print(f"Batch deleted {deleted_count} records from both sample and model_data tables")
            
        except Exception as e:
            print(f"Error during batch deletion: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error during deletion:\n{str(e)}")

    def open_data_import_dialog(self):
        dialog = DataImportDialog(self)

        if dialog.exec():  # 👈 modal + blocks
            data = dialog.get_data()

            print("Imported data info:")
            print(f"Mode: {data['mode']}")
            print(f"Path: {data['path']}")
            print(f"Paths ({len(data['paths'])} files): {data['paths']}")
            
            # Process based on selection mode
            if "folder" in data['mode'].lower():
                self._process_folder_import(data)
            else:
                self._process_file_import(data)

    def _process_folder_import(self, data):
        """Process folder import: read CSV files, display in table, and save to database."""
        paths = data['paths']
        
        if not paths:
            QMessageBox.warning(self, "No files", "No files found in the selected folder.")
            return
        
        print(f"Processing {len(paths)} file(s)")
        
        # Clear existing table
        self.table.setRowCount(0)
        
        try:
            # Connect to database
            conn = self._get_db_connection()
            if not conn:
                QMessageBox.critical(self, "Database Error", "Failed to connect to database")
                return
            
            row = 0
            inserted_count = 0
            sample_ids = []
            
            for file_path in paths:
                try:
                    print(f"Processing file: {file_path}")
                    
                    # Skip non-CSV files
                    if not file_path.lower().endswith('.csv'):
                        print(f"Skipping non-CSV file: {file_path}")
                        continue
                    
                    # Read CSV header rows (1-18) to extract metadata
                    header_data = self._extract_csv_header_metadata(file_path)
                    
                    # Read CSV file - skip first 18 rows (header/metadata)
                    print(f"Reading CSV file (skipping first 18 rows)...")
                    try:
                        # First try reading from row 19 onwards
                        data_df = pd.read_csv(file_path, skiprows=18, on_bad_lines='skip')
                        print(f"Successfully read CSV with skiprows=18")
                    except Exception as e:
                        print(f"Fallback: trying with engine='python'...")
                        # Fallback: use python engine which is more forgiving
                        data_df = pd.read_csv(file_path, skiprows=18, engine='python', on_bad_lines='skip')
                        print(f"Successfully read CSV with python engine")
                    
                    # Extract metadata from filename and mode
                    filename = os.path.basename(file_path)
                    mode = data.get('mode', '').lower()
                    
                    # If "add new samples named after folder" mode, extract sample name from folder
                    if 'folder' in mode:
                        folder_path = os.path.dirname(file_path)
                        folder_name = os.path.basename(folder_path)
                        separator = data.get('separator', '_')
                        if separator in folder_name:
                            sample_name = folder_name.split(separator)[-1]  # Get text after separator
                        else:
                            sample_name = folder_name  # Use entire folder name if separator not found
                    else:
                        sample_name = data.get('sample', filename.replace('.csv', ''))
                    
                    print(f"Sample name: {sample_name}, Columns: {list(data_df.columns)}")
                    
                    # Extract wavelength and absorbance (FULL, not just preview)
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
                    
                    # Insert into database
                    print(f"Inserting into database...")
                    sample_id = self._insert_sample_to_db(
                        conn, sample_name, data, absorb_points, wavelength_str, absorbance_str, data_df,
                        detector_temp, humidity, creation_time
                    )
                    
                    if sample_id:
                        print(f"Successfully inserted sample: {sample_id}")
                        sample_ids.append(sample_id)
                        inserted_count += 1
                    else:
                        print(f"Failed to insert sample: {sample_name}")
                    
                    # Add row to table
                    self.table.insertRow(row)
                    
                    # Column 0: Checkbox
                    checkbox = QCheckBox()
                    self.table.setCellWidget(row, 0, checkbox)
                    
                    # Column 1: ID (filename)
                    self.table.setItem(row, 1, QTableWidgetItem(filename))
                    
                    # Column 2: Sample Name (use the extracted sample_name variable)
                    self.table.setItem(row, 2, QTableWidgetItem(sample_name))
                    
                    # Column 3: Instrument (from dialog input)
                    instrument = data.get('instrument', 'Unknown')
                    self.table.setItem(row, 3, QTableWidgetItem(instrument))
                    
                    # Column 4: Lot Number (extract from folder name using separator, or from dialog)
                    # If "add new samples named after folder" mode, extract from folder name
                    mode = data.get('mode', '').lower()
                    if 'folder' in mode:
                        # Extract lot number from folder path before separator
                        folder_path = os.path.dirname(file_path)
                        folder_name = os.path.basename(folder_path)
                        separator = data.get('separator', '_')
                        if separator in folder_name:
                            lot = folder_name.split(separator)[0]  # Get text before separator
                        else:
                            lot = folder_name  # Use entire folder name if separator not found
                    else:
                        lot = data.get('lot', '')  # Use lot from dialog
                    self.table.setItem(row, 4, QTableWidgetItem(lot))
                    
                    # Column 5: Serial Number (sequential: 1, 2, 3...) - get row count AFTER insertion
                    serial = str(self.table.rowCount())
                    self.table.setItem(row, 5, QTableWidgetItem(serial))
                    
                    # Column 6: Wavelength Points (count of data rows)
                    self.table.setItem(row, 6, QTableWidgetItem(str(absorb_points)))
                    
                    # Column 7: Wavelength (full comma-separated)
                    self.table.setItem(row, 7, QTableWidgetItem(wavelength_str))
                    
                    # Column 8: Absorbance (full comma-separated)
                    self.table.setItem(row, 8, QTableWidgetItem(absorbance_str))
                    
                    # Column 9: Detector Temperature
                    self.table.setItem(row, 9, QTableWidgetItem(detector_temp))
                    
                    # Column 10: Humidity
                    self.table.setItem(row, 10, QTableWidgetItem(humidity))
                    
                    # Column 11: Creation Time
                    self.table.setItem(row, 11, QTableWidgetItem(creation_time))
                    
                    print(f"Table row {row}: {filename} | {sample_name} | {instrument} | {lot} | {creation_time}")
                    
                    # Plot first file's data
                    if row == 0 and data_df is not None:
                        self._plot_spectrogram(data_df)
                    
                    row += 1
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    import traceback
                    traceback.print_exc()
            
            conn.close()
            
            print(f"Total inserted: {inserted_count} files")
            
            if inserted_count > 0:
                QMessageBox.information(
                    self, "Success", 
                    f"Loaded {row} file(s)!\nSuccessfully inserted {inserted_count} sample(s) to database."
                )
            else:
                QMessageBox.warning(self, "No files processed", "Files were found but none were successfully processed. Check console for details.")
                
        except Exception as e:
            print(f"Database error: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error:\n{str(e)}")

    def _process_file_import(self, data):
        """Process single file import."""
        paths = data['paths']
        
        if not paths:
            QMessageBox.warning(self, "No file", "No file selected.")
            return
        
        file_path = paths[0]
        self.table.setRowCount(0)
        
        try:
            # Connect to database
            conn = self._get_db_connection()
            if not conn:
                QMessageBox.critical(self, "Database Error", "Failed to connect to database")
                return
            
            print(f"Processing single file: {file_path}")
            
            # Read CSV header rows (1-18) to extract metadata
            header_data = self._extract_csv_header_metadata(file_path)
            
            # Read CSV file - skip first 18 rows (header/metadata)
            try:
                df = pd.read_csv(file_path, skiprows=18, on_bad_lines='skip')
                data_df = df
                print(f"Successfully read CSV with skiprows=18")
            except Exception as e:
                print(f"Fallback: trying with engine='python'...")
                df = pd.read_csv(file_path, skiprows=18, engine='python', on_bad_lines='skip')
                data_df = df
                print(f"Successfully read CSV with python engine")
                
            filename = os.path.basename(file_path)
            mode = data.get('mode', '').lower()
            
            # If "add new samples named after folder" mode, extract sample name from folder
            if 'folder' in mode:
                folder_path = os.path.dirname(file_path)
                folder_name = os.path.basename(folder_path)
                separator = data.get('separator', '_')
                if separator in folder_name:
                    sample_name = folder_name.split(separator)[-1]  # Get text after separator
                else:
                    sample_name = folder_name  # Use entire folder name if separator not found
            else:
                sample_name = data.get('sample', filename.replace('.csv', ''))
            
            # Extract wavelength and absorbance (FULL, not just preview)
            wavelength_str = ""
            absorbance_str = ""
            absorb_points = 0
            
            if 'Wavelength' in data_df.columns and 'Absorbance' in data_df.columns:
                wavelength_str = ",".join(data_df['Wavelength'].astype(str).tolist())
                absorbance_str = ",".join(data_df['Absorbance'].astype(str).tolist())
                absorb_points = len(data_df)
            
            # Get detector temperature and humidity from header metadata
            detector_temp = header_data.get('detector_temp', '0')
            humidity = header_data.get('humidity', '0')
            creation_time = header_data.get('creation_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # Insert into database
            sample_id = self._insert_sample_to_db(
                conn, sample_name, data, absorb_points, wavelength_str, absorbance_str, data_df,
                detector_temp, humidity, creation_time
            )
            
            conn.close()
            
            # Add single row to table
            self.table.insertRow(0)
            
            # Column 0: Checkbox
            checkbox = QCheckBox()
            self.table.setCellWidget(0, 0, checkbox)
            
            # Column 1: ID (filename)
            self.table.setItem(0, 1, QTableWidgetItem(filename))
            
            # Column 2: Sample Name (from dialog)
            self.table.setItem(0, 2, QTableWidgetItem(sample_name))
            
            # Column 3: Instrument (from dialog)
            instrument = data.get('instrument', 'Unknown')
            self.table.setItem(0, 3, QTableWidgetItem(instrument))
            
            # Column 4: Lot Number (from dialog)
            lot = data.get('lot', '')
            self.table.setItem(0, 4, QTableWidgetItem(lot))
            
            # Column 5: Serial Number (sequential: 1, 2, 3...)
            serial = str(self.table.rowCount())  # Get row count after insertion (which is 1 for first row)
            self.table.setItem(0, 5, QTableWidgetItem(serial))
            
            # Column 6: Wavelength Points
            self.table.setItem(0, 6, QTableWidgetItem(str(absorb_points)))
            
            # Column 7: Wavelength
            self.table.setItem(0, 7, QTableWidgetItem(wavelength_str))
            
            # Column 8: Absorbance
            self.table.setItem(0, 8, QTableWidgetItem(absorbance_str))
            
            # Column 9: Detector Temperature
            self.table.setItem(0, 9, QTableWidgetItem(detector_temp))
            
            # Column 10: Humidity
            self.table.setItem(0, 10, QTableWidgetItem(humidity))
            
            # Column 11: Creation Time
            self.table.setItem(0, 11, QTableWidgetItem(creation_time))
            
            self._plot_spectrogram(df)
            
            if sample_id:
                QMessageBox.information(
                    self, "Success", 
                    f"File: {filename}\n"
                    f"Sample: {sample_name}\n"
                    f"Instrument: {instrument}\n"
                    f"Lot: {lot}\n\n"
                    f"Successfully saved to database!"
                )
            else:
                QMessageBox.warning(self, "Warning", f"File loaded but database insertion failed")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Error processing file:\n{str(e)}")

    def _plot_spectrogram(self, df):
        """Plot wavelength vs absorbance on the spectrogram widget (matplotlib)."""
        self.plot.clear()
        if 'Wavelength' in df.columns and 'Absorbance' in df.columns:
            wavelength = df['Wavelength'].values
            absorbance = df['Absorbance'].values
            self.plot.plot_spectra(wavelength, absorbance, title="NIR Spectra")

    def _extract_csv_header_metadata(self, file_path):
        """Extract metadata from CSV header rows (specific row/column positions)."""
        header_data = {
            'detector_temp': '0.0',
            'humidity': '0.0',
            'serial_number': '',
            'creation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            # Read CSV file
            df = pd.read_csv(file_path, header=None, skiprows=0, on_bad_lines='skip', encoding='utf-8')
            
            # Extract from specific rows (0-indexed, so row 4 in Excel = index 3)
            # Row 4: Detector Temp hundredths: | B column
            if len(df) > 3:  # Row 4
                try:
                    detector_val = df.iloc[3, 1]  # Column B (index 1)
                    if pd.notna(detector_val):
                        detector_val = float(detector_val) / 100.0  # Divide by 100 (hundredths)
                        header_data['detector_temp'] = f"{detector_val:.2f}"
                except (ValueError, IndexError):
                    pass
            
            # Row 5: Humidity hundredths: | B column
            if len(df) > 4:  # Row 5
                try:
                    humidity_val = df.iloc[4, 1]  # Column B (index 1)
                    if pd.notna(humidity_val):
                        humidity_val = float(humidity_val) / 100.0  # Divide by 100 (hundredths)
                        header_data['humidity'] = f"{humidity_val:.2f}"
                except (ValueError, IndexError):
                    pass
            
            # Row 8: Serial Number: | B column
            if len(df) > 7:  # Row 8
                try:
                    serial_val = df.iloc[7, 1]  # Column B (index 1)
                    if pd.notna(serial_val):
                        header_data['serial_number'] = str(serial_val).strip()
                except (ValueError, IndexError):
                    pass
            
            # Row 15: Measurement points: | B column (for wavelength count)
            # Note: Creation time will use current timestamp
            
            print(f"Extracted header metadata: {header_data}")
            return header_data
            
        except Exception as e:
            print(f"Error extracting CSV header metadata: {e}")
            import traceback
            traceback.print_exc()
            return header_data

    # ============= DATABASE METHODS =============
    def _get_db_connection(self):
        """Get database connection."""
        try:
            conn = pymysql.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                port=self.db_config['port'],
                charset=self.db_config['charset'],
                cursorclass=pymysql.cursors.DictCursor
            )
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

    def _insert_sample_to_db(self, conn, sample_name, data, absorb_points, wavelength_str, absorbance_str, data_df,
                             detector_temp='0', humidity='0', creation_time=None):
        """Insert sample data into database tables with all metadata from dialog."""
        cursor = None
        try:
            cursor = conn.cursor()
            
            if creation_time is None:
                creation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Generate unique sample_id
            sample_id = self._generate_sample_id(cursor)
            print(f"Generated sample_id: {sample_id}")
            
            # Extract wavelength range from data
            model_wavemin = "900"
            model_wavemax = "1700"
            
            if 'Wavelength' in data_df.columns:
                wavelengths = data_df['Wavelength'].values
                if len(wavelengths) > 0:
                    model_wavemin = str(int(wavelengths[0]))
                    model_wavemax = str(int(wavelengths[-1]))
            
            print(f"Wave range: {model_wavemin} - {model_wavemax}")
            
            # Get metadata from dialog inputs
            instrument = data.get('instrument', 'Unknown')
            lot_number = data.get('lot', '')
            file_format = data.get('format', 'csv')
            creation_date = datetime.now()
            
            # ===== INSERT INTO sample TABLE =====
            insert_sample = """
            INSERT INTO sample (
                sample_id, sample_name, model_num, model_wavemin, model_wavemax,
                model_wavepath, model_method, sample_status,
                create_person, create_time, sample_state
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """
            
            print(f"Inserting into sample table with:")
            print(f"  - sample_id: {sample_id}")
            print(f"  - sample_name: {sample_name}")
            print(f"  - instrument: {instrument}")
            print(f"  - lot_number: {lot_number}")
            print(f"  - file_format: {file_format}")
            
            cursor.execute(insert_sample, (
                sample_id, 
                sample_name, 
                0, 
                model_wavemin, 
                model_wavemax,
                '1', 
                '0', 
                '0',
                f'ui_import_{instrument}_{lot_number}',
                '1'
            ))
            print(f"Successfully inserted into sample table")
            
            # ===== INSERT INTO model_data TABLE =====
            if 'Wavelength' in data_df.columns and 'Absorbance' in data_df.columns:
                wave = ",".join(data_df['Wavelength'].astype(str).tolist())
                absorb = ",".join(data_df['Absorbance'].astype(str).tolist())
                
                insert_model = """
                INSERT INTO model_data (
                    sample_id, model_sno, model_order, device_id,
                    model_length, wave, absorb, system_temp, create_time
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                
                print(f"Inserting into model_data table with device_id: {instrument}")
                cursor.execute(insert_model, (
                    sample_id,
                    lot_number,  # Store lot number here
                    "1",
                    instrument,
                    str(absorb_points),
                    wave,
                    absorb,
                    "0"
                ))
                print(f"Successfully inserted into model_data table")
            else:
                print(f"Warning: Wavelength/Absorbance not found in data_df")
                # Still insert even without spectral data
                insert_model = """
                INSERT INTO model_data (
                    sample_id, model_sno, model_order, device_id,
                    model_length, system_temp, create_time
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(insert_model, (
                    sample_id,
                    lot_number,
                    "1",
                    instrument,
                    str(absorb_points),
                    "0"
                ))
            
            # ===== INSERT INTO project TABLE (optional) =====
            project_id = self._get_or_create_project(cursor, data)
            print(f"Project ID: {project_id}")
            
            # ===== INSERT INTO project_sample TABLE =====
            if project_id:
                project_sample_id = self._generate_project_sample_id(cursor)
                insert_project_sample = """
                INSERT INTO project_sample (id, project_id, sample_id, new_id, new_name)
                VALUES (%s, %s, %s, %s, %s)
                """
                
                print(f"Inserting into project_sample table...")
                cursor.execute(insert_project_sample, (
                    project_sample_id,
                    project_id,
                    sample_id,
                    "",
                    sample_name
                ))
                print(f"Successfully inserted into project_sample table")
            
            # Commit all changes
            conn.commit()
            print(f"✓ Successfully inserted sample: {sample_id} - {sample_name}")
            print(f"  Instrument: {instrument}, Lot: {lot_number}, Format: {file_format}")
            return sample_id
            
        except Exception as e:
            print(f"✗ Error inserting sample: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
            except:
                pass
            return None
        finally:
            if cursor:
                cursor.close()

    def _generate_sample_id(self, cursor):
        """Generate unique sample_id."""
        try:
            query = "SELECT MAX(CAST(sample_id AS UNSIGNED)) as max_id FROM sample"
            cursor.execute(query)
            result = cursor.fetchone()
            max_id = result['max_id'] if result['max_id'] else 0
            return str(max_id + 1)
        except:
            return str(int(datetime.now().timestamp()))

    def _generate_project_sample_id(self, cursor):
        """Generate unique project_sample id."""
        try:
            query = "SELECT MAX(CAST(id AS UNSIGNED)) as max_id FROM project_sample"
            cursor.execute(query)
            result = cursor.fetchone()
            max_id = result['max_id'] if result['max_id'] else 0
            return str(max_id + 1)
        except:
            return str(int(datetime.now().timestamp()))

    def _get_or_create_project(self, cursor, data):
        """Get existing project or create a new one."""
        try:
            project_name = f"Import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Check if project exists
            query = "SELECT project_id FROM project WHERE project_name = %s"
            cursor.execute(query, (project_name,))
            result = cursor.fetchone()
            
            if result:
                return result['project_id']
            
            # Create new project
            project_id = self._generate_project_id(cursor)
            insert_project = """
            INSERT INTO project (
                project_id, project_name, sample_type, analysis_type,
                project_progress, create_person, create_time, project_state
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
            """
            
            cursor.execute(insert_project, (
                project_id,
                project_name,
                "0",
                "1",
                "0",
                "data_import_ui",
                "1"
            ))
            
            return project_id
            
        except Exception as e:
            print(f"Error creating project: {e}")
            return None

    def _generate_project_id(self, cursor):
        """Generate unique project_id."""
        try:
            query = "SELECT MAX(CAST(project_id AS UNSIGNED)) as max_id FROM project"
            cursor.execute(query)
            result = cursor.fetchone()
            max_id = result['max_id'] if result['max_id'] else 0
            return str(max_id + 1)
        except:
            return str(int(datetime.now().timestamp()))