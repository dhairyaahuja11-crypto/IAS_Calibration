from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget, QFrame,
    QDoubleSpinBox, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
import pyqtgraph as pg
import os
import json
import numpy as np
from datetime import datetime
from pathlib import Path


class DataSelectionUI(QWidget):
    def __init__(self):
        super().__init__()
        # Dictionary to track sample states: {sample_id: 'calibration' or 'validation' or None}
        self.sample_states = {}
        # Track currently loaded project
        self.current_project_id = None
        self.current_project_name = None
        self._build_ui()
        self._load_projects()
        self._load_instruments()
        self._connect_signals()
    
    def _connect_signals(self):
        """Connect UI signals"""
        self.ok_btn.clicked.connect(self.on_ok_clicked)
        self.select_none_btn.clicked.connect(self.on_select_toggle_clicked)
        self.set_calibration_btn.clicked.connect(self.on_set_calibration_clicked)
        self.set_validation_btn.clicked.connect(self.on_set_validation_clicked)
        self.spectral_average_btn.clicked.connect(self.on_spectral_average_clicked)
        self.avg_ok_btn.clicked.connect(self.on_avg_ok_clicked)
    
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
            index = self.table.indexAt(event.pos())
            if not index.isValid():
                self.table.clearSelection()
                return True
        
        return super().eventFilter(obj, event)
    
    def on_set_calibration_clicked(self):
        """Mark selected samples as calibration"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Warning", "Please select samples first!")
            return
        
        # Mark samples as calibration
        calibration_samples = []
        for row in selected_rows:
            sample_id_item = self.table.item(row, 0)  # ID column
            if sample_id_item:
                sample_id = sample_id_item.text()
                self.sample_states[sample_id] = 'calibration'
                # Visually indicate calibration (pastel green background)
                pastel_green = QColor(220, 255, 220)
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(pastel_green)
                
                # Get spectral data for plotting
                wavelength_item = self.table.item(row, 5)  # Wavelength column
                absorbance_item = self.table.item(row, 6)  # Absorbance column
                if wavelength_item and absorbance_item:
                    wavelength_text = wavelength_item.data(Qt.ItemDataRole.UserRole) or wavelength_item.text()
                    absorbance_text = absorbance_item.data(Qt.ItemDataRole.UserRole) or absorbance_item.text()
                    calibration_samples.append({
                        'wavelength': wavelength_text,
                        'absorbance': absorbance_text
                    })
        
        # Clear selection to show the new colors immediately
        self.table.clearSelection()
        
        # Update plot with calibration samples
        self._plot_spectra(calibration_samples, 'calibration')
        
        print(f"Set {len(selected_rows)} samples as calibration")
        print(f"Current states: {self.sample_states}")
    
    def _plot_spectra(self, samples, sample_type='calibration'):
        """Plot spectral data for given samples"""
        self.plot.clear()
        
        if not samples:
            return
        
        # Generate diverse colors for different samples
        import random
        random.seed(42)  # For consistent colors
        
        successful_plots = 0
        for sample in samples:
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
                        self.plot.plot(
                            wavelengths, absorbances, 
                            pen=pg.mkPen(color=color, width=1),
                            antialias=True,
                            connect='all'
                        )
                        successful_plots += 1
            except Exception as e:
                print(f"Error plotting spectrum: {e}")
        
        # Update title with count and configure appearance
        self.plot.setTitle(f"{successful_plots} absorbance spectrums of {sample_type} set")
        self.plot.setLabel('left', 'Absorbance')
        self.plot.setLabel('bottom', 'Wavelength (nm)')
        self.plot.showGrid(x=True, y=True, alpha=0.3)
    
    def on_set_validation_clicked(self):
        """Mark selected samples as validation"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Warning", "Please select samples first!")
            return
        
        # Mark samples as validation
        for row in selected_rows:
            sample_id_item = self.table.item(row, 0)  # ID column
            if sample_id_item:
                sample_id = sample_id_item.text()
                self.sample_states[sample_id] = 'validation'
                # Visually indicate validation (pastel pink background)
                pastel_pink = QColor(255, 230, 240)
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(pastel_pink)
        
        # Clear selection to show the new colors immediately
        self.table.clearSelection()
        
        print(f"Set {len(selected_rows)} samples as validation")
        print(f"Current states: {self.sample_states}")
    
    def on_select_toggle_clicked(self):
        """Toggle between select all and select none"""
        if self.select_none_btn.text() == "select none":
            # Deselect all rows
            self.table.clearSelection()
            self.select_none_btn.setText("select all")
        else:
            # Select all rows
            self.table.selectAll()
            self.select_none_btn.setText("select none")
    
    def on_ok_clicked(self):
        """Handle OK button click to load project samples"""
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
            
            # Fetch project info to get measurement index
            project_info = DataSelectionService.get_project_info(project_id)
            measurement_index = project_info.get('analysis_object', 'Protein') if project_info else 'Protein'
            self.current_measurement_index = measurement_index  # Store for later use
            
            # Update table header with measurement index
            self.table.setHorizontalHeaderItem(8, QTableWidgetItem(measurement_index))
            
            # Fetch samples for the project - THIS ALREADY FILTERS BY PROJECT
            samples = DataSelectionService.get_project_samples(project_id)
            
            if not samples:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Information", "No samples found for this project.")
                self.sample_list_label.setText("")
                self.table.setRowCount(0)
                self.current_project_id = None
                self.current_project_name = None
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
            
            # Populate table with ALL replicates FROM THIS PROJECT ONLY
            self.populate_table(samples)
            
            print(f"Loaded {len(samples)} samples from project: {self.current_project_name} (ID: {project_id})")
        
        except Exception as e:
            print(f"Error loading project samples: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to load samples: {str(e)}")
            self.current_project_id = None
            self.current_project_name = None
    
    def populate_table(self, samples):
        """Populate the table with sample data"""
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        
        for idx, sample in enumerate(samples):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
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
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, sample)
                elif col == 5:  # Wavelength column - store full data
                    item.setData(Qt.ItemDataRole.UserRole, sample.get('wavelength', ''))
                elif col == 6:  # Absorbance column - store full data
                    item.setData(Qt.ItemDataRole.UserRole, sample.get('absorbance', ''))
                self.table.setItem(row, col, item)
        
        self.table.setSortingEnabled(True)

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
            
            print(f"Spectral average completed for project: {self.current_project_name}")
            print(f"Saved to: {output_file}")
            print(f"Original samples: {len(samples_data)}, Averaged: {len(averaged_data)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to perform spectral averaging: {str(e)}")
            print(f"Error in spectral averaging: {e}")
            import traceback
            traceback.print_exc()
    
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
            
            print(f"Raw data saved for project: {self.current_project_name}")
            print(f"Saved to: {output_file}")
            print(f"Total samples: {len(samples_data)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")
            print(f"Error in saving data: {e}")
            import traceback
            traceback.print_exc()
    
    def _extract_samples_from_table(self):
        """Extract all sample data from the table (only samples from current project)"""
        if not self.current_project_id:
            print("Warning: No project selected, cannot extract samples")
            return []
            
        samples_data = []
        
        print(f"\nExtracting samples from project: {self.current_project_name} (ID: {self.current_project_id})")
        
        for row in range(self.table.rowCount()):
            try:
                sample_id_item = self.table.item(row, 0)
                sample_name_item = self.table.item(row, 1)
                wavelength_item = self.table.item(row, 5)
                absorbance_item = self.table.item(row, 6)
                property_item = self.table.item(row, 8)
                
                if not all([sample_id_item, sample_name_item, wavelength_item, absorbance_item]):
                    continue
                
                # Get full wavelength and absorbance data from UserRole
                wavelength_data = wavelength_item.data(Qt.ItemDataRole.UserRole) or wavelength_item.text()
                absorbance_data = absorbance_item.data(Qt.ItemDataRole.UserRole) or absorbance_item.text()
                
                # Parse wavelength and absorbance
                wavelengths = [float(x.strip()) for x in wavelength_data.split(',') if x.strip()]
                absorbances = [float(x.strip()) for x in absorbance_data.split(',') if x.strip()]
                
                if len(wavelengths) != len(absorbances) or len(wavelengths) == 0:
                    print(f"Warning: Skipping row {row} - wavelength/absorbance mismatch")
                    continue
                
                # Check if sample is calibration or validation
                sample_id = sample_id_item.text()
                sample_type = self.sample_states.get(sample_id, None)
                
                samples_data.append({
                    'sample_id': sample_id,
                    'sample_name': sample_name_item.text(),
                    'project_id': self.current_project_id,
                    'project_name': self.current_project_name,
                    'wavelengths': wavelengths,
                    'absorbances': absorbances,
                    'property_value': property_item.text() if property_item else '',
                    'sample_type': sample_type  # 'calibration', 'validation', or None
                })
                
            except Exception as e:
                print(f"Error extracting row {row}: {e}")
                continue
        
        print(f"Extracted {len(samples_data)} samples from project")
        return samples_data
    
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
        
        print(f"\nSpectral Averaging Summary (with wavelength matching):")
        print(f"Total unique samples: {len(grouped)}")
        print(f"Wavelength tolerance: {tolerance} nm")
        for name, replicates in grouped.items():
            print(f"  {name}: {len(replicates)} replicate(s)")
        
        # Calculate average for each group
        averaged_data = []
        for sample_name, replicates in grouped.items():
            # Use the first replicate as reference
            ref_wavelengths = np.array(replicates[0]['wavelengths'])
            ref_absorbances = np.array(replicates[0]['absorbances'])
            
            # For single replicate, no averaging needed
            if len(replicates) == 1:
                averaged_data.append({
                    'sample_name': sample_name,
                    'replicate_count': 1,
                    'wavelengths': ref_wavelengths.tolist(),
                    'absorbances': ref_absorbances.tolist(),
                    'property_value': replicates[0]['property_value'],
                    'sample_type': replicates[0]['sample_type'],
                    'original_sample_ids': [replicates[0]['sample_id']],
                    'wavelength_matched': False
                })
                continue
            
            # Collect absorbances aligned to reference wavelengths
            aligned_absorbances = [ref_absorbances]
            matched_count = 1
            skipped_replicates = []
            
            # Process remaining replicates
            for i, rep in enumerate(replicates[1:], start=1):
                rep_wavelengths = np.array(rep['wavelengths'])
                rep_absorbances = np.array(rep['absorbances'])
                
                # Validate wavelength range coverage
                if (rep_wavelengths[0] > ref_wavelengths[0] + tolerance or 
                    rep_wavelengths[-1] < ref_wavelengths[-1] - tolerance):
                    print(f"    WARNING: Replicate {i+1} wavelength range mismatch - skipping")
                    skipped_replicates.append(i)
                    continue
                
                # Align this replicate's absorbances to reference wavelengths
                aligned_abs = np.zeros_like(ref_absorbances)
                all_within_tolerance = True
                
                for j, ref_wl in enumerate(ref_wavelengths):
                    # Find closest wavelength index using np.argmin(np.abs(...))
                    closest_idx = np.argmin(np.abs(rep_wavelengths - ref_wl))
                    closest_wl = rep_wavelengths[closest_idx]
                    
                    # Check if within tolerance
                    if np.abs(closest_wl - ref_wl) > tolerance:
                        print(f"    WARNING: Replicate {i+1} wavelength {ref_wl:.2f} nm "
                              f"not matched (closest: {closest_wl:.2f} nm, "
                              f"difference: {abs(closest_wl - ref_wl):.2f} nm) - skipping replicate")
                        all_within_tolerance = False
                        break
                    
                    # Use the matched absorbance value
                    aligned_abs[j] = rep_absorbances[closest_idx]
                
                if all_within_tolerance:
                    aligned_absorbances.append(aligned_abs)
                    matched_count += 1
                else:
                    skipped_replicates.append(i)
            
            # Calculate mean absorbance across aligned replicates
            # Inclusive of all matched replicates [0:matched_count]
            avg_absorbances = np.mean(aligned_absorbances, axis=0)
            
            if skipped_replicates:
                print(f"    Note: Used {matched_count}/{len(replicates)} replicates "
                      f"(skipped: {skipped_replicates})")
            
            # Use first replicate's metadata
            first_rep = replicates[0]
            
            averaged_data.append({
                'sample_name': sample_name,
                'replicate_count': len(replicates),
                'matched_count': matched_count,
                'wavelengths': ref_wavelengths.tolist(),
                'absorbances': avg_absorbances.tolist(),
                'property_value': first_rep['property_value'],
                'sample_type': first_rep['sample_type'],
                'original_sample_ids': [rep['sample_id'] for rep in replicates],
                'wavelength_matched': True,
                'skipped_replicates': skipped_replicates
            })
        
        return averaged_data
    
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
                'measurement_index': getattr(self, 'current_measurement_index', 'Protein'),
                'timestamp': timestamp,
                'data_type': data_type,
                'total_samples': len(data),
                'cropped': False  # Mark fresh data as not cropped
            },
            'samples': data
        }
        
        with open(json_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        # Also save as CSV for easy viewing
        csv_filename = f"{project_name}_{data_type}_{timestamp}.csv"
        csv_path = temp_dir / csv_filename
        self._save_as_csv(data, csv_path, averaged)
        
        print(f"Data saved to:")
        print(f"  JSON: {json_path}")
        print(f"  CSV: {csv_path}")
        
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
        
        except Exception as e:
            print(f"Error loading projects: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_instruments(self):
        """Load all instruments into the dropdown"""
        try:
            from services.data_selection_service import DataSelectionService
            
            instruments = DataSelectionService.get_instruments()
            
            self.instrument_cb.clear()
            self.instrument_cb.addItem("", None)  # Empty option
            
            for instrument in instruments:
                self.instrument_cb.addItem(instrument, instrument)
        
        except Exception as e:
            print(f"Error loading instruments: {e}")
            import traceback
            traceback.print_exc()
    
    def refresh_dropdowns(self):
        """Refresh project and instrument dropdowns - called when tab becomes active"""
        self._load_projects()
        self._load_instruments()


    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        # ================= TOP ROW (Project/Instrument/Buttons + Sample List + Measurement) =================
        top_row = QHBoxLayout()
        
        # --- LEFT: Project, Instrument, and Action Buttons ---
        left_top = QVBoxLayout()
        
        project_layout = QHBoxLayout()
        project_layout.addWidget(QLabel("project:"))
        self.project_cb = QComboBox()
        project_layout.addWidget(self.project_cb)
        project_layout.addStretch()
        left_top.addLayout(project_layout)
        
        instrument_layout = QHBoxLayout()
        instrument_layout.addWidget(QLabel("instrument:"))
        self.instrument_checkbox = QCheckBox()
        instrument_layout.addWidget(self.instrument_checkbox)
        self.instrument_cb = QComboBox()
        instrument_layout.addWidget(self.instrument_cb)
        self.ok_btn = QPushButton("OK")
        instrument_layout.addWidget(self.ok_btn)
        instrument_layout.addStretch()
        left_top.addLayout(instrument_layout)
        
        # Action Buttons (fill remaining space)
        self.select_none_btn = QPushButton("select none")
        self.set_calibration_btn = QPushButton("set as calibration")
        self.set_validation_btn = QPushButton("set as validation")
        self.invalidation_btn = QPushButton("invalidation")
        
        left_top.addWidget(self.select_none_btn)
        left_top.addWidget(self.set_calibration_btn)
        left_top.addWidget(self.set_validation_btn)
        left_top.addWidget(self.invalidation_btn)
        left_top.addStretch()
        
        top_row.addLayout(left_top, 2)
        
        # --- MIDDLE: Sample List ---
        sample_list_layout = QVBoxLayout()
        sample_list_layout.addWidget(QLabel("sample list:"))
        self.sample_list_label = QLabel("")
        self.sample_list_label.setWordWrap(True)
        self.sample_list_label.setStyleSheet("background-color: white; padding: 5px; border: 1px solid #ccc;")
        self.sample_list_label.setMinimumHeight(80)
        sample_list_layout.addWidget(self.sample_list_label)
        top_row.addLayout(sample_list_layout, 3)
        
        # --- RIGHT: Measurement Controls ---
        right_top = QVBoxLayout()
        
        measure_frame = QFrame()
        measure_frame.setFrameStyle(QFrame.Shape.Box)
        measure_layout = QGridLayout(measure_frame)
        
        measure_layout.addWidget(QLabel("measurement index:"), 0, 0)
        self.index_cb = QComboBox()
        self.index_cb.addItems(["leverage value"])
        measure_layout.addWidget(self.index_cb, 0, 1)
        
        measure_layout.addWidget(QLabel("Protein"), 0, 2)
        
        measure_layout.addWidget(QLabel("contribution rate:"), 1, 0)
        self.contrib_spin = QDoubleSpinBox()
        self.contrib_spin.setRange(0, 1)
        self.contrib_spin.setSingleStep(0.01)
        self.contrib_spin.setValue(0.90)
        measure_layout.addWidget(self.contrib_spin, 1, 1)
        
        self.invalidation_measure_btn = QPushButton("invalidation")
        measure_layout.addWidget(self.invalidation_measure_btn, 1, 2)
        
        self.order_cb = QComboBox()
        self.order_cb.addItems(["ascending", "descending"])
        measure_layout.addWidget(self.order_cb, 0, 3)
        
        measure_layout.addWidget(QLabel("each sample from"), 1, 3)
        self.from_spin = QSpinBox()
        self.from_spin.setValue(0)
        self.from_spin.setMaximum(1000)
        measure_layout.addWidget(self.from_spin, 1, 4)
        
        measure_layout.addWidget(QLabel("start, get"), 1, 5)
        self.count_spin = QSpinBox()
        self.count_spin.setValue(10)
        self.count_spin.setMaximum(1000)
        measure_layout.addWidget(self.count_spin, 1, 6)
        
        measure_layout.addWidget(QLabel("number of data"), 1, 7)
        
        self.select_data_btn = QPushButton("select data")
        measure_layout.addWidget(self.select_data_btn, 0, 4, 1, 2)
        
        right_top.addWidget(measure_frame)
        
        avg_layout = QHBoxLayout()
        self.spectral_average_btn = QPushButton("spectral average")
        avg_layout.addWidget(self.spectral_average_btn)
        self.avg_ok_btn = QPushButton("OK")
        avg_layout.addWidget(self.avg_ok_btn)
        avg_layout.addStretch()
        right_top.addLayout(avg_layout)
        
        top_row.addLayout(right_top, 3)
        
        main_layout.addLayout(top_row)
        
        # ================= BOTTOM ROW (Table + Plot) =================
        bottom_row = QHBoxLayout()
        
        # --- Table ---
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "ID", "sample name", "instrument", "serial number",
            "wavelength points", "wavelength", "absorbance",
            "creation time", "Protein"
        ])
        # Set selection behavior to select entire rows
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        
        # Install event filter to detect clicks on empty table space
        self.table.viewport().installEventFilter(self)
        
        bottom_row.addWidget(self.table, 3)
        
        # --- Plot ---
        self.plot = pg.PlotWidget()
        self.plot.setBackground('w')
        self.plot.setLabel("left", "absorbance(AU)")
        self.plot.setLabel("bottom", "wavelength")
        self.plot.showGrid(x=True, y=True)
        self.plot.setTitle("60 absorbance spectrums of calibration set")
        # Enable antialiasing for smooth lines
        self.plot.setAntialiasing(True)
        bottom_row.addWidget(self.plot, 2)
        
        main_layout.addLayout(bottom_row)
