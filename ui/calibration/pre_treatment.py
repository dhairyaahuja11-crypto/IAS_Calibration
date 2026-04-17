from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QDialog, QDoubleSpinBox, QMessageBox, QSpinBox, QSizePolicy
)
from PyQt6.QtCore import Qt
import numpy as np
from collections import Counter
from services.spectral_processing_service import SpectralProcessingService
from services.preprocessing_service import PreprocessingService
from ui.plot_widget import PlotWidget


class PreTreatmentUI(QWidget):
    MAX_PLOT_SPECTRA = 120

    def __init__(self):
        super().__init__()
        self.current_data = None
        self.calibration_data = None
        self.validation_data = None
        self.original_spectra = None  # Original cropped data (never changes)
        self.processed_spectra = None  # Last processed result
        self.validation_original_spectra = None
        self.processed_validation_spectra = None
        self.wavelengths = None
        self.applied_algorithms = []  # Track chain of applied algorithms
        self.applied_algorithm_steps = []
        self.intercept_metadata = {}
        self._build_ui()
        self._connect_signals()
        self._load_initial_data()
    
    def _connect_signals(self):
        """Connect UI signals"""
        self.intercept_algo.activated.connect(self.on_intercept_algo_activated)
        self.intercept_btn.clicked.connect(self.on_intercept_clicked)
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

    def _format_algorithm_step(self, algorithm_name, params):
        """Create a readable preprocessing label including active parameters."""
        if not params:
            return algorithm_name

        ordered_keys = ["window_size", "window_length", "polyorder", "deriv"]
        parts = []
        for key in ordered_keys:
            if key in params:
                parts.append(f"{key}={params[key]}")
        for key, value in params.items():
            if key not in ordered_keys:
                parts.append(f"{key}={value}")

        return f"{algorithm_name} ({', '.join(parts)})" if parts else algorithm_name

    # ================= PLOT FACTORY =================
    def _create_plot(self, title, y_label, x_label):
        plot = PlotWidget(show_toolbar=False)
        plot.reset_axes(title=title, xlabel=x_label, ylabel=y_label)
        plot.draw()
        return plot
    
    def on_intercept_algo_activated(self, index):
        """Handle interception algorithm dropdown selection (fires on every click)"""
        _ = self.intercept_algo.itemText(index)

    def on_intercept_clicked(self):
        """Apply the selected interception algorithm and reload the latest cropped data."""
        if not self.current_data:
            QMessageBox.warning(
                self,
                "No Data",
                "No data loaded. Please run data selection first!"
            )
            return

        algorithm_name = self.intercept_algo.currentText()
        if algorithm_name == "Manual Selection":
            self.show_spectra_cropping_dialog()
            return

        try:
            crop_start, crop_end, detail = self._determine_intercept_range(algorithm_name)
            cropped_data, message = SpectralProcessingService.crop_spectral_data(
                self.current_data,
                crop_start,
                crop_end
            )

            if cropped_data is None:
                QMessageBox.warning(self, "Intercept Failed", message)
                return

            saved_path = SpectralProcessingService.save_cropped_data(cropped_data)
            if not saved_path:
                QMessageBox.critical(self, "Intercept Failed", "Failed to save intercepted data.")
                return

            self.intercept_metadata = {
                "algorithm": algorithm_name,
                "range": f"{crop_start:.2f}-{crop_end:.2f} nm",
                "detail": detail
            }
            self.applied_algorithms = []
            self.applied_algorithm_steps = []
            self.load_cropped_data(force_latest=True)

            QMessageBox.information(
                self,
                "Intercept Applied",
                f"{detail}\n\n{message}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Intercept Failed", f"Failed to apply {algorithm_name} interception:\n{e}")

    def _determine_intercept_range(self, algorithm_name):
        """Estimate a wavelength band for the selected interception algorithm."""
        samples = self.current_data.get("samples", []) if self.current_data else []
        wavelengths, spectra = self._extract_spectra_arrays(samples)
        if wavelengths is None or spectra is None or spectra.shape[1] < 5:
            raise ValueError("Not enough spectral data is available to determine an interception range.")

        score = self._build_intercept_score(samples, spectra)
        point_count = len(score)

        if algorithm_name == "LPG":
            threshold = float(np.quantile(score, 0.65))
            segment = self._longest_true_segment(score >= threshold)
            minimum_width = max(25, point_count // 12)
            segment = self._expand_segment(segment, point_count, minimum_width)
            detail = "LPG selected the longest informative wavelength band."
        else:
            peak_idx = int(np.argmax(score))
            threshold = float(score[peak_idx]) * 0.72
            start_idx = peak_idx
            end_idx = peak_idx

            while start_idx > 0 and score[start_idx - 1] >= threshold:
                start_idx -= 1
            while end_idx < point_count - 1 and score[end_idx + 1] >= threshold:
                end_idx += 1

            minimum_width = max(21, point_count // 14)
            segment = self._expand_segment((start_idx, end_idx), point_count, minimum_width)
            detail = "SPG selected the strongest peak-centered wavelength band."

        start_idx, end_idx = segment
        return float(wavelengths[start_idx]), float(wavelengths[end_idx]), detail

    def _build_intercept_score(self, samples, spectra):
        """Blend spectral spread and property correlation into one importance score."""
        std_score = np.std(spectra, axis=0)
        std_score = std_score / (np.max(std_score) + 1e-12)

        targets = []
        for sample in samples:
            try:
                targets.append(float(sample.get("property_value")))
            except (TypeError, ValueError):
                targets.append(np.nan)

        targets = np.array(targets, dtype=float)
        corr_score = np.zeros(spectra.shape[1], dtype=float)
        finite_mask = np.isfinite(targets)
        if np.count_nonzero(finite_mask) >= 3 and len(np.unique(targets[finite_mask])) > 1:
            usable_spectra = spectra[finite_mask]
            usable_targets = targets[finite_mask]
            for col_idx in range(usable_spectra.shape[1]):
                corr = np.corrcoef(usable_spectra[:, col_idx], usable_targets)[0, 1]
                corr_score[col_idx] = 0.0 if np.isnan(corr) else abs(float(corr))
            corr_score = corr_score / (np.max(corr_score) + 1e-12)

        combined = (0.65 * corr_score) + (0.35 * std_score)
        return combined if np.any(combined) else std_score

    def _longest_true_segment(self, mask):
        """Return the longest contiguous True segment in a boolean mask."""
        best_start = 0
        best_end = len(mask) - 1
        current_start = None

        for idx, keep in enumerate(mask):
            if keep and current_start is None:
                current_start = idx
            if not keep and current_start is not None:
                if (idx - 1) - current_start > best_end - best_start:
                    best_start, best_end = current_start, idx - 1
                current_start = None

        if current_start is not None and (len(mask) - 1) - current_start > best_end - best_start:
            best_start, best_end = current_start, len(mask) - 1

        return best_start, best_end

    def _expand_segment(self, segment, point_count, minimum_width):
        """Expand the selected segment until it reaches a minimum width."""
        start_idx, end_idx = segment
        while (end_idx - start_idx + 1) < minimum_width:
            if start_idx > 0:
                start_idx -= 1
            if (end_idx - start_idx + 1) >= minimum_width:
                break
            if end_idx < point_count - 1:
                end_idx += 1
            if start_idx == 0 and end_idx == point_count - 1:
                break

        return start_idx, end_idx
    
    def show_spectra_cropping_dialog(self):
        """Show the Spectra Cropping dialog"""
        dialog = SpectraCroppingDialog(self)
        if dialog.exec():
            # Clear preprocessing state when data changes due to cropping
            self.original_spectra = None
            self.processed_spectra = None
            self.applied_algorithms = []
            self.applied_algorithm_steps = []
            
            # Reload data after cropping
            self.load_cropped_data(force_latest=True)
            crop_range = ""
            if self.current_data:
                crop_range = self.current_data.get("metadata", {}).get("crop_range", "")
            self.intercept_metadata = {
                "algorithm": "Manual Selection",
                "range": crop_range,
                "detail": "Manual wavelength interception was applied."
            }
    
    def on_operation_clicked(self):
        """Apply selected preprocessing algorithm to ORIGINAL cropped data (resets chain)"""
        if not self.calibration_data:
            QMessageBox.warning(
                self,
                "No Data",
                "No data loaded. Please run data selection first!"
            )
            return
        
        algorithm = self.pretreat_combo.currentText()
        
        # Get custom parameters from UI
        custom_params = self._get_algorithm_parameters(algorithm)
        algorithm_step = self._format_algorithm_step(algorithm, custom_params)
        
        try:
            # Apply preprocessing to calibration data only
            original_spectra, processed_spectra, message = PreprocessingService.apply_preprocessing(
                self.calibration_data, algorithm, custom_params
            )
            
            if original_spectra is None or processed_spectra is None:
                QMessageBox.warning(self, "Processing Failed", message)
                return
            
            # Store results - original stays as baseline, processed is the new result
            if self.original_spectra is None:
                self.original_spectra = original_spectra
            
            self.processed_spectra = processed_spectra

            # Apply the same preprocessing to validation samples when present
            self.validation_original_spectra = None
            self.processed_validation_spectra = None
            if self.validation_data and self.validation_data.get('samples'):
                val_original, val_processed, _ = PreprocessingService.apply_preprocessing(
                    self.validation_data, algorithm, custom_params
                )
                self.validation_original_spectra = val_original
                self.processed_validation_spectra = val_processed
            
            # Reset algorithm chain and start fresh
            self.applied_algorithms = [algorithm]
            self.applied_algorithm_steps = [algorithm_step]
            
            # Extract wavelengths
            samples = self.calibration_data.get('samples', [])
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
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply preprocessing: {str(e)}")
    
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
        algorithm_step = self._format_algorithm_step(algorithm, custom_params)
        
        try:
            # Create temporary data dict with processed spectra
            temp_data = {
                'samples': [],
                'metadata': self.calibration_data.get('metadata', {})
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

            if self.validation_data and self.validation_data.get('samples'):
                validation_temp_data = {
                    'samples': [],
                    'metadata': self.validation_data.get('metadata', {})
                }
                source_validation = self.processed_validation_spectra
                if source_validation is None:
                    source_validation = self.validation_original_spectra
                if source_validation is not None:
                    for i in range(source_validation.shape[0]):
                        validation_temp_data['samples'].append({
                            'wavelengths': self.wavelengths.tolist(),
                            'absorbances': source_validation[i].tolist()
                        })
                    _, new_processed_validation, _ = PreprocessingService.apply_preprocessing(
                        validation_temp_data, algorithm, custom_params
                    )
                    self.processed_validation_spectra = new_processed_validation
            
            # Add algorithm to chain
            self.applied_algorithms.append(algorithm)
            self.applied_algorithm_steps.append(algorithm_step)
            
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
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply combination: {str(e)}")
    
    def on_reset_clicked(self):
        """Reset preprocessing algorithms only (keep current cropping)"""
        if self.original_spectra is not None:
            # Reset to the original cropped data (before preprocessing)
            self.processed_spectra = None
            self.processed_validation_spectra = None
            self.applied_algorithms = []
            self.applied_algorithm_steps = []
            
            # Re-display the original spectra and clear processed plot
            self._plot_spectra(self.original_spectra, self.original_plot, "original spectrogram")
            self.treated_plot.clear()
            self.treated_plot.ax.set_title("spectrum after treatment")
            self.treated_plot.draw()
            self.corr_plot.clear()
            self.corr_plot.ax.set_title("correlation coefficient diagram")
            self.corr_plot.draw()
            self.std_plot.clear()
            self.std_plot.ax.set_title("standard deviation diagram")
            self.std_plot.draw()
            
            QMessageBox.information(self, "Reset", "Reset preprocessing algorithms.\nCropping is preserved.")
        else:
            # No preprocessing has been applied yet, reload from temp_data
            self.processed_spectra = None
            self.processed_validation_spectra = None
            self.applied_algorithms = []
            self.applied_algorithm_steps = []
            self._load_initial_data()
            
            QMessageBox.information(self, "Reset", "Reloaded data from temp_data.")
    
    def _load_initial_data(self, project_name=None):
        """Load initial data from temp_data"""
        self.current_data = SpectralProcessingService.load_latest_data(project_name=project_name)
        if self.current_data:
            self.load_cropped_data(force_latest=True, project_name=project_name)
        else:
            self._clear_plots()

    def _clear_plots(self):
        """Clear all plots and restore default titles."""
        self.original_plot.clear()
        self.original_plot.ax.set_title("original spectrogram")
        self.original_plot.draw()
        self.treated_plot.clear()
        self.treated_plot.ax.set_title("spectrum after treatment")
        self.treated_plot.draw()
        self.corr_plot.clear()
        self.corr_plot.ax.set_title("correlation coefficient diagram")
        self.corr_plot.draw()
        self.std_plot.clear()
        self.std_plot.ax.set_title("standard deviation diagram")
        self.std_plot.draw()

    def _build_subset_data(self, samples):
        """Clone the current dataset metadata with a provided sample list."""
        if not self.current_data:
            return None

        metadata = dict(self.current_data.get('metadata', {}))
        metadata['total_samples'] = len(samples)
        return {
            'metadata': metadata,
            'samples': list(samples)
        }

    def _split_samples_by_type(self, data):
        """Split loaded temp_data into calibration and validation subsets."""
        samples = data.get('samples', []) if data else []
        calibration_samples = []
        validation_samples = []

        for sample in samples:
            sample_type = str(sample.get('sample_type', '')).strip().lower()
            if sample_type == 'validation':
                validation_samples.append(sample)
            else:
                calibration_samples.append(sample)

        if not calibration_samples:
            calibration_samples = list(samples)
            validation_samples = []

        return calibration_samples, validation_samples

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
        if spectra is None or spectra.size == 0:
            plot_widget.ax.set_title(title)
            plot_widget.draw()
            return
        
        import random
        random.seed(42)

        row_indices = self._sample_indices_for_plot(spectra.shape[0], self.MAX_PLOT_SPECTRA)
        
        for i in row_indices:
            color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
            if self.wavelengths is not None:
                normalized = tuple(channel / 255 for channel in color)
                plot_widget.ax.plot(self.wavelengths, spectra[i], color=normalized, linewidth=1)
        if len(row_indices) < spectra.shape[0]:
            plot_widget.ax.set_title(f"{title} ({len(row_indices)} of {spectra.shape[0]} spectra)")
        else:
            plot_widget.ax.set_title(f"{title} ({spectra.shape[0]} spectra)")
        plot_widget.ax.set_xlabel("wavelength")
        plot_widget.ax.set_ylabel("absorbance(AU)")
        plot_widget.ax.grid(True, alpha=0.3)
        plot_widget.draw()

    def _sample_indices_for_plot(self, count, limit):
        """Reduce plotting load by sampling rows evenly."""
        if count <= limit:
            return list(range(count))
        if limit <= 1:
            return [0]

        last_index = count - 1
        indices = []
        for slot in range(limit):
            idx = round(slot * last_index / (limit - 1))
            if idx not in indices:
                indices.append(idx)
        return indices
    
    def _plot_line(self, x: np.ndarray, y: np.ndarray, plot_widget, title: str, color='b'):
        """Plot a single line"""
        plot_widget.clear()
        plot_widget.ax.plot(x, y, color=color, linewidth=1)
        plot_widget.ax.set_title(title)
        plot_widget.ax.grid(True, alpha=0.3)
        plot_widget.draw()
    
    def load_cropped_data(self, force_latest=False, project_name=None):
        """Load and display cropped data in plots"""
        try:
            data = SpectralProcessingService.load_latest_data(project_name=project_name) if force_latest else (
                self.current_data or SpectralProcessingService.load_latest_data(project_name=project_name)
            )
            self.current_data = data

            if not data:
                self.original_spectra = None
                self.processed_spectra = None
                self.validation_original_spectra = None
                self.processed_validation_spectra = None
                self.wavelengths = None
                self._clear_plots()
                return

            calibration_samples, validation_samples = self._split_samples_by_type(data)
            self.calibration_data = self._build_subset_data(calibration_samples)
            self.validation_data = self._build_subset_data(validation_samples)

            wavelengths, original_spectra = self._extract_spectra_arrays(calibration_samples)
            _, validation_original_spectra = self._extract_spectra_arrays(validation_samples)

            self.original_spectra = original_spectra
            self.processed_spectra = None
            self.validation_original_spectra = validation_original_spectra
            self.processed_validation_spectra = None
            self.wavelengths = wavelengths

            self.original_plot.clear()
            
            import random
            random.seed(42)
            
            sample_rows = self._sample_indices_for_plot(len(calibration_samples), self.MAX_PLOT_SPECTRA)
            for row_index in sample_rows:
                sample = calibration_samples[row_index]
                wavelengths = sample.get('wavelengths', [])
                absorbances = sample.get('absorbances', [])
                
                if wavelengths and absorbances:
                    color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
                    normalized = tuple(channel / 255 for channel in color)
                    self.original_plot.ax.plot(wavelengths, absorbances, color=normalized, linewidth=1)
            
            base_title = self._build_loaded_title(calibration_samples)
            if len(sample_rows) < len(calibration_samples):
                self.original_plot.ax.set_title(f"{base_title} (showing {len(sample_rows)})")
            else:
                self.original_plot.ax.set_title(base_title)
            self.original_plot.ax.set_xlabel("wavelength")
            self.original_plot.ax.set_ylabel("absorbance(AU)")
            self.original_plot.ax.grid(True, alpha=0.3)
            self.original_plot.draw()
            self.treated_plot.clear()
            self.treated_plot.ax.set_title("spectrum after treatment")
            self.treated_plot.draw()
            self.corr_plot.clear()
            self.corr_plot.ax.set_title("correlation coefficient diagram")
            self.corr_plot.draw()
            self.std_plot.clear()
            self.std_plot.ax.set_title("standard deviation diagram")
            self.std_plot.draw()
            
        except Exception:
            pass


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
            else:
                # Check if data was already cropped in a previous session
                already_cropped = metadata.get('cropped', False)
                
                if already_cropped:
                    # Data was cropped before but doesn't have original range stored
                    # Use standard NIR range as default
                    self.original_min_wavelength = 900.0
                    self.original_max_wavelength = 1700.0
                else:
                    # Fresh data, use current range as original
                    self.original_min_wavelength = self.data_min_wavelength
                    self.original_max_wavelength = self.data_max_wavelength
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
        project_name = ""
        if self.loaded_data:
            project_name = str(self.loaded_data.get('metadata', {}).get('project_name', '')).strip()
        original_data = SpectralProcessingService.load_original_uncropped_data(project_name=project_name or None)
        
        if original_data:
            # Save the original data to temp_data so it becomes the latest file
            saved_path = SpectralProcessingService.save_original_data(original_data)
            
            if saved_path:
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
            QMessageBox.warning(
                self,
                "Reset",
                f"Original uncropped data not found.\n\n"
                f"Reset spinboxes to: {self.original_min_wavelength:.2f} - {self.original_max_wavelength:.2f} nm\n"
                f"Note: You cannot crop beyond the current data range."
            )


