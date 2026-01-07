import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget
)
from PyQt6.QtCore import Qt

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
        self.tabs.addTab(DataManagementUI(), "data management")
        self.tabs.addTab(SampleManagementUI(), "sample management")
        self.tabs.addTab(ProjectManagementUI(), "project management")
        self.tabs.addTab(CalibrationMainUI(), "calibration")
        self.tabs.addTab(ModelManagementUI(), "model management")
        self.tabs.addTab(InstrumentManagementUI(), "instrument management")
        self.tabs.addTab(ScanningManagementUI(), "scanning management")
        self.tabs.addTab(MeasurementDemoUI(), "measurement(demo)")

        main_layout.addWidget(self.tabs)
        self.setCentralWidget(central_widget)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()



