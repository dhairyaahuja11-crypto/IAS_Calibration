from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg


class PreTreatmentUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)

        # ================= LEFT CONTROL PANEL =================
        control_panel = QVBoxLayout()

        self.reset_btn = QPushButton("reset")
        control_panel.addWidget(self.reset_btn)

        control_panel.addSpacing(10)

        control_panel.addWidget(QLabel("interception\nalgorithm:"))
        self.intercept_algo = QComboBox()
        self.intercept_algo.addItems(["LPG", "SPG", "Manual Selection"])
        control_panel.addWidget(self.intercept_algo)

        control_panel.addSpacing(10)

        self.intercept_btn = QPushButton("intercept data")
        control_panel.addWidget(self.intercept_btn)

        control_panel.addSpacing(10)

        control_panel.addWidget(QLabel("pre-treatment"))
        self.pretreat_combo = QComboBox()
        self.pretreat_combo.addItems([
            "mean-centering","moving smoothing", "autoscaling",
            "SG smoothing","normalization", "detrending", "MSC",
            "SNV", "SG 1st derivative", "SG 2nd derivative"
        ])
        control_panel.addWidget(self.pretreat_combo)

        control_panel.addSpacing(15)

        self.operation_btn = QPushButton("operation")
        self.operation_combo_btn = QPushButton("operation\ncombination")

        control_panel.addWidget(self.operation_btn)
        control_panel.addWidget(self.operation_combo_btn)

        control_panel.addStretch()

        main_layout.addLayout(control_panel, 1)

        # ================= RIGHT PLOTS AREA =================
        plots_layout = QGridLayout()

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

        main_layout.addLayout(plots_layout, 5)

    # ================= PLOT FACTORY =================
    def _create_plot(self, title, y_label, x_label):
        plot = pg.PlotWidget(title=title)
        plot.setLabel("left", y_label)
        plot.setLabel("bottom", x_label)
        plot.showGrid(x=True, y=True)
        plot.setBackground("w")
        return plot
