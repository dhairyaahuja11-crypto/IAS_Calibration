from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
import numpy as np

# Import calibration sub-tabs
from ui.calibration.data_selection import DataSelectionUI
from ui.calibration.pre_treatment import PreTreatmentUI
from ui.calibration.dimension_reduction import DimensionReductionUI
from ui.calibration.analysis_measure import AnalysisMeasureUI


class CalibrationMainUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Sub-tabs inside Calibration
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Add sub-tabs (order matters) - store references
        self.data_selection_tab = DataSelectionUI()
        self.pre_treatment_tab = PreTreatmentUI()
        self.dimension_reduction_tab = DimensionReductionUI()
        
        self.tabs.addTab(self.data_selection_tab, "data selection")
        self.tabs.addTab(self.pre_treatment_tab, "pre-treatment")
        self.tabs.addTab(self.dimension_reduction_tab, "dimension reduction analysis")
        self.tabs.addTab(AnalysisMeasureUI(), "analysis and measure")
        
        # Connect tab changes to pass data between tabs
        self.tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tabs)
    
    def _on_tab_changed(self, index):
        """Handle data passing when switching tabs"""
        tab_name = self.tabs.tabText(index).lower()
        
        # When switching to dimension reduction, pass preprocessed data
        if tab_name == "dimension reduction analysis":
            self._pass_data_to_dimension_reduction()
    
    def _pass_data_to_dimension_reduction(self):
        """Pass preprocessed data from pre-treatment to dimension reduction"""
        if hasattr(self.pre_treatment_tab, 'processed_spectra') and \
           self.pre_treatment_tab.processed_spectra is not None:
            
            # Get preprocessed spectra
            spectra = self.pre_treatment_tab.processed_spectra
            wavelengths = self.pre_treatment_tab.wavelengths
            
            # Try to get target values from data (if available)
            target_values = None
            sample_names = []
            sample_metadata = []
            if hasattr(self.pre_treatment_tab, 'current_data') and \
               self.pre_treatment_tab.current_data is not None:
                # Get measurement index (substance name) from metadata
                metadata = self.pre_treatment_tab.current_data.get('metadata', {})
                measurement_index = metadata.get('measurement_index', 'Property')
                
                samples = self.pre_treatment_tab.current_data.get('samples', [])
                if samples:
                    # Extract property values, sample names, and metadata (for PLSR)
                    target_values = []
                    for sample in samples:
                        # Get property value
                        prop_val = sample.get('property_value', None)
                        if prop_val is not None and prop_val != '':
                            try:
                                target_values.append(float(prop_val))
                            except (ValueError, TypeError):
                                target_values.append(0.0)
                        else:
                            target_values.append(0.0)
                        
                        # Get sample name
                        sample_names.append(sample.get('sample_name', 'Unknown'))
                        
                        # Store metadata for each sample
                        sample_metadata.append({
                            'sample_name': sample.get('sample_name', 'Unknown'),
                            'sample_id': sample.get('sample_id', ''),
                            'property_value': prop_val,
                            'property_name': measurement_index  # Substance/property being measured
                        })
                    
                    if len(target_values) > 0:
                        target_values = np.array(target_values)
                    else:
                        target_values = None
            
            # Load data into dimension reduction tab
            self.dimension_reduction_tab.load_preprocessed_data(
                spectra, 
                wavelengths, 
                target_values,
                sample_metadata
            )
            
            print(f"Passed preprocessed data to dimension reduction")
    
    def refresh_data(self):
        """Refresh project/instrument lists when tab becomes active"""
        self.data_selection_tab.refresh_dropdowns()
