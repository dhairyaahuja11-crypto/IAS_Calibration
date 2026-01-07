from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QRadioButton,
    QDoubleSpinBox, QSpinBox, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QListWidget
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg


class DimensionReductionUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ================= TOP BAR =================
        top_layout = QHBoxLayout()

        top_layout.addWidget(QLabel("select algorithm:"))

        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["PCR","PLSR"])
        top_layout.addWidget(self.algorithm_combo)

        self.reduce_btn = QPushButton("dimension\nreduction")
        top_layout.addWidget(self.reduce_btn)

        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # ================= MIDDLE AREA =================
        middle_layout = QHBoxLayout()

        # -------- LEFT LIST (PC list / variables) --------
        self.pc_list = QListWidget()
        middle_layout.addWidget(self.pc_list, 1)

        # -------- RIGHT CONTROL + PLOT --------
        right_layout = QVBoxLayout()

        # ===== Choose Group =====
        choose_group = QGroupBox("choose")
        choose_layout = QGridLayout(choose_group)

        self.radio_contribution = QRadioButton("contribution rate")
        self.radio_contribution.setChecked(True)
        choose_layout.addWidget(self.radio_contribution, 0, 0)

        self.contribution_spin = QDoubleSpinBox()
        self.contribution_spin.setRange(0.0, 1.0)
        self.contribution_spin.setSingleStep(0.01)
        self.contribution_spin.setValue(0.95)
        choose_layout.addWidget(self.contribution_spin, 0, 1)

        self.radio_pc_num = QRadioButton("number of principal components")
        choose_layout.addWidget(self.radio_pc_num, 0, 2)

        self.pc_spin = QSpinBox()
        self.pc_spin.setRange(1, 50)
        self.pc_spin.setValue(1)
        choose_layout.addWidget(self.pc_spin, 0, 3)

        self.select_dim_btn = QPushButton("select dimension")
        choose_layout.addWidget(self.select_dim_btn, 0, 4)

        right_layout.addWidget(choose_group)

        # ===== Axis Selection =====
        axis_layout = QHBoxLayout()

        axis_layout.addWidget(QLabel("X axis:"))
        self.x_axis_combo = QComboBox()
        self.x_axis_combo.addItems(["PC_1", "PC_2", "PC_3", "PC_4", "PC_5", "PC_6", 
        "PC_7", "PC_8", "PC_9", "PC_10"])
        axis_layout.addWidget(self.x_axis_combo)

        axis_layout.addWidget(QLabel("Y axis:"))
        self.y_axis_combo = QComboBox()
        self.y_axis_combo.addItems(["PC_1", "PC_2", "PC_3", "PC_4", "PC_5", "PC_6", 
        "PC_7", "PC_8", "PC_9", "PC_10"])
        axis_layout.addWidget(self.y_axis_combo)

        self.display_btn = QPushButton("display")
        self.diagram_3d_btn = QPushButton("3D diagram")
        self.save_btn = QPushButton("save the score matrix")

        axis_layout.addWidget(self.display_btn)
        axis_layout.addWidget(self.diagram_3d_btn)
        axis_layout.addWidget(self.save_btn)

        axis_layout.addStretch()
        right_layout.addLayout(axis_layout)

        # ===== Plot =====
        self.score_plot = pg.PlotWidget(
            title="principal component score diagram"
        )
        self.score_plot.setLabel("left", "PC_2")
        self.score_plot.setLabel("bottom", "PC_1")
        self.score_plot.showGrid(x=True, y=True)
        self.score_plot.setBackground("w")

        right_layout.addWidget(self.score_plot, 1)

        middle_layout.addLayout(right_layout, 3)

        main_layout.addLayout(middle_layout)
