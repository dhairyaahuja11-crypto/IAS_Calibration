from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QDialog, QDoubleSpinBox, QMessageBox, QSpinBox, QSizePolicy
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np
from collections import Counter
from services.spectral_processing_service import SpectralProcessingService
from services.preprocessing_service import PreprocessingService


class PreTreatmentUI(QWidget):
    def __init__(self):
        super().__init__()
        self.current_data = None
        self.original_spectra = None  # Original cropped data (never changes)
        self.processed_spectra = None  # Last processed result
        self.wavelengths = None
        self.applied_algorithms = []  # Track chain of applied algorithms
        self._build_ui()
        self._connect_signals()
        self._load_initial_data()
    
    def _connect_signals(self):
        """Connect UI signals"""
        self.intercept_algo.activated.connect(self.on_intercept_algo_activated)
        self.operation_btn.clicked.connect(self.on_operation_clicked)
        self.operation_combo_btn.clicked.connect(self.on_operation_combination_clicked)
        self.reset_btn.clicked.connect(self.on_reset_clicked)
        self.pretreat_combo.currentTextChanged.connect(self.on_pretreat_changed)

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ================= LEFT CONTROL PANEL =================
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.Shape.StyledPanel)
        control_frame.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #d8e1eb; border-radius: 8px; }"
        )
        control_frame.setMinimumWidth(300)
        control_frame.setMaximumWidth(340)
        control_panel = QVBoxLayout(control_frame)
        control_panel.setContentsMargins(10, 10, 10, 10)
        control_panel.setSpacing(8)

        self.reset_btn = QPushButton("reset")
        self.reset_btn.setMinimumHeight(34)
        control_panel.addWidget(self.reset_btn)

        control_panel.addSpacing(6)

        control_panel.addWidget(QLabel("interception algorithm:"))
        self.intercept_algo = QComboBox()
        self.intercept_algo.setMinimumHeight(34)
        self.intercept_algo.addItems(["LPG", "SPG", "Manual Selection"])
        control_panel.addWidget(self.intercept_algo)

        control_panel.addSpacing(6)

        self.intercept_btn = QPushButton("intercept data")
        self.intercept_btn.setMinimumHeight(34)
        control_panel.addWidget(self.intercept_btn)

        control_panel.addSpacing(6)

        control_panel.addWidget(QLabel("pre-treatment"))
        self.pretreat_combo = QComboBox()
        self.pretreat_combo.setMinimumHeight(34)
        self.pretreat_combo.addItems([
            "mean-centering","moving smoothing", "autoscaling",
            "SG smoothing","normalization", "detrending", "MSC",
            "SNV", "SG 1st derivative", "SG 2nd derivative"
        ])
        control_panel.addWidget(self.pretreat_combo)

        # ================= PARAMETER INPUTS =================
        # Moving Smoothing parameters
        self.moving_params_label = QLabel("window size:")
        self.moving_window = QSpinBox()
        self.moving_window.setRange(3, 15)
        self.moving_window.setValue(5)
        self.moving_window.setSingleStep(2)  # Odd numbers preferred
        
        # SG Smoothing parameters (shared by SG smoothing and derivatives)
        self.sg_window_label = QLabel("window length:")
        self.sg_window = QSpinBox()
        self.sg_window.setRange(5, 25)
        self.sg_window.setValue(11)
        self.sg_window.setSingleStep(2)  # Must be odd
        
        self.sg_polyorder_label = QLabel("polynomial order:")
        self.sg_polyorder = QSpinBox()
        self.sg_polyorder.setRange(1, 5)
        self.sg_polyorder.setValue(2)
        
        # Add to layout (initially hidden)
        control_panel.addWidget(self.moving_params_label)
        control_panel.addWidget(self.moving_window)
        control_panel.addWidget(self.sg_window_label)
        control_panel.addWidget(self.sg_window)
        control_panel.addWidget(self.sg_polyorder_label)
        control_panel.addWidget(self.sg_polyorder)
        
        # Hide all parameter inputs by default
        self.moving_params_label.hide()
        self.moving_window.hide()
        self.sg_window_label.hide()
        self.sg_window.hide()
        self.sg_polyorder_label.hide()
        self.sg_polyorder.hide()

        self.moving_window.setMinimumHeight(32)
        self.sg_window.setMinimumHeight(32)
        self.sg_polyorder.setMinimumHeight(32)

        control_panel.addSpacing(8)

        self.operation_btn = QPushButton("operation")
        self.operation_btn.setMinimumHeight(34)
        self.operation_combo_btn = QPushButton("operation combination")
        self.operation_combo_btn.setMinimumHeight(34)

        control_panel.addWidget(self.operation_btn)
        control_panel.addWidget(self.operation_combo_btn)

        control_panel.addStretch()

        main_layout.addWidget(control_frame, 0)

        # ================= RIGHT PLOTS AREA =================
        plots_layout = QGridLayout()
        plots_layout.setHorizontalSpacing(10)
        plots_layout.setVerticalSpacing(10)

        self.original_plot = self._create_plot(
            "original spectrogram",
            "absorbance(AU)",
            "wavelength"
        )
        plots_layout.addWidget(self.original_plot, 0, 0)

        self.treated_plot = self._create_plot(
            "spectrum after treatment",
            "absorbance(AU)",
            "wavelength"
        )
        plots_layout.addWidget(self.treated_plot, 0, 1)

        self.corr_plot = self._create_plot(
            "correlation coefficient diagram",
            "correlation coefficient",
            "wavelength"
        )
        plots_layout.addWidget(self.corr_plot, 1, 0)

        self.std_plot = self._create_plot(
            "standard deviation diagram",
            "standard deviation",
            "wavelength"
        )
        plots_layout.addWidget(self.std_plot, 1, 1)

        plots_frame = QFrame()
        plots_frame.setFrameShape(QFrame.Shape.StyledPanel)
        plots_frame.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #d8e1eb; border-radius: 8px; }"
        )
        plots_frame_layout = QVBoxLayout(plots_frame)
        plots_frame_layout.setContentsMargins(10, 10, 10, 10)
        plots_frame_layout.addLayout(plots_layout)
        plots_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout.addWidget(plots_frame, 1)
    
    def on_pretreat_changed(self, algorithm_name):
        """Show/hide parameter inputs based on selected algorithm"""
        # Hide all parameter inputs first
        self.moving_params_label.hide()
        self.moving_window.hide()
        self.sg_window_label.hide()
        self.sg_window.hide()
        self.sg_polyorder_label.hide()
        self.sg_polyorder.hide()
        
        # Show relevant inputs based on algorithm
        if algorithm_name == "moving smoothing":
            self.moving_params_label.show()
            self.moving_window.show()
        elif algorithm_name in ["SG smoothing", "SG 1st derivative", "SG 2nd derivative"]:
            self.sg_window_label.show()
            self.sg_window.show()
            self.sg_polyorder_label.show()
            self.sg_polyorder.show()
    
    def _get_algorithm_parameters(self, algorithm_name):
        """Get custom parameters from UI inputs based on algorithm"""
        params = {}
        
        if algorithm_name == "moving smoothing":
            params['window_size'] = self.moving_window.value()
        elif algorithm_name in ["SG smoothing", "SG 1st derivative", "SG 2nd derivative"]:
            params['window_length'] = self.sg_window.value()
            params['polyorder'] = self.sg_polyorder.value()
            
            # Set derivative order based on algorithm
            if algorithm_name == "SG smoothing":
                params['deriv'] = 0
            elif algorithm_name == "SG 1st derivative":
                params['deriv'] = 1
            elif algorithm_name == "SG 2nd derivative":
                params['deriv'] = 2
        
        return params

    # ================= PLOT FACTORY =================
    def _create_plot(self, title, y_label, x_label):
        plot = pg.PlotWidget(title=title)
        plot.setLabel("left", y_label)
        plot.setLabel("bottom", x_label)
        plot.showGrid(x=True, y=True)
        plot.setBackground("w")
        # Enable antialiasing for smooth lines
        plot.setAntialiasing(True)
        return plot
    
    def on_intercept_algo_activated(self, index):
        """Handle interception algorithm dropdown selection (fires on every click)"""
        text = self.intercept_algo.itemText(index)
        if text == "Manual Selection":
            self.show_spectra_cropping_dialog()
    
    def show_spectra_cropping_dialog(self):
        """Show the Spectra Cropping dialog"""
        dialog = SpectraCroppingDialog(self)
        if dialog.exec():
            # Clear preprocessing state when data changes due to cropping
            self.original_spectra = None
            self.processed_spectra = None
            self.applied_algorithms = []
            
            # Reload data after cropping
            self.load_cropped_data()
    
    def on_operation_clicked(self):
        """Apply selected preprocessing algorithm to ORIGINAL cropped data (resets chain)"""
        if not self.current_data:
            QMessageBox.warning(
                self,
                "No Data",
                "No data loaded. Please run data selection first!"
            )
            return
        
        algorithm = self.pretreat_combo.currentText()
        
        # Get custom parameters from UI
        custom_params = self._get_algorithm_parameters(algorithm)
        
        try:
            # Apply preprocessing to ORIGINAL cropped data
            original_spectra, processed_spectra, message = PreprocessingService.apply_preprocessing(
                self.current_data, algorithm, custom_params
            )
            
            if original_spectra is None or processed_spectra is None:
                QMessageBox.warning(self, "Processing Failed", message)
                return
            
            # Store results - original stays as baseline, processed is the new result
            if self.original_spectra is None:
                self.original_spectra = original_spectra
            
            self.processed_spectra = processed_spectra
            
            # Reset algorithm chain and start fresh
            self.applied_algorithms = [algorithm]
            
            # Extract wavelengths
            samples = self.current_data.get('samples', [])
            if samples and samples[0].get('wavelengths'):
                self.wavelengths = np.array(samples[0]['wavelengths'])
            
            # Update plots
            self._plot_spectra(self.original_spectra, self.original_plot, "original spectrogram")
            self._plot_spectra(self.processed_spectra, self.treated_plot, 
                             f"spectrum after {' → '.join(self.applied_algorithms)}")
            
            # Calculate and plot correlation coefficient
            correlations = PreprocessingService.calculate_correlation_coefficient(self.processed_spectra)
            self._plot_line(self.wavelengths, correlations, self.corr_plot, 
                           "correlation coefficient diagram", color='b')
            
            # Calculate and plot standard deviation
            std_dev = PreprocessingService.calculate_standard_deviation(self.processed_spectra)
            self._plot_line(self.wavelengths, std_dev, self.std_plot,
                           "standard deviation diagram", color='r')
            
            print(f"Applied {algorithm} to original cropped data")
            print(f"Algorithm chain: {' → '.join(self.applied_algorithms)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply preprocessing: {str(e)}")
            print(f"Error in preprocessing: {e}")
            import traceback
            traceback.print_exc()
    
    def on_operation_combination_clicked(self):
        """Apply selected preprocessing algorithm to PREVIOUSLY PROCESSED data (chain algorithms)"""
        if self.processed_spectra is None:
            QMessageBox.warning(
                self,
                "No Processed Data",
                "No processed data available. Please click 'operation' first!"
            )
            return
        
        algorithm = self.pretreat_combo.currentText()
        
        # Get custom parameters from UI
        custom_params = self._get_algorithm_parameters(algorithm)
        
        try:
            # Create temporary data dict with processed spectra
            temp_data = {
                'samples': [],
                'metadata': self.current_data.get('metadata', {})
            }
            
            # Convert processed spectra back to sample format
            for i in range(self.processed_spectra.shape[0]):
                temp_data['samples'].append({
                    'wavelengths': self.wavelengths.tolist(),
                    'absorbances': self.processed_spectra[i].tolist()
                })
            
            # Apply preprocessing to PROCESSED data (chaining)
            _, new_processed_spectra, message = PreprocessingService.apply_preprocessing(
                temp_data, algorithm, custom_params
            )
            
            if new_processed_spectra is None:
                QMessageBox.warning(self, "Processing Failed", message)
                return
            
            # Update processed spectra with new result
            self.processed_spectra = new_processed_spectra
            
            # Add algorithm to chain
            self.applied_algorithms.append(algorithm)
            
            # Update plots
            self._plot_spectra(self.original_spectra, self.original_plot, "original spectrogram")
            self._plot_spectra(self.processed_spectra, self.treated_plot, 
                             f"spectrum after {' → '.join(self.applied_algorithms)}")
            
            # Calculate and plot correlation coefficient
            correlations = PreprocessingService.calculate_correlation_coefficient(self.processed_spectra)
            self._plot_line(self.wavelengths, correlations, self.corr_plot, 
                           "correlation coefficient diagram", color='b')
            
            # Calculate and plot standard deviation
            std_dev = PreprocessingService.calculate_standard_deviation(self.processed_spectra)
            self._plot_line(self.wavelengths, std_dev, self.std_plot,
                           "standard deviation diagram", color='r')
            
            print(f"Applied {algorithm} to previously processed data")
            print(f"Algorithm chain: {' → '.join(self.applied_algorithms)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply combination: {str(e)}")
            print(f"Error in operation combination: {e}")
            import traceback
            traceback.print_exc()
    
    def on_reset_clicked(self):
        """Reset preprocessing algorithms only (keep current cropping)"""
        if self.original_spectra is not None:
            # Reset to the original cropped data (before preprocessing)
            self.processed_spectra = None
            self.applied_algorithms = []
            
            # Re-display the original spectra and clear processed plot
            self._plot_spectra(self.original_spectra, self.original_plot, "original spectrogram")
            self.treated_plot.clear()
            self.treated_plot.setTitle("spectrum after treatment")
            self.corr_plot.clear()
            self.corr_plot.setTitle("correlation coefficient diagram")
            self.std_plot.clear()
            self.std_plot.setTitle("standard deviation diagram")
            
            QMessageBox.information(self, "Reset", "Reset preprocessing algorithms.\nCropping is preserved.")
        else:
            # No preprocessing has been applied yet, reload from temp_data
            self.processed_spectra = None
            self.applied_algorithms = []
            self._load_initial_data()
            
            QMessageBox.information(self, "Reset", "Reloaded data from temp_data.")
    
    def _load_initial_data(self):
        """Load initial data from temp_data"""
        self.current_data = SpectralProcessingService.load_latest_data()
        if self.current_data:
            self.load_cropped_data()
        else:
            self._clear_plots()

    def _clear_plots(self):
        """Clear all plots and restore default titles."""
        self.original_plot.clear()
        self.original_plot.setTitle("original spectrogram")
        self.treated_plot.clear()
        self.treated_plot.setTitle("spectrum after treatment")
        self.corr_plot.clear()
        self.corr_plot.setTitle("correlation coefficient diagram")
        self.std_plot.clear()
        self.std_plot.setTitle("standard deviation diagram")

    def _build_loaded_title(self, samples):
        """Create an informative title for the loaded spectra plot."""
        sample_count = len(samples)
        metadata = self.current_data.get('metadata', {}) if self.current_data else {}
        data_type = str(metadata.get('data_type', '')).strip().lower()

        sample_names = [
            str(sample.get('sample_name', '')).strip()
            for sample in samples
            if str(sample.get('sample_name', '')).strip()
        ]
        unique_count = len(Counter(sample_names)) if sample_names else sample_count

        if data_type == 'raw' and unique_count != sample_count:
            return f"Loaded {sample_count} spectra ({unique_count} unique samples)"

        return f"Loaded {sample_count} spectra"

    def _extract_spectra_arrays(self, samples):
        """Convert sample dictionaries into numpy arrays used by preprocessing."""
        wavelengths = None
        absorbance_rows = []

        for sample in samples:
            sample_wavelengths = sample.get('wavelengths', [])
            sample_absorbances = sample.get('absorbances', [])

            if not sample_wavelengths or not sample_absorbances:
                continue

            if wavelengths is None:
                wavelengths = np.array(sample_wavelengths, dtype=float)

            absorbance_rows.append(np.array(sample_absorbances, dtype=float))

        if wavelengths is None or not absorbance_rows:
            return None, None

        return wavelengths, np.vstack(absorbance_rows)
    
    def _plot_spectra(self, spectra: np.ndarray, plot_widget, title: str):
        """Plot multiple spectra"""
        plot_widget.clear()
        
        import random
        random.seed(42)
        
        for i in range(spectra.shape[0]):
            color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
            if self.wavelengths is not None:
                plot_widget.plot(
                    self.wavelengths, 
                    spectra[i], 
                    pen=pg.mkPen(color=color, width=1),
                    antialias=True,
                    connect='all'
                )
        
        plot_widget.setTitle(f"{title} ({spectra.shape[0]} spectra)")
    
    def _plot_line(self, x: np.ndarray, y: np.ndarray, plot_widget, title: str, color='b'):
        """Plot a single line"""
        plot_widget.clear()
        plot_widget.plot(
            x, y, 
            pen=pg.mkPen(color=color, width=1),
            antialias=True,
            connect='all'
        )
        plot_widget.setTitle(title)
    
    def load_cropped_data(self):
        """Load and display cropped data in plots"""
        try:
            data = self.current_data or SpectralProcessingService.load_latest_data()
            self.current_data = data

            if not data:
                self.original_spectra = None
                self.processed_spectra = None
                self.wavelengths = None
                self._clear_plots()
                return
            
            samples = data.get('samples', [])
            wavelengths, original_spectra = self._extract_spectra_arrays(samples)

            self.original_spectra = original_spectra
            self.processed_spectra = None
            self.wavelengths = wavelengths

            self.original_plot.clear()
            
            import random
            random.seed(42)
            
            for sample in samples:
                wavelengths = sample.get('wavelengths', [])
                absorbances = sample.get('absorbances', [])
                
                if wavelengths and absorbances:
                    color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
                    self.original_plot.plot(
                        wavelengths, absorbances, 
                        pen=pg.mkPen(color=color, width=1),
                        antialias=True,
                        connect='all'
                    )
            
            self.original_plot.setTitle(self._build_loaded_title(samples))
            self.treated_plot.clear()
            self.treated_plot.setTitle("spectrum after treatment")
            self.corr_plot.clear()
            self.corr_plot.setTitle("correlation coefficient diagram")
            self.std_plot.clear()
            self.std_plot.setTitle("standard deviation diagram")
            
        except Exception as e:
            print(f"Error loading cropped data: {e}")


class SpectraCroppingDialog(QDialog):
    """Dialog for manual spectra cropping"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spectra Cropping")
        self.setModal(True)
        self.setFixedSize(300, 180)
        self.loaded_data = None
        self.original_data = None
        self._load_data()
        self._build_ui()
    
    def _load_data(self):
        """Load data using service"""
        self.loaded_data = SpectralProcessingService.load_latest_data()
        if self.loaded_data:
            # Create deep copy for original data
            import json
            self.original_data = json.loads(json.dumps(self.loaded_data))
            
            # Get current wavelength range
            self.data_min_wavelength, self.data_max_wavelength = \
                SpectralProcessingService.get_wavelength_range(self.loaded_data)
            
            # Check if data has been cropped before and has original range stored
            metadata = self.loaded_data.get('metadata', {})
            original_range = metadata.get('original_wavelength_range')
            
            if original_range:
                # Use the stored original range (from before any cropping)
                self.original_min_wavelength = original_range['min']
                self.original_max_wavelength = original_range['max']
                print(f"Using stored original range: {self.original_min_wavelength} - {self.original_max_wavelength} nm")
            else:
                # Check if data was already cropped in a previous session
                already_cropped = metadata.get('cropped', False)
                
                if already_cropped:
                    # Data was cropped before but doesn't have original range stored
                    # Use standard NIR range as default
                    print("Warning: Data was previously cropped but original range not stored. Using 900-1700 nm as default.")
                    self.original_min_wavelength = 900.0
                    self.original_max_wavelength = 1700.0
                else:
                    # Fresh data, use current range as original
                    self.original_min_wavelength = self.data_min_wavelength
                    self.original_max_wavelength = self.data_max_wavelength
            
            print(f"Current data wavelength range: {self.data_min_wavelength} - {self.data_max_wavelength} nm")
        else:
            self.data_min_wavelength = 0.0
            self.data_max_wavelength = 10000.0
            self.original_min_wavelength = 900.0
            self.original_max_wavelength = 1700.0
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Spectra Cropping")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 10px;")
        layout.addWidget(title_label)
        
        # Wavelength inputs
        wavelength_layout = QGridLayout()
        
        # Start Wavelength
        start_label = QLabel("Start Wavelength:")
        self.start_wavelength = QDoubleSpinBox()
        self.start_wavelength.setRange(0, 100000)
        self.start_wavelength.setValue(self.data_min_wavelength if hasattr(self, 'data_min_wavelength') else 0.00)
        self.start_wavelength.setDecimals(2)
        self.start_wavelength.setSuffix(" nm")
        self.start_wavelength.setMinimumWidth(150)
        
        wavelength_layout.addWidget(start_label, 0, 0)
        wavelength_layout.addWidget(self.start_wavelength, 0, 1)
        
        # End Wavelength
        end_label = QLabel("End Wavelength:")
        self.end_wavelength = QDoubleSpinBox()
        self.end_wavelength.setRange(0, 100000)
        self.end_wavelength.setValue(self.data_max_wavelength if hasattr(self, 'data_max_wavelength') else 10000.00)
        self.end_wavelength.setDecimals(2)
        self.end_wavelength.setSuffix(" nm")
        self.end_wavelength.setMinimumWidth(150)
        
        wavelength_layout.addWidget(end_label, 1, 0)
        wavelength_layout.addWidget(self.end_wavelength, 1, 1)
        
        layout.addLayout(wavelength_layout)
        
        layout.addSpacing(10)
        
        # Buttons
        self.apply_crop_btn = QPushButton("Apply Crop")
        self.apply_crop_btn.clicked.connect(self.apply_crop)
        layout.addWidget(self.apply_crop_btn)
        
        self.reset_btn = QPushButton("Reset to Original")
        self.reset_btn.clicked.connect(self.reset_to_original)
        layout.addWidget(self.reset_btn)
    
    def apply_crop(self):
        """Apply the wavelength cropping"""
        if not self.loaded_data:
            QMessageBox.warning(
                self,
                "No Data",
                "No data loaded from temp_data. Please run data selection first!"
            )
            return
        
        crop_start = self.start_wavelength.value()
        crop_end = self.end_wavelength.value()
        
        # Use service to crop data
        cropped_data, message = SpectralProcessingService.crop_spectral_data(
            self.loaded_data, crop_start, crop_end
        )
        
        if cropped_data is None:
            # Cropping failed, show error message
            QMessageBox.warning(self, "Crop Failed", message)
            return
        
        # Save cropped data
        saved_path = SpectralProcessingService.save_cropped_data(cropped_data)
        
        if saved_path:
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save cropped data!")
    
    def reset_to_original(self):
        """Reset to original wavelength range and reload uncropped data"""
        # Try to load the original uncropped data
        original_data = SpectralProcessingService.load_original_uncropped_data()
        
        if original_data:
            # Save the original data to temp_data so it becomes the latest file
            saved_path = SpectralProcessingService.save_original_data(original_data)
            
            if saved_path:
                print(f"Restored original uncropped data to: {saved_path}")
                
                # Update dialog's internal data
                self.loaded_data = original_data
                import json
                self.original_data = json.loads(json.dumps(original_data))
                
                # Get the wavelength range from original data
                self.data_min_wavelength, self.data_max_wavelength = \
                    SpectralProcessingService.get_wavelength_range(original_data)
                
                # Reset spinboxes
                self.start_wavelength.setValue(self.data_min_wavelength)
                self.end_wavelength.setValue(self.data_max_wavelength)
                
                # Close dialog and signal parent to reload
                QMessageBox.information(
                    self,
                    "Reset Complete",
                    f"Reset to original uncropped data:\n"
                    f"{self.data_min_wavelength:.2f} - {self.data_max_wavelength:.2f} nm\n\n"
                    f"Graph will refresh automatically."
                )
                self.accept()  # Close dialog with success
            else:
                QMessageBox.critical(self, "Error", "Failed to save original data!")
        else:
            # Fallback: just reset the spinboxes to default range
            self.start_wavelength.setValue(self.original_min_wavelength)
            self.end_wavelength.setValue(self.original_max_wavelength)
            
            print(f"Could not find original uncropped data. Reset spinboxes to: {self.original_min_wavelength}-{self.original_max_wavelength} nm")
            QMessageBox.warning(
                self,
                "Reset",
                f"Original uncropped data not found.\n\n"
                f"Reset spinboxes to: {self.original_min_wavelength:.2f} - {self.original_max_wavelength:.2f} nm\n"
                f"Note: You cannot crop beyond the current data range."
            )


