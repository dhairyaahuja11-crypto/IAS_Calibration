from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
import numpy as np

# Import calibration sub-tabs
from ui.calibration.data_selection import DataSelectionUI
from ui.calibration.pre_treatment import PreTreatmentUI
from ui.calibration.dimension_reduction import DimensionReductionUI
from ui.calibration.analysis_measure import AnalysisMeasureUI
from services.spectral_processing_service import SpectralProcessingService


class CalibrationMainUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.setObjectName("calibrationMainRoot")
        self.setStyleSheet("""
            QWidget#calibrationMainRoot {
                background-color: #f6f8fb;
            }
            QTabWidget::pane {
                border: 1px solid #d8e1eb;
                background: #ffffff;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background: #eef3f9;
                border: 1px solid #d8e1eb;
                border-bottom: none;
                padding: 7px 12px;
                min-width: 110px;
                color: #1f2937;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                font-weight: 600;
            }
            QTabBar::tab:hover {
                background: #f2f6ff;
            }
        """)

        # Sub-tabs inside Calibration
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Add sub-tabs (order matters) - store references
        self.data_selection_tab = DataSelectionUI()
        self.pre_treatment_tab = PreTreatmentUI()
        self.dimension_reduction_tab = DimensionReductionUI()
        self.analysis_measure_tab = AnalysisMeasureUI()
        
        self.tabs.addTab(self.data_selection_tab, "data selection")
        self.tabs.addTab(self.pre_treatment_tab, "pre-treatment")
        self.tabs.addTab(self.dimension_reduction_tab, "dimension reduction analysis")
        self.tabs.addTab(self.analysis_measure_tab, "analysis and measure")
        
        # Connect tab changes to pass data between tabs
        self.tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tabs)
    
    def _on_tab_changed(self, index):
        """Handle data passing when switching tabs"""
        tab_name = self.tabs.tabText(index).lower()
        
        if tab_name == "pre-treatment":
            self._sync_pre_treatment_project_data()
        elif tab_name == "dimension reduction analysis":
            self._pass_data_to_dimension_reduction()
        elif tab_name == "analysis and measure":
            self._sync_pre_treatment_project_data()
            self.analysis_measure_tab.refresh_data()
            self._pass_data_to_analysis_measure()

    def _sync_pre_treatment_project_data(self):
        """Reload pre-treatment data only when the selected project changed."""
        selected_project = str(getattr(self.data_selection_tab, 'current_project_name', '') or '').strip()
        current_project = ""
        current_timestamp = ""
        current_data_type = ""
        if getattr(self.pre_treatment_tab, 'current_data', None):
            current_metadata = self.pre_treatment_tab.current_data.get('metadata', {})
            current_project = str(current_metadata.get('project_name', '')).strip()
            current_timestamp = str(current_metadata.get('timestamp', '')).strip()
            current_data_type = str(current_metadata.get('data_type', '')).strip().lower()

        if not selected_project:
            return

        latest_project_data = SpectralProcessingService.load_latest_data(project_name=selected_project)
        latest_metadata = (latest_project_data or {}).get('metadata', {})
        latest_timestamp = str(latest_metadata.get('timestamp', '')).strip()
        latest_data_type = str(latest_metadata.get('data_type', '')).strip().lower()

        should_reload = (
            selected_project != current_project
            or (latest_timestamp and latest_timestamp != current_timestamp)
            or (latest_data_type and latest_data_type != current_data_type)
        )

        if should_reload:
            self.pre_treatment_tab.original_spectra = None
            self.pre_treatment_tab.processed_spectra = None
            self.pre_treatment_tab.validation_original_spectra = None
            self.pre_treatment_tab.processed_validation_spectra = None
            self.pre_treatment_tab.applied_algorithms = []
            self.pre_treatment_tab.applied_algorithm_steps = []
            self.pre_treatment_tab.intercept_metadata = {}
            self.pre_treatment_tab.load_cropped_data(force_latest=True, project_name=selected_project)
    
    def _pass_data_to_dimension_reduction(self):
        """Pass preprocessed data from pre-treatment to dimension reduction"""
        if hasattr(self.pre_treatment_tab, 'processed_spectra') and \
           self.pre_treatment_tab.processed_spectra is not None:
            
            # Get preprocessed spectra
            spectra = self.pre_treatment_tab.processed_spectra
            wavelengths = self.pre_treatment_tab.wavelengths
            target_values, sample_metadata = self._extract_targets_and_metadata(
                getattr(self.pre_treatment_tab, 'calibration_data', None),
                spectra
            )
            validation_spectra = getattr(self.pre_treatment_tab, 'processed_validation_spectra', None)
            validation_targets, validation_metadata = self._extract_targets_and_metadata(
                getattr(self.pre_treatment_tab, 'validation_data', None),
                validation_spectra
            )
            
            # Load data into dimension reduction tab
            self.dimension_reduction_tab.load_preprocessed_data(
                spectra, 
                wavelengths, 
                target_values,
                sample_metadata,
                validation_spectra=validation_spectra,
                validation_targets=validation_targets,
                validation_metadata=validation_metadata
            )

    def _pass_data_to_analysis_measure(self):
        """Provide calibration/validation context to the analysis tab."""
        calibration_spectra = getattr(self.pre_treatment_tab, 'processed_spectra', None)
        validation_spectra = getattr(self.pre_treatment_tab, 'processed_validation_spectra', None)

        if calibration_spectra is None:
            calibration_spectra = getattr(self.pre_treatment_tab, 'original_spectra', None)
        if validation_spectra is None:
            validation_spectra = getattr(self.pre_treatment_tab, 'validation_original_spectra', None)

        calibration_targets, calibration_metadata = self._extract_targets_and_metadata(
            getattr(self.pre_treatment_tab, 'calibration_data', None),
            calibration_spectra
        )
        validation_targets, validation_metadata = self._extract_targets_and_metadata(
            getattr(self.pre_treatment_tab, 'validation_data', None),
            validation_spectra
        )

        calibration_spectra, calibration_targets, calibration_metadata, validation_spectra, validation_targets, validation_metadata = (
            self._apply_dimension_reduction_split(
                calibration_spectra,
                calibration_targets,
                calibration_metadata,
                validation_spectra,
                validation_targets,
                validation_metadata
            )
        )

        self.analysis_measure_tab.load_analysis_context({
            'project_id': getattr(self.data_selection_tab, 'current_project_id', None),
            'project_name': getattr(self.data_selection_tab, 'current_project_name', None),
            'instrument': getattr(self.data_selection_tab, 'current_project_instrument', None),
            'measurement_index': self._read_temp_metadata('measurement_index'),
            'temp_metadata': self._read_temp_metadata(),
            'intercept_metadata': getattr(self.pre_treatment_tab, 'intercept_metadata', {}),
            'pretreatment_steps': list(getattr(self.pre_treatment_tab, 'applied_algorithm_steps', [])),
            'dimension_algorithm': getattr(self.dimension_reduction_tab.algorithm_combo, 'currentText', lambda: '')(),
            'wavelengths': getattr(self.pre_treatment_tab, 'wavelengths', None),
            'calibration_spectra': calibration_spectra,
            'calibration_targets': calibration_targets,
            'calibration_metadata': calibration_metadata,
            'validation_spectra': validation_spectra,
            'validation_targets': validation_targets,
            'validation_metadata': validation_metadata,
            'dimension_results': getattr(self.dimension_reduction_tab, 'current_results', None)
        })

    def _apply_dimension_reduction_split(
        self,
        calibration_spectra,
        calibration_targets,
        calibration_metadata,
        validation_spectra,
        validation_targets,
        validation_metadata
    ):
        """Honor validation/excluded selections made in dimension reduction."""
        dim_tab = getattr(self, 'dimension_reduction_tab', None)
        if calibration_spectra is None or calibration_targets is None or dim_tab is None:
            return (
                calibration_spectra,
                calibration_targets,
                calibration_metadata,
                validation_spectra,
                validation_targets,
                validation_metadata
            )

        row_count = calibration_spectra.shape[0]
        excluded_indices = {
            idx for idx in getattr(dim_tab, 'excluded_indices', [])
            if 0 <= idx < row_count
        }
        moved_validation_indices = [
            idx for idx in getattr(dim_tab, 'validation_indices', [])
            if 0 <= idx < row_count and idx not in excluded_indices
        ]

        if not excluded_indices and not moved_validation_indices:
            return (
                calibration_spectra,
                calibration_targets,
                calibration_metadata,
                validation_spectra,
                validation_targets,
                validation_metadata
            )

        calibration_metadata = list(calibration_metadata or [])
        validation_metadata = list(validation_metadata or [])

        keep_indices = [
            idx for idx in range(row_count)
            if idx not in excluded_indices and idx not in moved_validation_indices
        ]

        moved_validation_spectra = calibration_spectra[moved_validation_indices] if moved_validation_indices else None
        moved_validation_targets = calibration_targets[moved_validation_indices] if moved_validation_indices else None
        moved_validation_metadata = []
        for idx in moved_validation_indices:
            meta = dict(calibration_metadata[idx]) if idx < len(calibration_metadata) else {}
            meta['sample_type'] = 'validation'
            moved_validation_metadata.append(meta)

        filtered_calibration_spectra = calibration_spectra[keep_indices]
        filtered_calibration_targets = calibration_targets[keep_indices]
        filtered_calibration_metadata = [
            calibration_metadata[idx]
            for idx in keep_indices
            if idx < len(calibration_metadata)
        ]

        merged_validation_spectra = self._concat_optional_arrays(validation_spectra, moved_validation_spectra)
        merged_validation_targets = self._concat_optional_arrays(validation_targets, moved_validation_targets)
        merged_validation_metadata = validation_metadata + moved_validation_metadata

        return (
            filtered_calibration_spectra,
            filtered_calibration_targets,
            filtered_calibration_metadata,
            merged_validation_spectra,
            merged_validation_targets,
            merged_validation_metadata
        )

    def _concat_optional_arrays(self, left, right):
        """Combine two aligned numpy arrays when either side may be empty."""
        if left is None:
            return right
        if right is None:
            return left
        if len(left) == 0:
            return right
        if len(right) == 0:
            return left
        return np.concatenate([left, right], axis=0)

    def _extract_targets_and_metadata(self, data_source, spectra):
        """Extract aligned targets/metadata for the provided sample list."""
        if data_source is None or spectra is None:
            return None, []

        metadata = data_source.get('metadata', {})
        measurement_index = metadata.get('measurement_index', 'Property')
        samples = data_source.get('samples', [])
        if len(samples) != spectra.shape[0]:
            raise ValueError(
                "Sample metadata count does not match spectra count. "
                f"Samples: {len(samples)}, spectra rows: {spectra.shape[0]}."
            )

        target_values = []
        sample_metadata = []
        for sample in samples:
            prop_val = sample.get('property_value', None)
            if prop_val is not None and str(prop_val).strip() != '':
                try:
                    target_values.append(float(prop_val))
                except (ValueError, TypeError):
                    target_values.append(np.nan)
            else:
                target_values.append(np.nan)

            sample_metadata.append({
                'sample_name': sample.get('sample_name', 'Unknown'),
                'sample_id': sample.get('sample_id', ''),
                'instrument': sample.get('instrument', ''),
                'serial_number': sample.get('serial_number', ''),
                'create_time': sample.get('create_time', ''),
                'user_id': sample.get('user_id', ''),
                'wavelength_points': sample.get('wavelength_points', spectra.shape[1] if spectra is not None else ''),
                'property_value': prop_val,
                'property_name': measurement_index,
                'sample_type': sample.get('sample_type', 'calibration')
            })

        target_values = np.array(target_values, dtype=float)
        valid_mask = np.isfinite(target_values)
        if np.all(valid_mask):
            return target_values, sample_metadata

        filtered_spectra = spectra[valid_mask]
        if len(filtered_spectra) != np.count_nonzero(valid_mask):
            raise ValueError("Failed to align finite targets with spectra rows.")
        return target_values[valid_mask], [
            meta for meta, keep in zip(sample_metadata, valid_mask) if keep
        ]

    def _read_temp_metadata(self, key=None):
        """Read the latest temp_data metadata for model persistence details."""
        project_name = str(getattr(self.data_selection_tab, 'current_project_name', '') or '').strip() or None
        data = SpectralProcessingService.load_latest_data(project_name=project_name) or {}
        metadata = data.get('metadata', {})
        if key is None:
            return metadata
        return metadata.get(key)
            
    def refresh_data(self):
        """Refresh project/instrument lists when tab becomes active"""
        self.data_selection_tab.refresh_dropdowns()
        self.data_selection_tab.refresh_current_project()
        self.analysis_measure_tab.refresh_data()
