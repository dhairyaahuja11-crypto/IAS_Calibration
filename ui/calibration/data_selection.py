from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget, QFrame,
    QDoubleSpinBox, QTableWidgetItem, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
import os
import json
import numpy as np
from datetime import datetime
from pathlib import Path
from ui.plot_widget import PlotWidget


class DataSelectionUI(QWidget):
    MAX_PLOT_SPECTRA = None
    COL_TICK = 0
    COL_SAMPLE_ID = 1
    COL_SAMPLE_NAME = 2
    COL_WAVELENGTH = 6
    COL_ABSORBANCE = 7
    COL_PROPERTY = 9

    def __init__(self):
        super().__init__()
        # Dictionary to track sample states: {sample_id: 'calibration' or 'validation' or None}
        self.sample_states = {}
        # Track currently loaded project
        self.current_project_id = None
        self.current_project_name = None
        self.current_project_instrument = None
        self._build_ui()
        self._load_projects()
        self._load_instruments()
        self._connect_signals()

    def _log(self, message):
        """Keep terminal output quiet unless debugging is needed."""
        return
    
    def _connect_signals(self):
        """Connect UI signals"""
        self.ok_btn.clicked.connect(self.on_ok_clicked)
        self.select_none_btn.clicked.connect(self.on_select_toggle_clicked)
        self.set_calibration_btn.clicked.connect(self.on_set_calibration_clicked)
        self.set_validation_btn.clicked.connect(self.on_set_validation_clicked)
        self.invalidation_btn.clicked.connect(self.on_invalidation_clicked)
        self.spectral_average_btn.clicked.connect(self.on_spectral_average_clicked)
        self.avg_ok_btn.clicked.connect(self.on_avg_ok_clicked)
    
    def keyPressEvent(self, event):
        """Handle key press events - Escape to clear selection"""
        from PyQt6.QtCore import Qt
        if self._handle_table_range_selection(event):
            return
        if event.key() == Qt.Key.Key_Escape:
            self.table.clearSelection()
        else:
            super().keyPressEvent(event)

    def _handle_table_range_selection(self, event):
        """Extend selection with Ctrl+Shift+Up/Down."""
        from PyQt6.QtCore import Qt

        if not (
            event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
            and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down)
        ):
            return False

        row_count = self.table.rowCount()
        if row_count == 0:
            return True

        current_row = self.table.currentRow()
        if current_row < 0:
            current_row = 0 if event.key() == Qt.Key.Key_Down else row_count - 1
            self.table.selectRow(current_row)
            self.table.setCurrentCell(current_row, self.COL_SAMPLE_ID)
            return True

        step = -1 if event.key() == Qt.Key.Key_Up else 1
        target_row = max(0, min(row_count - 1, current_row + step))

        if target_row == current_row:
            return True

        selection_model = self.table.selectionModel()
        target_index = self.table.model().index(target_row, self.COL_SAMPLE_ID)
        selection_model.select(
            target_index,
            selection_model.SelectionFlag.Select | selection_model.SelectionFlag.Rows
        )
        self.table.setCurrentCell(target_row, self.COL_SAMPLE_ID)
        self.table.scrollToItem(self.table.item(target_row, self.COL_SAMPLE_ID))
        return True
    
    def eventFilter(self, obj, event):
        """Filter events to detect clicks on empty table space"""
        from PyQt6.QtCore import QEvent
        
        if obj == self.table.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            index = self.table.indexAt(event.pos())
            if not index.isValid():
                self.table.clearSelection()
                return True
        
        return super().eventFilter(obj, event)
    
    def on_set_calibration_clicked(self):
        """Mark ticked or selected samples as calibration."""
        target_rows = self._get_target_rows()

        if not target_rows:
            QMessageBox.warning(self, "Warning", "Please tick or select samples first!")
            return

        for row in target_rows:
            sample_id_item = self.table.item(row, self.COL_SAMPLE_ID)
            if sample_id_item:
                self.sample_states[sample_id_item.text()] = 'calibration'

        self.table.clearSelection()
        self._apply_states_to_table()
        self._refresh_plot_from_states()
    
    def _plot_spectra(self, samples, sample_type='calibration'):
        """Plot spectral data for given samples"""
        self.plot.clear()
        self.plot.reset_axes(
            title="",
            xlabel="Wavelength (nm)",
            ylabel="Absorbance"
        )
        
        if not samples:
            self.plot.draw()
            return

        samples_to_plot = self._sample_rows_for_plot(samples, self.MAX_PLOT_SPECTRA)
        
        # Generate diverse colors for different samples
        import random
        random.seed(42)  # For consistent colors
        
        successful_plots = 0
        for sample in samples_to_plot:
            try:
                # Parse wavelength and absorbance
                wavelength_str = sample.get('wavelength', '')
                absorbance_str = sample.get('absorbance', '')
                
                if wavelength_str and absorbance_str:
                    wavelengths = [float(x.strip()) for x in wavelength_str.split(',') if x.strip()]
                    absorbances = [float(x.strip()) for x in absorbance_str.split(',') if x.strip()]
                    
                    if len(wavelengths) == len(absorbances) and len(wavelengths) > 0:
                        # Generate random color for each spectrum
                        color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
                        normalized = tuple(channel / 255 for channel in color)
                        self.plot.ax.plot(wavelengths, absorbances, color=normalized, linewidth=1)
                        successful_plots += 1
            except Exception as e:
                self._log(f"Error plotting spectrum: {e}")
        
        # Update title with count and configure appearance
        total_count = len(samples)
        if total_count > len(samples_to_plot):
            self.plot.ax.set_title(
                f"{successful_plots} of {total_count} absorbance spectrums of {sample_type} set"
            )
        else:
            self.plot.ax.set_title(f"{successful_plots} absorbance spectrums of {sample_type} set")
        self.plot.ax.grid(True, alpha=0.3)
        self.plot.draw()

    def _sample_rows_for_plot(self, rows, limit):
        """Reduce plot load by sampling rows evenly when the dataset is large."""
        if limit in (None, 0):
            return rows

        if len(rows) <= limit:
            return rows

        if limit <= 1:
            return rows[:1]

        last_index = len(rows) - 1
        indices = []
        for slot in range(limit):
            idx = round(slot * last_index / (limit - 1))
            if idx not in indices:
                indices.append(idx)

        return [rows[idx] for idx in indices]
    
    def on_set_validation_clicked(self):
        """Mark ticked or selected samples as validation."""
        target_rows = self._get_target_rows()

        if not target_rows:
            QMessageBox.warning(self, "Warning", "Please tick or select samples first!")
            return

        for row in target_rows:
            sample_id_item = self.table.item(row, self.COL_SAMPLE_ID)
            if sample_id_item:
                self.sample_states[sample_id_item.text()] = 'validation'

        self.table.clearSelection()
        self._apply_states_to_table()
        self._refresh_plot_from_states()

    def on_invalidation_clicked(self):
        """Clear calibration/validation assignment for ticked or selected samples."""
        target_rows = self._get_target_rows()

        if not target_rows:
            QMessageBox.warning(self, "Warning", "Please tick or select samples first!")
            return

        for row in target_rows:
            sample_id_item = self.table.item(row, self.COL_SAMPLE_ID)
            if sample_id_item:
                self.sample_states.pop(sample_id_item.text(), None)

        self.table.clearSelection()
        self._apply_states_to_table()
        self._refresh_plot_from_states()
    
    def on_select_toggle_clicked(self):
        """Toggle all row tick boxes on or off."""
        if self.select_none_btn.text() == "select none":
            self._set_all_row_ticks(False)
            self.select_none_btn.setText("select all")
        else:
            self._set_all_row_ticks(True)
            self.select_none_btn.setText("select none")
    
    def on_ok_clicked(self):
        """Handle OK button click to load project samples"""
        self._load_current_project_samples()

    def _selected_instrument_override(self):
        """Return the explicitly selected instrument from the UI when enabled."""
        if not getattr(self, "instrument_checkbox", None) or not self.instrument_checkbox.isChecked():
            return ""

        if not getattr(self, "instrument_cb", None):
            return ""

        value = self.instrument_cb.currentData()
        if value is None:
            value = self.instrument_cb.currentText()
        return str(value).strip() if value is not None else ""

    def _load_current_project_samples(self, project_id=None, preserve_states=False):
        """Load current project samples into the table and sample list."""
        if project_id is None:
            project_id = self.project_cb.currentData()
        
        if not project_id:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Warning", "Please select a project first!")
            return
        
        try:
            from services.data_selection_service import DataSelectionService
            
            # Store current project info
            self.current_project_id = project_id
            self.current_project_name = self.project_cb.currentText()
            previous_states = dict(self.sample_states) if preserve_states else {}
            
            # Fetch project info to get measurement index
            project_info = DataSelectionService.get_project_info(project_id)
            measurement_index = project_info.get('analysis_object', 'Protein') if project_info else 'Protein'
            self.current_measurement_index = measurement_index  # Store for later use
            self.current_project_instrument = project_info.get('instrument', '') if project_info else ''
            selected_instrument = self._selected_instrument_override()
            if selected_instrument:
                self.current_project_instrument = selected_instrument
            
            # Update table header with measurement index
            self.table.setHorizontalHeaderItem(self.COL_PROPERTY, QTableWidgetItem(measurement_index))
            
            # Fetch samples for the project - THIS ALREADY FILTERS BY PROJECT
            samples = DataSelectionService.get_project_samples(project_id)
            
            if not samples:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Information", "No samples found for this project.")
                self.sample_list_label.setText("")
                self.table.setRowCount(0)
                self.current_project_id = None
                self.current_project_name = None
                self.current_project_instrument = None
                self.sample_states = {}
                self.plot.clear()
                return
            
            # Update sample list label with UNIQUE sample names only
            unique_sample_names = []
            seen_names = set()
            for s in samples:
                name = s.get('sample_name', '')
                if name and name not in seen_names:
                    unique_sample_names.append(name)
                    seen_names.add(name)
            
            self.sample_list_label.setText("  ".join(unique_sample_names))
            
            self.populate_table(samples)
            self.sample_states = {
                sample_id: sample_state
                for sample_id, sample_state in previous_states.items()
                if self._table_contains_sample_id(sample_id)
            }
            self._apply_states_to_table()
            self._refresh_plot_from_states()
        
        except Exception as e:
            self._log(f"Error loading project samples: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to load samples: {str(e)}")
            self.current_project_id = None
            self.current_project_name = None
            self.current_project_instrument = None
    
    def populate_table(self, samples):
        """Populate the table with sample data"""
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        for sample in samples:
            row = self.table.rowCount()
            self.table.insertRow(row)

            tick_box = QCheckBox()
            tick_box.setStyleSheet("margin-left: 12px; margin-right: 12px;")
            tick_box.stateChanged.connect(self._sync_select_button_text)
            self.table.setCellWidget(row, self.COL_TICK, tick_box)
            
            # Columns: ID, sample name, instrument, serial number, wavelength points,
            #          wavelength, absorbance, creation time, Protein
            columns = [
                str(sample.get('sample_id', '')),  # Use actual sample_id from database
                str(sample.get('sample_name', '')),
                str(sample.get('instrument', '')),
                str(sample.get('serial_number', '')),
                str(sample.get('wavelength_points', '')),
                str(sample.get('wavelength', ''))[:20] + '...' if sample.get('wavelength', '') else '',
                str(sample.get('absorbance', ''))[:20] + '...' if sample.get('absorbance', '') else '',
                str(sample.get('create_time', '')),
                str(sample.get('property_value', ''))
            ]
            
            for col, value in enumerate(columns):
                from PyQt6.QtWidgets import QTableWidgetItem
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Store full data in UserRole
                actual_col = col + 1
                if actual_col == self.COL_SAMPLE_ID:
                    item.setData(Qt.ItemDataRole.UserRole, sample)
                elif actual_col == self.COL_WAVELENGTH:
                    item.setData(Qt.ItemDataRole.UserRole, sample.get('wavelength', ''))
                elif actual_col == self.COL_ABSORBANCE:
                    item.setData(Qt.ItemDataRole.UserRole, sample.get('absorbance', ''))
                self.table.setItem(row, actual_col, item)
        
        self.table.setSortingEnabled(True)
        self._sync_select_button_text()

    def _table_contains_sample_id(self, sample_id):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, self.COL_SAMPLE_ID)
            if item and item.text() == str(sample_id):
                return True
        return False

    def _apply_states_to_table(self):
        """Repaint table rows using the current calibration/validation state map."""
        default_color = QColor(Qt.GlobalColor.white)
        alt_color = QColor("#f8fbff")
        calibration_color = QColor(220, 255, 220)
        validation_color = QColor(255, 230, 240)

        for row in range(self.table.rowCount()):
            sample_id_item = self.table.item(row, self.COL_SAMPLE_ID)
            sample_id = sample_id_item.text() if sample_id_item else None
            state = self.sample_states.get(sample_id)

            if state == 'calibration':
                row_color = calibration_color
            elif state == 'validation':
                row_color = validation_color
            else:
                row_color = alt_color if row % 2 else default_color

            for col in range(1, self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(row_color)

    def _refresh_plot_from_states(self):
        """Rebuild the calibration graph from the current state assignments."""
        calibration_samples = []

        for row in range(self.table.rowCount()):
            sample_id_item = self.table.item(row, self.COL_SAMPLE_ID)
            if not sample_id_item:
                continue

            sample_id = sample_id_item.text()
            if self.sample_states.get(sample_id) != 'calibration':
                continue

            wavelength_item = self.table.item(row, self.COL_WAVELENGTH)
            absorbance_item = self.table.item(row, self.COL_ABSORBANCE)
            if wavelength_item and absorbance_item:
                calibration_samples.append({
                    'wavelength': wavelength_item.data(Qt.ItemDataRole.UserRole) or wavelength_item.text(),
                    'absorbance': absorbance_item.data(Qt.ItemDataRole.UserRole) or absorbance_item.text()
                })

        self._plot_spectra(calibration_samples, 'calibration')

    def _get_row_tickbox(self, row):
        widget = self.table.cellWidget(row, self.COL_TICK)
        return widget if isinstance(widget, QCheckBox) else None

    def _get_checked_rows(self):
        checked_rows = []
        for row in range(self.table.rowCount()):
            tick_box = self._get_row_tickbox(row)
            if tick_box and tick_box.isChecked():
                checked_rows.append(row)
        return checked_rows

    def _get_target_rows(self):
        checked_rows = self._get_checked_rows()
        if checked_rows:
            return checked_rows
        return sorted({item.row() for item in self.table.selectedItems()})

    def _set_all_row_ticks(self, checked):
        for row in range(self.table.rowCount()):
            tick_box = self._get_row_tickbox(row)
            if tick_box:
                tick_box.blockSignals(True)
                tick_box.setChecked(checked)
                tick_box.blockSignals(False)

    def _sync_select_button_text(self, *_):
        if self.table.rowCount() == 0:
            self.select_none_btn.setText("select all")
            return
        checked_count = len(self._get_checked_rows())
        self.select_none_btn.setText("select none" if checked_count > 0 else "select all")

    def on_spectral_average_clicked(self):
        """Process samples with spectral averaging and save to temp_data"""
        # Validate project is loaded
        if not self.current_project_id:
            QMessageBox.warning(
                self, 
                "Warning", 
                "Please select a project and click OK to load samples first!"
            )
            return
            
        if self.table.rowCount() == 0:
            QMessageBox.warning(
                self, 
                "Warning", 
                "No samples loaded from the project. Please click OK to load samples first!"
            )
            return
        
        try:
            # Get all samples from table (already filtered by project from on_ok_clicked)
            samples_data = self._extract_samples_from_table()
            
            if not samples_data:
                QMessageBox.warning(self, "Warning", "No valid sample data found!")
                return
            
            # Group samples by sample_name and calculate average
            averaged_data = self._calculate_spectral_average(samples_data)
            
            # Save to temp_data
            temp_dir = self._ensure_temp_directory()
            output_file = self._save_to_temp(averaged_data, temp_dir, averaged=True)
            
            QMessageBox.information(
                self, 
                "Success", 
                f"Spectral averaging completed!\n\n"
                f"Project: {self.current_project_name}\n"
                f"Processed {len(samples_data)} samples into {len(averaged_data)} averaged spectra.\n"
                f"Data saved to: {output_file}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to perform spectral averaging: {str(e)}")
    
    def on_avg_ok_clicked(self):
        """Process all samples without averaging and save to temp_data"""
        # Validate project is loaded
        if not self.current_project_id:
            QMessageBox.warning(
                self, 
                "Warning", 
                "Please select a project and click OK to load samples first!"
            )
            return
            
        if self.table.rowCount() == 0:
            QMessageBox.warning(
                self, 
                "Warning", 
                "No samples loaded from the project. Please click OK to load samples first!"
            )
            return
        
        try:
            # Get all samples from table (already filtered by project from on_ok_clicked)
            samples_data = self._extract_samples_from_table()
            
            if not samples_data:
                QMessageBox.warning(self, "Warning", "No valid sample data found!")
                return
            
            # Save to temp_data as-is (no averaging)
            temp_dir = self._ensure_temp_directory()
            output_file = self._save_to_temp(samples_data, temp_dir, averaged=False)
            
            QMessageBox.information(
                self, 
                "Success", 
                f"Data saved successfully!\n\n"
                f"Project: {self.current_project_name}\n"
                f"Saved {len(samples_data)} samples (all replicates included).\n"
                f"Data saved to: {output_file}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")
    
    def _extract_samples_from_table(self):
        """Extract all sample data from the table (only samples from current project)"""
        if not self.current_project_id:
            return []
            
        samples_data = []
        dropped_samples = []
        
        for row in range(self.table.rowCount()):
            try:
                sample_id_item = self.table.item(row, self.COL_SAMPLE_ID)
                sample_name_item = self.table.item(row, self.COL_SAMPLE_NAME)
                wavelength_item = self.table.item(row, self.COL_WAVELENGTH)
                absorbance_item = self.table.item(row, self.COL_ABSORBANCE)
                property_item = self.table.item(row, self.COL_PROPERTY)
                
                if not all([sample_id_item, sample_name_item, wavelength_item, absorbance_item]):
                    dropped_samples.append(f"Row {row + 1}: missing table data")
                    continue

                source_sample = sample_id_item.data(Qt.ItemDataRole.UserRole) or {}
                wavelength_data = source_sample.get('wavelength') if isinstance(source_sample, dict) else None
                absorbance_data = source_sample.get('absorbance') if isinstance(source_sample, dict) else None

                if not wavelength_data:
                    wavelength_data = wavelength_item.data(Qt.ItemDataRole.UserRole) or wavelength_item.text()
                if not absorbance_data:
                    absorbance_data = absorbance_item.data(Qt.ItemDataRole.UserRole) or absorbance_item.text()

                wavelengths = self._parse_numeric_series(wavelength_data)
                absorbances = self._parse_numeric_series(absorbance_data)

                if not wavelengths or not absorbances:
                    sample_name = sample_name_item.text() or f"Row {row + 1}"
                    dropped_samples.append(f"{sample_name}: empty or invalid spectral values")
                    continue

                if len(wavelengths) != len(absorbances):
                    sample_name = sample_name_item.text() or f"Row {row + 1}"
                    dropped_samples.append(
                        f"{sample_name}: wavelength/absorbance length mismatch ({len(wavelengths)} vs {len(absorbances)})"
                    )
                    continue
                
                # Check if sample is calibration or validation
                sample_id = sample_id_item.text()
                sample_type = self.sample_states.get(sample_id, None)
                
                samples_data.append({
                    'sample_id': sample_id,
                    'sample_name': sample_name_item.text(),
                    'project_id': self.current_project_id,
                    'project_name': self.current_project_name,
                    'instrument': (
                        self._selected_instrument_override()
                        or (source_sample.get('instrument', '') if isinstance(source_sample, dict) else '')
                    ),
                    'serial_number': source_sample.get('serial_number', '') if isinstance(source_sample, dict) else '',
                    'create_time': source_sample.get('create_time', '') if isinstance(source_sample, dict) else '',
                    'user_id': source_sample.get('user_id', '') if isinstance(source_sample, dict) else '',
                    'property_name': source_sample.get('property_name', '') if isinstance(source_sample, dict) else '',
                    'wavelengths': wavelengths,
                    'absorbances': absorbances,
                    'property_value': property_item.text() if property_item else '',
                    'wavelength_points': len(wavelengths),
                    'sample_type': sample_type  # 'calibration', 'validation', or None
                })
                
            except Exception as e:
                self._log(f"Error extracting row {row}: {e}")
                sample_name = sample_name_item.text() if sample_name_item else f"Row {row + 1}"
                dropped_samples.append(f"{sample_name}: {e}")
                continue

        if dropped_samples:
            preview = "\n".join(dropped_samples[:5])
            more = ""
            if len(dropped_samples) > 5:
                more = f"\n... and {len(dropped_samples) - 5} more"
            QMessageBox.warning(
                self,
                "Incomplete Spectra",
                f"Loaded {len(samples_data)} row(s), but {len(dropped_samples)} row(s) were skipped:\n\n{preview}{more}"
            )
        return samples_data

    def _parse_numeric_series(self, value):
        """Parse wavelengths/absorbances from stored table data."""
        if value is None:
            return []

        if isinstance(value, np.ndarray):
            return [float(item) for item in value.tolist()]

        if isinstance(value, (list, tuple)):
            parsed = []
            for item in value:
                text = str(item).strip()
                if not text:
                    continue
                parsed.append(float(text))
            return parsed

        text = str(value).strip()
        if not text:
            return []

        return [float(part.strip()) for part in text.split(',') if part.strip()]
    
    def _calculate_spectral_average(self, samples_data, tolerance=0.5):
        """
        Calculate spectral average for samples grouped by sample_name with wavelength matching.
        
        Args:
            samples_data: List of sample dictionaries with wavelengths and absorbances
            tolerance: Maximum allowed wavelength difference in nm (default: 0.5)
        
        Returns:
            List of averaged sample dictionaries
        """
        # Group samples by sample_name
        grouped = {}
        for sample in samples_data:
            name = sample['sample_name']
            if name not in grouped:
                grouped[name] = []
            grouped[name].append(sample)
        
        # Calculate average for each group
        averaged_data = []
        for sample_name, replicates in grouped.items():
            resolved_sample_type = self._resolve_group_sample_type(replicates)
            resolved_property_value = self._resolve_group_property_value(replicates)
            # Use the first replicate as reference for single-scan groups.
            ref_wavelengths = np.array(replicates[0]['wavelengths'], dtype=float)
            ref_absorbances = np.array(replicates[0]['absorbances'], dtype=float)
            
            # For single replicate, no averaging needed
            if len(replicates) == 1:
                averaged_data.append({
                    'sample_name': sample_name,
                    'replicate_count': 1,
                    'wavelengths': ref_wavelengths.tolist(),
                    'absorbances': ref_absorbances.tolist(),
                    'property_value': resolved_property_value,
                    'sample_type': resolved_sample_type,
                    'original_sample_ids': [replicates[0]['sample_id']],
                    'wavelength_matched': False
                })
                continue
            # Align all replicate scans to one wavelength grid and average all scans.
            # Keep tolerance argument for compatibility, but interpolation now ensures
            # every scan contributes to the final averaged spectrum.
            avg_wavelengths, avg_absorbances = self._average_all_replicate_scans(replicates)
            
            averaged_data.append({
                'sample_name': sample_name,
                'replicate_count': len(replicates),
                'matched_count': len(replicates),
                'wavelengths': avg_wavelengths.tolist(),
                'absorbances': avg_absorbances.tolist(),
                'property_value': resolved_property_value,
                'sample_type': resolved_sample_type,
                'original_sample_ids': [rep['sample_id'] for rep in replicates],
                'wavelength_matched': True,
                'skipped_replicates': []
            })
        
        return averaged_data

    def _average_all_replicate_scans(self, replicates):
        """Average absorbance across all scans for a sample using interpolation."""
        series = []
        for rep in replicates:
            wl = np.array(rep.get('wavelengths', []), dtype=float)
            ab = np.array(rep.get('absorbances', []), dtype=float)
            if wl.size == 0 or ab.size == 0 or wl.size != ab.size:
                continue

            sort_idx = np.argsort(wl)
            wl = wl[sort_idx]
            ab = ab[sort_idx]
            unique_wl, unique_idx = np.unique(wl, return_index=True)
            wl = unique_wl
            ab = ab[unique_idx]
            if wl.size > 1:
                series.append((wl, ab))

        if not series:
            fallback_wl = np.array(replicates[0].get('wavelengths', []), dtype=float)
            fallback_ab = np.array(replicates[0].get('absorbances', []), dtype=float)
            return fallback_wl, fallback_ab

        overlap_min = max(wl[0] for wl, _ in series)
        overlap_max = min(wl[-1] for wl, _ in series)

        reference_wl = series[0][0]
        if overlap_max > overlap_min:
            overlap_grid = reference_wl[(reference_wl >= overlap_min) & (reference_wl <= overlap_max)]
            if overlap_grid.size >= 2:
                target_wl = overlap_grid
            else:
                target_wl = reference_wl
        else:
            target_wl = reference_wl

        interpolated = []
        for wl, ab in series:
            interp = np.interp(target_wl, wl, ab, left=np.nan, right=np.nan)
            interpolated.append(interp)

        stacked = np.vstack(interpolated)
        avg_absorbances = np.nanmean(stacked, axis=0)

        if np.isnan(avg_absorbances).any():
            ref_interp = np.interp(target_wl, series[0][0], series[0][1])
            nan_mask = np.isnan(avg_absorbances)
            avg_absorbances[nan_mask] = ref_interp[nan_mask]

        return target_wl, avg_absorbances

    def _resolve_group_sample_type(self, replicates):
        """Resolve a single sample_type for an averaged replicate group."""
        normalized_types = {
            str(rep.get('sample_type', '')).strip().lower()
            for rep in replicates
            if str(rep.get('sample_type', '')).strip()
        }

        if 'validation' in normalized_types:
            return 'validation'
        if 'calibration' in normalized_types:
            return 'calibration'
        return None

    def _resolve_group_property_value(self, replicates):
        """Resolve one sample-level property value from all scans in the group."""
        raw_values = []
        for rep in replicates:
            value = str(rep.get('property_value', '')).strip()
            if not value or value == '0' or value.lower() == 'nan':
                continue
            raw_values.append(value)

        if not raw_values:
            return ''

        numeric_values = []
        for value in raw_values:
            try:
                numeric_values.append(float(value))
            except (TypeError, ValueError):
                numeric_values = []
                break

        if numeric_values:
            rounded_counts = {}
            for value in numeric_values:
                key = f"{value:.6f}"
                rounded_counts[key] = rounded_counts.get(key, 0) + 1
            best_key = max(rounded_counts, key=rounded_counts.get)
            return f"{float(best_key):.4f}"

        text_counts = {}
        for value in raw_values:
            text_counts[value] = text_counts.get(value, 0) + 1
        return max(text_counts, key=text_counts.get)
    
    def _ensure_temp_directory(self):
        """Create temp_data directory if it doesn't exist"""
        # Create temp_data in the project root
        base_dir = Path(__file__).parent.parent.parent  # Go up to project root
        temp_dir = base_dir / 'temp_data'
        temp_dir.mkdir(exist_ok=True)
        return temp_dir
    
    def _save_to_temp(self, data, temp_dir, averaged=True):
        """Save processed data to temp_data directory"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        data_type = 'averaged' if averaged else 'raw'
        
        # Get project name from dropdown
        project_name = self.project_cb.currentText().replace(' ', '_') or 'unknown'
        
        # Save as JSON for easy reading and processing
        json_filename = f"{project_name}_{data_type}_{timestamp}.json"
        json_path = temp_dir / json_filename
        
        # Prepare data for JSON serialization
        output_data = {
            'metadata': {
                'project_name': self.project_cb.currentText(),
                'project_id': self.project_cb.currentData(),
                'instrument': self.current_project_instrument or self._selected_instrument_override(),
                'measurement_index': getattr(self, 'current_measurement_index', 'Protein'),
                'timestamp': timestamp,
                'data_type': data_type,
                'total_samples': len(data),
                'cropped': False  # Mark fresh data as not cropped
            },
            'samples': data
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        # Also save as CSV for easy viewing
        csv_filename = f"{project_name}_{data_type}_{timestamp}.csv"
        csv_path = temp_dir / csv_filename
        self._save_as_csv(data, csv_path, averaged)
        
        return json_path
    
    def _save_as_csv(self, data, csv_path, averaged):
        """Save data as CSV format"""
        import csv
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            if averaged:
                writer.writerow(['Sample Name', 'Replicate Count', 'Property Value', 'Sample Type', 
                               'Wavelengths (comma-separated)', 'Absorbances (comma-separated)'])
                
                for sample in data:
                    writer.writerow([
                        sample['sample_name'],
                        sample['replicate_count'],
                        sample['property_value'],
                        sample['sample_type'] or '',
                        ','.join(map(str, sample['wavelengths'])),
                        ','.join(map(str, sample['absorbances']))
                    ])
            else:
                writer.writerow(['Sample ID', 'Sample Name', 'Property Value', 'Sample Type',
                               'Wavelengths (comma-separated)', 'Absorbances (comma-separated)'])
                
                for sample in data:
                    writer.writerow([
                        sample['sample_id'],
                        sample['sample_name'],
                        sample['property_value'],
                        sample['sample_type'] or '',
                        ','.join(map(str, sample['wavelengths'])),
                        ','.join(map(str, sample['absorbances']))
                    ])

    
    def _load_projects(self):
        """Load all projects into the dropdown"""
        try:
            from services.data_selection_service import DataSelectionService
            
            projects = DataSelectionService.get_all_projects()
            
            self.project_cb.clear()
            self.project_cb.addItem("", None)  # Empty option
            
            for project in projects:
                project_name = project.get('project_name', '')
                project_id = project.get('project_id', '')
                self.project_cb.addItem(project_name, project_id)
        
        except Exception:
            pass
    
    def _load_instruments(self):
        """Load all instruments into the dropdown"""
        try:
            from services.data_selection_service import DataSelectionService
            
            instruments = DataSelectionService.get_instruments()
            
            self.instrument_cb.clear()
            self.instrument_cb.addItem("", None)  # Empty option
            
            for instrument in instruments:
                self.instrument_cb.addItem(instrument, instrument)
        
        except Exception:
            pass
    
    def refresh_dropdowns(self):
        """Refresh project and instrument dropdowns - called when tab becomes active"""
        self._load_projects()
        self._load_instruments()

    def refresh_current_project(self):
        """Refresh the currently loaded project so sample list and graph stay in sync."""
        if not self.current_project_id:
            return

        index = self.project_cb.findData(self.current_project_id)
        if index >= 0:
            self.project_cb.setCurrentIndex(index)
        self._load_current_project_samples(project_id=self.current_project_id, preserve_states=True)


    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # ================= TOP ROW (Project/Instrument/Buttons + Sample List + Measurement) =================
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        
        # --- LEFT: Project, Instrument, and Action Buttons ---
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_panel.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #d8e1eb; border-radius: 8px; }")
        left_top = QVBoxLayout(left_panel)
        left_top.setContentsMargins(10, 10, 10, 10)
        left_top.setSpacing(8)
        
        project_layout = QHBoxLayout()
        project_layout.setSpacing(8)
        project_layout.addWidget(QLabel("project:"))
        self.project_cb = QComboBox()
        self.project_cb.setMinimumHeight(30)
        self.project_cb.setMinimumWidth(150)
        project_layout.addWidget(self.project_cb)
        project_layout.addStretch()
        left_top.addLayout(project_layout)
        
        instrument_layout = QHBoxLayout()
        instrument_layout.setSpacing(8)
        instrument_layout.addWidget(QLabel("instrument:"))
        self.instrument_checkbox = QCheckBox()
        instrument_layout.addWidget(self.instrument_checkbox)
        self.instrument_cb = QComboBox()
        self.instrument_cb.setMinimumHeight(30)
        self.instrument_cb.setMinimumWidth(110)
        instrument_layout.addWidget(self.instrument_cb)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setMinimumHeight(30)
        self.ok_btn.setMinimumWidth(88)
        instrument_layout.addWidget(self.ok_btn)
        instrument_layout.addStretch()
        left_top.addLayout(instrument_layout)
        
        # Action Buttons (fill remaining space)
        self.select_none_btn = QPushButton("select none")
        self.set_calibration_btn = QPushButton("set as calibration")
        self.set_validation_btn = QPushButton("set as validation")
        self.invalidation_btn = QPushButton("invalidation")

        for btn in [
            self.select_none_btn,
            self.set_calibration_btn,
            self.set_validation_btn,
            self.invalidation_btn
        ]:
            btn.setMinimumHeight(32)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        left_top.addWidget(self.select_none_btn)
        left_top.addWidget(self.set_calibration_btn)
        left_top.addWidget(self.set_validation_btn)
        left_top.addWidget(self.invalidation_btn)
        left_top.addStretch(1)
        
        left_panel.setFixedHeight(232)
        left_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        top_row.addWidget(left_panel, 2)
        
        # --- MIDDLE: Sample List ---
        sample_panel = QFrame()
        sample_panel.setFrameShape(QFrame.Shape.StyledPanel)
        sample_panel.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #d8e1eb; border-radius: 8px; }")
        sample_list_layout = QVBoxLayout(sample_panel)
        sample_list_layout.setContentsMargins(10, 10, 10, 10)
        sample_list_layout.setSpacing(8)

        sample_title = QLabel("sample list:")
        sample_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sample_list_layout.addWidget(sample_title)
        self.sample_list_label = QLabel("")
        self.sample_list_label.setWordWrap(True)
        self.sample_list_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.sample_list_label.setStyleSheet(
            "background-color: #f9fbff; padding: 10px; border: 1px solid #d8e1eb; border-radius: 6px;"
        )
        self.sample_list_label.setMinimumHeight(0)
        self.sample_list_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sample_list_layout.addWidget(self.sample_list_label, 1)
        sample_panel.setFixedHeight(232)
        sample_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        top_row.addWidget(sample_panel, 2)
        
        # --- RIGHT: Measurement Controls ---
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_panel.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #d8e1eb; border-radius: 8px; }")
        right_top = QVBoxLayout(right_panel)
        right_top.setContentsMargins(10, 10, 10, 10)
        right_top.setSpacing(8)
        
        measure_frame = QFrame()
        measure_frame.setFrameStyle(QFrame.Shape.Box)
        measure_frame.setStyleSheet("QFrame { border: 1px solid #d8e1eb; border-radius: 6px; }")
        measure_layout = QGridLayout(measure_frame)
        measure_layout.setHorizontalSpacing(6)
        measure_layout.setVerticalSpacing(6)
        
        measure_layout.addWidget(QLabel("measurement index:"), 0, 0)
        self.index_cb = QComboBox()
        self.index_cb.addItems(["leverage value"])
        self.index_cb.setMinimumHeight(30)
        self.index_cb.setMinimumWidth(130)
        measure_layout.addWidget(self.index_cb, 0, 1)
        
        measure_layout.addWidget(QLabel("Protein"), 0, 2)
        
        measure_layout.addWidget(QLabel("contribution rate:"), 1, 0)
        self.contrib_spin = QDoubleSpinBox()
        self.contrib_spin.setRange(0, 1)
        self.contrib_spin.setSingleStep(0.01)
        self.contrib_spin.setValue(0.90)
        self.contrib_spin.setMinimumHeight(30)
        self.contrib_spin.setMinimumWidth(110)
        measure_layout.addWidget(self.contrib_spin, 1, 1)
        
        self.invalidation_measure_btn = QPushButton("invalidation")
        self.invalidation_measure_btn.setMinimumHeight(30)
        self.invalidation_measure_btn.setMinimumWidth(96)
        measure_layout.addWidget(self.invalidation_measure_btn, 1, 2)
        
        self.order_cb = QComboBox()
        self.order_cb.addItems(["ascending", "descending"])
        self.order_cb.setMinimumHeight(30)
        self.order_cb.setMinimumWidth(110)
        measure_layout.addWidget(self.order_cb, 0, 3)
        
        measure_layout.addWidget(QLabel("each sample from"), 1, 3)
        self.from_spin = QSpinBox()
        self.from_spin.setValue(0)
        self.from_spin.setMaximum(1000)
        self.from_spin.setMinimumHeight(30)
        self.from_spin.setMinimumWidth(84)
        measure_layout.addWidget(self.from_spin, 1, 4)
        
        measure_layout.addWidget(QLabel("start, get"), 1, 5)
        self.count_spin = QSpinBox()
        self.count_spin.setValue(10)
        self.count_spin.setMaximum(1000)
        self.count_spin.setMinimumHeight(30)
        self.count_spin.setMinimumWidth(84)
        measure_layout.addWidget(self.count_spin, 1, 6)
        
        measure_layout.addWidget(QLabel("number of data"), 1, 7)
        
        self.select_data_btn = QPushButton("select data")
        self.select_data_btn.setMinimumHeight(30)
        self.select_data_btn.setMinimumWidth(128)
        measure_layout.addWidget(self.select_data_btn, 0, 4, 1, 2)
        
        right_top.addWidget(measure_frame)
        
        avg_layout = QHBoxLayout()
        avg_layout.setSpacing(6)
        self.spectral_average_btn = QPushButton("spectral average")
        self.spectral_average_btn.setMinimumHeight(30)
        self.spectral_average_btn.setMinimumWidth(120)
        avg_layout.addWidget(self.spectral_average_btn)
        self.avg_ok_btn = QPushButton("OK")
        self.avg_ok_btn.setMinimumHeight(30)
        self.avg_ok_btn.setMinimumWidth(74)
        avg_layout.addWidget(self.avg_ok_btn)
        avg_layout.addStretch()
        right_top.addLayout(avg_layout)
        
        right_panel.setFixedHeight(232)
        right_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        top_row.addWidget(right_panel, 5)
        
        main_layout.addLayout(top_row, 0)
        
        # ================= BOTTOM ROW (Table + Plot) =================
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        
        # --- Table ---
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "tick", "ID", "sample name", "instrument", "serial number",
            "wavelength points", "wavelength", "absorbance",
            "creation time", "Protein"
        ])
        # Set selection behavior to select entire rows
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8fbff;
                border: 1px solid #d8e1eb;
                border-radius: 8px;
                gridline-color: #e5ebf2;
            }
            QHeaderView::section {
                background-color: #eef3f9;
                border: 1px solid #d8e1eb;
                padding: 6px;
                font-weight: 600;
            }
        """)
        
        # Install event filter to detect clicks on empty table space
        self.table.viewport().installEventFilter(self)
        
        bottom_row.addWidget(self.table, 3)
        
        # --- Plot ---
        self.plot = PlotWidget(show_toolbar=True)
        self.plot.reset_axes(
            title="60 absorbance spectrums of calibration set",
            xlabel="wavelength",
            ylabel="absorbance(AU)"
        )
        self.plot.setStyleSheet("border: 1px solid #d8e1eb; border-radius: 8px; background: #ffffff;")
        bottom_row.addWidget(self.plot, 2)
        
        main_layout.addLayout(bottom_row, 1)
