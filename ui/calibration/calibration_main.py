from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

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

        # Add sub-tabs (order matters)
        self.tabs.addTab(DataSelectionUI(), "data selection")
        self.tabs.addTab(PreTreatmentUI(), "pre-treatment")
        self.tabs.addTab(DimensionReductionUI(), "dimension reduction analysis")
        self.tabs.addTab(AnalysisMeasureUI(), "analysis and measure")

        layout.addWidget(self.tabs)
