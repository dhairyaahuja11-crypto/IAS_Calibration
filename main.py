import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget
)
from PyQt6.QtCore import Qt
from dotenv import load_dotenv

# Main tabs
from ui.data_management import DataManagementUI
from ui.sample_management import SampleManagementUI
from ui.project_management import ProjectManagementUI
from ui.calibration.calibration_main import CalibrationMainUI
from ui.model_management import ModelManagementUI
from ui.instrument_management import InstrumentManagementUI
from ui.scanning_management import ScanningManagementUI
from ui.measurement_demo import MeasurementDemoUI


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectral Analysis System")
        self.resize(1600, 900)

        self._build_ui()

    def _build_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Top-level tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(False)
        self.tabs.setTabsClosable(False)

        # ---- ADD TABS (ORDER MATTERS) ----
        self.data_management_tab = DataManagementUI()
        self.tabs.addTab(self.data_management_tab, "data management")
        self.sample_management_tab = SampleManagementUI()
        self.tabs.addTab(self.sample_management_tab, "sample management")
        self.project_management_tab = ProjectManagementUI()
        self.tabs.addTab(self.project_management_tab, "project management")
        self.calibration_tab = CalibrationMainUI()
        self.tabs.addTab(self.calibration_tab, "calibration")
        self.model_management_tab = ModelManagementUI()
        self.tabs.addTab(self.model_management_tab, "model management")
        self.instrument_management_tab = InstrumentManagementUI()
        self.tabs.addTab(self.instrument_management_tab, "instrument management")
        self.scanning_management_tab = ScanningManagementUI()
        self.tabs.addTab(self.scanning_management_tab, "scanning management")
        self.measurement_demo_tab = MeasurementDemoUI()
        self.tabs.addTab(self.measurement_demo_tab, "measurement(demo)")

        # Connect tab change signal for auto-refresh
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        # Connect project changes to calibration refresh
        self.project_management_tab.project_changed.connect(self.calibration_tab.refresh_data)

        main_layout.addWidget(self.tabs)
        self.setCentralWidget(central_widget)
    
    def _on_tab_changed(self, index):
        """Refresh data when switching tabs (only if data was previously loaded)"""
        current_tab = self.tabs.widget(index)
        
        try:
            if current_tab == self.sample_management_tab:
                # Only auto-refresh if inquiry has been run before
                if hasattr(self.sample_management_tab, '_inquiry_run') and self.sample_management_tab._inquiry_run:
                    self.sample_management_tab.on_inquiry_clicked(silent=True)
            elif current_tab == self.project_management_tab:
                # Only auto-refresh if inquiry has been run before
                if hasattr(self.project_management_tab, '_inquiry_run') and self.project_management_tab._inquiry_run:
                    self.project_management_tab.load_projects(silent=True)
            elif current_tab == self.calibration_tab:
                self.calibration_tab.refresh_data()
            elif current_tab == self.model_management_tab:
                self.model_management_tab.load_models()
                self.model_management_tab.on_inquiry_clicked()
        except Exception as e:
            _ = e


def main():
    load_dotenv()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

 
