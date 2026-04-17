
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget,
    QSplitter, QDateEdit, QMessageBox, QTableWidgetItem, QCheckBox, QHeaderView
)
from ui.custom_widgets import DateEditWithToday

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

# 👉 IMPORT SHARED SERVICE
from services.spectral_import_service import SpectralImportService


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
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Visual polish only: keep behavior and structure unchanged
        self.setObjectName("dataManagementRoot")
        self.setStyleSheet("""
            QWidget#dataManagementRoot {
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
        filter_layout.setColumnStretch(1, 1)
        filter_layout.setColumnStretch(5, 1)
        filter_layout.setColumnStretch(7, 1)
        filter_layout.setColumnStretch(11, 1)

        filter_layout.addWidget(QLabel("Creation time:"), 0, 0)

        self.date_from = DateEditWithToday()
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setDisplayFormat("dd MMMM yyyy")
        self.date_from.setMinimumWidth(150)

        self.date_to = DateEditWithToday()
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
        btn_layout.setSpacing(8)

        self.btn_inquiry = QPushButton("Inquiry")
        self.btn_batch_delete = QPushButton("Batch Deletion")
        self.btn_tick = QPushButton("Tick")
        self.btn_clear_selection = QPushButton("Clear Selection")
        self.btn_export = QPushButton("Data Export")
        self.btn_import = QPushButton("Data Import")
        self.btn_spectrogram = QPushButton("Spectrogram Display")

        btn_layout.addWidget(self.btn_inquiry)
        btn_layout.addWidget(self.btn_batch_delete)
        btn_layout.addWidget(self.btn_tick)
        btn_layout.addWidget(self.btn_clear_selection)
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
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setShowGrid(True)

        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setDefaultSectionSize(120)
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 34)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents)

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
        
        splitter.addWidget(self.table)


        # Right side: Spectrogram display (matplotlib) - clean, self-explanatory panel
        plot_panel = QWidget()
        plot_panel.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #d8e1eb;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        plot_panel_layout = QVBoxLayout(plot_panel)
        plot_panel_layout.setContentsMargins(12, 10, 12, 12)
        plot_panel_layout.setSpacing(8)

        plot_title = QLabel("Spectrogram Viewer")
        plot_title.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #1f2937; border: none;"
        )
        plot_subtitle = QLabel("Visualize absorbance vs wavelength for selected samples")
        plot_subtitle.setStyleSheet(
            "font-size: 11px; color: #4b5563; border: none;"
        )

        self.plot = PlotWidget()

        plot_panel_layout.addWidget(plot_title)
        plot_panel_layout.addWidget(plot_subtitle)
        plot_panel_layout.addWidget(self.plot)
        splitter.addWidget(plot_panel)

        splitter.setSizes([900, 620])
        main_layout.addWidget(splitter)

    def _derive_sample_name_from_filename(self, file_path):
        """Derive a logical sample name from imported scan filenames."""
        filename = os.path.basename(file_path)
        base_name, _ = os.path.splitext(filename)
        parts = [part.strip() for part in base_name.split('_') if part.strip()]

        candidate_tokens = []
        if len(parts) > 1:
            candidate_tokens.append(parts[1])
        if len(parts) > 2:
            candidate_tokens.append(parts[2])
        candidate_tokens.append(base_name)

        sample_name = ""
        for token in candidate_tokens:
            cleaned = token.strip()
            if not cleaned:
                continue

            # Example: ca95220260401-05136 -> ca952
            cleaned = re.sub(r"(?i)(20\d{6}.*)$", "", cleaned)
            cleaned = re.sub(r"[-_]+$", "", cleaned)

            if cleaned and not cleaned.isdigit():
                sample_name = cleaned
                break

        if not sample_name:
            sample_name = base_name
        if len(sample_name) > 50:
            sample_name = sample_name[:40] + sample_name[-10:]

        return sample_name[:50]

    # ---------------- SIGNALS ----------------
    def _connect_signals(self):
        self.btn_import.clicked.connect(self.open_data_import_dialog)
        self.btn_inquiry.clicked.connect(self.on_inquiry_clicked)
        self.btn_tick.clicked.connect(self.on_tick_clicked)
        self.btn_clear_selection.clicked.connect(self.on_clear_selection_clicked)
        self.btn_batch_delete.clicked.connect(self.on_batch_delete_clicked)
        self.btn_export.clicked.connect(self.on_export_clicked)
        self.btn_spectrogram.clicked.connect(self.on_spectrogram_display_clicked)
    
    def keyPressEvent(self, event):
        """Handle key press events - Escape to clear selection"""
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Escape:
            self.table.clearSelection()
        else:
            super().keyPressEvent(event)
    
    def on_clear_selection_clicked(self):
        """Clear highlighted rows and untick all checked rows."""
        self.table.clearSelection()
        self.on_header_checkbox_changed(False)
        self.checkbox_header.setChecked(False)

    def on_spectrogram_display_clicked(self):
        """Display spectra: for ticked rows from DB, or browse folder if nothing ticked."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import pandas as pd
        import matplotlib.pyplot as plt
        import os
        import numpy as np
        import matplotlib.cm as cm

        # First, check if any rows are ticked
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
        
        # If rows are ticked, display their spectra from database
        if ticked_rows:
            sample_ids = []
            for row_idx in ticked_rows:
                id_item = self.table.item(row_idx, 1)
                if id_item:
                    sample_ids.append(id_item.text())
            
            if not sample_ids:
                QMessageBox.warning(self, "Error", "Could not retrieve sample IDs")
                return
            
            # Fetch spectral data from database
            try:
                conn = self._get_db_connection()
                if not conn:
                    QMessageBox.critical(self, "Database Error", "Failed to connect to database")
                    return
                
                cursor = conn.cursor()
                all_wavelengths = []
                all_absorbances = []
                sample_names = []
                
                for sample_id in sample_ids:
                    query = """
                        SELECT s.sample_name, s.sample_id, md.wave, md.absorb
                        FROM sample s
                        LEFT JOIN model_data md ON s.sample_id = md.sample_id
                        WHERE s.sample_id = %s
                    """
                    cursor.execute(query, (sample_id,))
                    result = cursor.fetchone()
                    
                    if result and result['wave'] and result['absorb']:
                        sample_names.append(result['sample_name'])
                        wavelengths = [float(w) for w in result['wave'].split(',')]
                        absorbances = [float(a) for a in result['absorb'].split(',')]
                        all_wavelengths.append(wavelengths)
                        all_absorbances.append(absorbances)
                
                conn.close()
                
                # Plot the spectra
                self.plot.clear()
                if len(all_wavelengths) == 0:
                    QMessageBox.warning(self, "No Data", "No spectral data found for selected samples")
                    return
                
                color_map = cm.get_cmap('tab10')
                for i, (wavelength, absorbance, name) in enumerate(zip(all_wavelengths, all_absorbances, sample_names)):
                    color = color_map(i % 10)
                    self.plot.ax.plot(wavelength, absorbance, linestyle='solid', color=color, linewidth=0.5, 
                                     antialiased=True, solid_capstyle='round', solid_joinstyle='round', label=name)
                
                self.plot.ax.set_xlabel('Wavelength (nm)')
                self.plot.ax.set_ylabel('Absorbance')
                self.plot.ax.set_title(f'Spectrogram Display ({len(sample_names)} Selected Samples)')
                self.plot.ax.grid(True, alpha=0.3)
                if len(sample_names) <= 10:  # Only show legend if not too many samples
                    self.plot.ax.legend(loc='best', fontsize=8)
                self.plot.figure.tight_layout()
                self.plot.canvas.draw()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to fetch spectral data:\n{str(e)}")
                import traceback
                traceback.print_exc()
            
            return
        
        # If no rows are ticked, show folder dialog (original behavior)
        folder_path = QFileDialog.getExistingDirectory(self, "Select a folder of CSVs")
        if not folder_path:
            return

        all_wavelengths = []
        all_absorbances = []
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
            self.plot.ax.plot(wavelength, absorbance, linestyle='solid', color=color, linewidth=1.0, 
                             antialiased=True, solid_capstyle='round', solid_joinstyle='round')
        self.plot.ax.set_xlabel('Wavelength (nm)')
        self.plot.ax.set_ylabel('Absorbance')
        self.plot.ax.set_title('Spectrogram Display (All Files)')
        self.plot.ax.grid(True, alpha=0.3)
        # Remove legend to avoid file name box
        self.plot.figure.tight_layout()
        self.plot.canvas.draw()
    def on_export_clicked(self):
        """Export each ticked sample as separate CSV with wavelength and absorbance columns."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import csv, os

        # Open file dialog for folder selection
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            return  # User cancelled

        # Get sample IDs from ticked rows
        sample_ids = []
        for row_idx in range(self.table.rowCount()):
            cb_widget = self.table.cellWidget(row_idx, 0)
            if cb_widget is not None:
                layout = cb_widget.layout()
                if layout is not None and layout.count() > 0:
                    checkbox = layout.itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                        # Get sample_id from column 1 (ID column)
                        id_item = self.table.item(row_idx, 1)
                        if id_item:
                            sample_ids.append(id_item.text())

        print(f"Export: Found {len(sample_ids)} ticked samples")
        
        if not sample_ids:
            QMessageBox.information(self, "Export", "No rows ticked for export.")
            return

        # Export each sample as separate CSV
        try:
            conn = self._get_db_connection()
            if not conn:
                QMessageBox.critical(self, "Database Error", "Failed to connect to database")
                return
            
            cursor = conn.cursor()
            exported_count = 0
            
            for sample_id in sample_ids:
                # Get sample name and spectral data
                query = """
                    SELECT s.sample_name, s.sample_id, md.wave, md.absorb
                    FROM sample s
                    LEFT JOIN model_data md ON s.sample_id = md.sample_id
                    WHERE s.sample_id = %s
                """
                cursor.execute(query, (sample_id,))
                result = cursor.fetchone()
                
                if not result:
                    print(f"Warning: No data found for sample_id {sample_id}")
                    continue
                
                sample_name = result['sample_name']
                wave_str = result['wave']
                absorb_str = result['absorb']
                
                if not wave_str or not absorb_str:
                    print(f"Warning: No spectral data for sample {sample_name}")
                    continue
                
                # Parse wavelength and absorbance strings
                try:
                    wavelengths = [float(w) for w in wave_str.split(',')]
                    absorbances = [float(a) for a in absorb_str.split(',')]
                    
                    if len(wavelengths) != len(absorbances):
                        print(f"Warning: Wavelength/absorbance mismatch for {sample_name}")
                        continue
                    
                    # Create filename: SampleName_SampleID.csv
                    filename = f"{sample_name}_{sample_id}.csv"
                    csv_path = os.path.join(folder, filename)
                    
                    # Write CSV with wavelength and value columns
                    with open(csv_path, "w", newline='', encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(['Wavelength', 'Value'])  # Header
                        for wave, absorb in zip(wavelengths, absorbances):
                            writer.writerow([wave, absorb])
                    
                    print(f"Exported: {filename}")
                    exported_count += 1
                    
                except Exception as e:
                    print(f"Error parsing spectral data for {sample_name}: {e}")
                    continue
            
            cursor.close()
            conn.close()
            
            if exported_count > 0:
                QMessageBox.information(self, "Export", f"Successfully exported {exported_count} CSV file(s) to:\n{folder}")
            else:
                QMessageBox.warning(self, "Export", "No samples were exported. Check if selected samples have spectral data.")
                
        except Exception as e:
            print(f"Export: Error occurred - {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    # ============= ACTIONS ============
    def on_header_checkbox_changed(self, checked):
        row_count = self.table.rowCount()
        for row_idx in range(row_count):
            checkbox = self._get_row_checkbox(row_idx)
            if checkbox is not None:
                checkbox.blockSignals(True)
                checkbox.setChecked(bool(checked))
                checkbox.blockSignals(False)

    def on_row_checkbox_changed(self):
        row_count = self.table.rowCount()
        all_checked = row_count > 0
        for row_idx in range(row_count):
            checkbox = self._get_row_checkbox(row_idx)
            if checkbox is None or not checkbox.isChecked():
                all_checked = False
                break
        self.checkbox_header.setChecked(all_checked)

    def _create_checkbox_widget(self):
        """Create a centered checkbox widget for the first column."""
        checkbox = QCheckBox()
        checkbox.stateChanged.connect(self.on_row_checkbox_changed)

        cb_widget = QWidget()
        cb_layout = QHBoxLayout(cb_widget)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cb_layout.addWidget(checkbox)
        cb_widget.setLayout(cb_layout)
        return cb_widget

    def _get_row_checkbox(self, row_idx):
        """Return the checkbox for a row, handling both wrapped and legacy widgets."""
        cb_widget = self.table.cellWidget(row_idx, 0)
        if isinstance(cb_widget, QCheckBox):
            return cb_widget
        if cb_widget is None:
            return None

        layout = cb_widget.layout()
        if layout is None or layout.count() == 0:
            return None

        checkbox = layout.itemAt(0).widget()
        return checkbox if isinstance(checkbox, QCheckBox) else None

    def _get_checked_row_indices(self):
        checked_rows = []
        for row_idx in range(self.table.rowCount()):
            checkbox = self._get_row_checkbox(row_idx)
            if checkbox is not None and checkbox.isChecked():
                checked_rows.append(row_idx)
        return checked_rows

    def _get_selected_row_indices(self):
        return sorted({row_index.row() for row_index in self.table.selectionModel().selectedRows()})

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
                md.model_length as wavelength_points,
                md.wave as wavelength,
                md.absorb as absorbance,
                '0' as detector_temp,
                '0' as humidity,
                s.create_time as creation_time
            FROM sample s
            LEFT JOIN model_data md ON s.sample_id = md.sample_id
            WHERE DATE(s.create_time) BETWEEN %s AND %s
            AND (s.sample_state IS NULL OR s.sample_state != 'Deleted')
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
                self.table.setCellWidget(row_idx, 0, self._create_checkbox_widget())
                # Convert ID to int if possible
                try:
                    row_data['id'] = int(row_data['id'])
                except Exception:
                    row_data['id'] = 0
                
                # Clean up creation time
                creation_time = self._format_creation_time(row_data.get('creation_time', ''))
                
                # Set each column in the order: ID, Sample Name, Instrument, Lot Number, Wavelength Points, Wavelength, Absorbance, Detector Temp, Humidity, Creation Time
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
                    creation_time
                ]

                # Set UserRole for correct sorting (ID and Wavelength Points as int, others as float/string as needed)
                numeric_columns = [0, 4]  # ID and Wavelength Points
                float_columns = [5, 7, 8]  # Wavelength, Detector Temp, Humidity
                absorbance_column = 6  # Absorbance column - sort by first value
                for col_idx, value in enumerate(columns):
                    item = SortableTableWidgetItem(str(value) if value is not None else "")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if col_idx in numeric_columns:
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, int(value))
                        except Exception:
                            item.setData(Qt.ItemDataRole.UserRole, 0)
                    elif col_idx == absorbance_column:
                        # For absorbance, extract first value from comma-separated string
                        try:
                            first_value = float(str(value).split(',')[0].strip())
                            item.setData(Qt.ItemDataRole.UserRole, first_value)
                        except Exception:
                            item.setData(Qt.ItemDataRole.UserRole, 0.0)
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

    def on_tick_clicked(self):
        """Check selected rows, or untick them if they are already all checked."""
        selected_rows = self._get_selected_row_indices()
        if not selected_rows:
            QMessageBox.information(self, "Info", "Please select rows first")
            return

        target_checked = not all(
            self._get_row_checkbox(row_idx) is not None and self._get_row_checkbox(row_idx).isChecked()
            for row_idx in selected_rows
        )

        changed_count = 0
        for row_idx in selected_rows:
            checkbox = self._get_row_checkbox(row_idx)
            if checkbox is None:
                continue
            if checkbox.isChecked() != target_checked:
                changed_count += 1
            checkbox.setChecked(target_checked)

        self.table.clearSelection()
        self.on_row_checkbox_changed()
        action = "Ticked" if target_checked else "Unticked"
        print(f"{action} {changed_count} selected row(s)")

    def on_batch_delete_clicked(self):
        """Delete rows from database and table using ticked rows or current row selection."""
        ticked_rows = self._get_checked_row_indices()
        selected_rows = self._get_selected_row_indices()
        rows_to_delete = ticked_rows or selected_rows

        if not rows_to_delete:
            QMessageBox.information(self, "Info", "Please tick or select rows to delete.")
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
            
            # Soft delete: Mark as deleted using sample_state flag
            deleted_count = 0
            for sample_id in sample_ids:
                try:
                    # Mark sample as deleted (soft delete)
                    cursor.execute("""
                        UPDATE sample 
                        SET sample_state = 'Deleted'
                        WHERE sample_id = %s
                    """, (sample_id,))
                    
                    deleted_count += 1
                    print(f"Soft deleted sample_id: {sample_id} (marked as Deleted)")
                except Exception as e:
                    print(f"Error soft deleting sample_id {sample_id}: {e}")
            
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
            
            QMessageBox.information(self, "Success", f"Successfully marked {deleted_count} record(s) as deleted")
            print(f"Soft deleted {deleted_count} records (marked as Deleted state)")
            
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
                # Check if multiple files were selected
                if len(data['paths']) > 1:
                    # Process multiple files like folder import
                    self._process_folder_import(data)
                else:
                    # Process single file
                    self._process_file_import(data)

    def _process_folder_import(self, data):
        """Process folder import: read CSV files, display in table, and save to database."""
        paths = data['paths']
        
        if not paths:
            QMessageBox.warning(self, "No files", "No files found in the selected folder.")
            return
        
        print(f"Processing {len(paths)} file(s)")
        
        # Capture batch import timestamp - all files in this import will have the same timestamp
        batch_import_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"Batch import started at: {batch_import_time}")
        
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
                    header_data = SpectralImportService.extract_csv_header_metadata(file_path)
                    
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
                    
                    # Unified sample name extraction for both file and folder
                    filename = os.path.basename(file_path)
                    sample_name = self._derive_sample_name_from_filename(file_path)
                    
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
                    # Note: Not using creation_time from header, using batch_import_time instead
                    
                    # Insert into database with batch import time
                    print(f"Inserting into database...")
                    instrument = data.get('instrument', 'Unknown')
                    
                    # Extract lot number based on mode
                    mode = data.get('mode', '').lower()
                    if 'folder' in mode:
                        folder_path = os.path.dirname(file_path)
                        folder_name = os.path.basename(folder_path)
                        separator = data.get('separator', '_')
                        if separator in folder_name:
                            lot_number = folder_name.split(separator)[0]
                        else:
                            lot_number = folder_name
                    else:
                        lot_number = data.get('lot', '')
                    
                    sample_id = SpectralImportService.insert_sample_to_db(
                        conn, sample_name, instrument, lot_number, absorb_points, 
                        wavelength_str, absorbance_str, data_df,
                        detector_temp, humidity, batch_import_time
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
                    self.table.setCellWidget(row, 0, self._create_checkbox_widget())
                    
                    # Column 1: ID (database sample_id)
                    self.table.setItem(row, 1, QTableWidgetItem(str(sample_id or "")))
                    
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
                    
                    # Column 5: Wavelength Points (count of data rows)
                    self.table.setItem(row, 5, QTableWidgetItem(str(absorb_points)))
                    
                    # Column 6: Wavelength (full comma-separated)
                    self.table.setItem(row, 6, QTableWidgetItem(wavelength_str))
                    
                    # Column 7: Absorbance (full comma-separated)
                    self.table.setItem(row, 7, QTableWidgetItem(absorbance_str))
                    
                    # Column 8: Detector Temperature
                    self.table.setItem(row, 8, QTableWidgetItem(detector_temp))
                    
                    # Column 9: Humidity
                    self.table.setItem(row, 9, QTableWidgetItem(humidity))
                    
                    # Column 10: Creation Time
                    self.table.setItem(row, 10, QTableWidgetItem(batch_import_time))
                    
                    print(f"Table row {row}: {filename} | {sample_name} | {instrument} | {lot} | {batch_import_time}")
                    
                    # Plot first file's data
                    if row == 0 and data_df is not None:
                        self._plot_spectrogram(data_df)
                    
                    row += 1
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Ensure all commits are flushed before closing
            conn.commit()
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
        
        # Capture import timestamp for single file
        batch_import_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"File import started at: {batch_import_time}")
        
        try:
            # Connect to database
            conn = self._get_db_connection()
            if not conn:
                QMessageBox.critical(self, "Database Error", "Failed to connect to database")
                return
            
            print(f"Processing single file: {file_path}")
            
            # Read CSV header rows (1-18) to extract metadata
            header_data = SpectralImportService.extract_csv_header_metadata(file_path)
            
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
            
            # Unified sample name extraction for both file and folder
            sample_name = self._derive_sample_name_from_filename(file_path)
            
            # Truncate sample_name to fit VARCHAR(50) limit
            if len(sample_name) > 50:
                sample_name = sample_name[:40] + sample_name[-10:]
                print(f"Truncated sample_name to 50 chars: {sample_name}")
            
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
            # Note: Using batch_import_time instead of header creation_time
            
            # Insert into database with batch import time
            instrument = data.get('instrument', 'Unknown')
            lot_number = data.get('lot', '')
            
            sample_id = SpectralImportService.insert_sample_to_db(
                conn, sample_name, instrument, lot_number, absorb_points, 
                wavelength_str, absorbance_str, data_df,
                detector_temp, humidity, batch_import_time
            )
            
            # Ensure commit is flushed before closing
            conn.commit()
            conn.close()
            
            # Add single row to table
            self.table.insertRow(0)
            
            # Column 0: Checkbox
            self.table.setCellWidget(0, 0, self._create_checkbox_widget())
            
            # Column 1: ID (database sample_id)
            self.table.setItem(0, 1, QTableWidgetItem(str(sample_id or "")))
            
            # Column 2: Sample Name (from dialog)
            self.table.setItem(0, 2, QTableWidgetItem(sample_name))
            
            # Column 3: Instrument (from dialog)
            instrument = data.get('instrument', 'Unknown')
            self.table.setItem(0, 3, QTableWidgetItem(instrument))
            
            # Column 4: Lot Number (from dialog)
            lot = data.get('lot', '')
            self.table.setItem(0, 4, QTableWidgetItem(lot))
            
            # Column 5: Wavelength Points
            self.table.setItem(0, 5, QTableWidgetItem(str(absorb_points)))
            
            # Column 6: Wavelength
            self.table.setItem(0, 6, QTableWidgetItem(wavelength_str))
            
            # Column 7: Absorbance
            self.table.setItem(0, 7, QTableWidgetItem(absorbance_str))
            
            # Column 8: Detector Temperature
            self.table.setItem(0, 8, QTableWidgetItem(detector_temp))
            
            # Column 9: Humidity
            self.table.setItem(0, 9, QTableWidgetItem(humidity))
            
            # Column 10: Creation Time
            self.table.setItem(0, 10, QTableWidgetItem(batch_import_time))
            
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

    # Removed: _extract_csv_header_metadata - now using SpectralImportService.extract_csv_header_metadata()

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

    # Removed: _insert_sample_to_db - now using SpectralImportService.insert_sample_to_db()

    # Removed: _generate_sample_id - now using SpectralImportService.generate_sample_id()

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
