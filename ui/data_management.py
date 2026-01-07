from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget,
    QSplitter, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
import pyqtgraph as pg

# 👉 IMPORT THE DIALOG
from ui.dialogs.data_import_dialog import DataImportDialog


class DataManagementUI(QWidget):
    def __init__(self):
        super().__init__()
        self.import_dialog = None  # ✅ persistent reference
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------------- FILTER AREA ----------------
        filter_layout = QGridLayout()

        filter_layout.addWidget(QLabel("Creation time:"), 0, 0)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setDisplayFormat("dd MMMM yyyy")

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd MMMM yyyy")

        filter_layout.addWidget(self.date_from, 0, 1)
        filter_layout.addWidget(QLabel("~"), 0, 2)
        filter_layout.addWidget(self.date_to, 0, 3)

        filter_layout.addWidget(QLabel("Instrument:"), 0, 4)
        self.instrument = QComboBox()
        self.instrument.addItem("all")
        filter_layout.addWidget(self.instrument, 0, 5)

        filter_layout.addWidget(QLabel("Absorb from"), 0, 6)
        self.absorb_from = QLineEdit("0")
        filter_layout.addWidget(self.absorb_from, 0, 7)

        filter_layout.addWidget(QLabel("to"), 0, 8)
        self.absorb_to = QLineEdit("30")
        filter_layout.addWidget(self.absorb_to, 0, 9)

        filter_layout.addWidget(QLabel("Project:"), 0, 10)
        self.project = QComboBox()
        self.project.addItem("all")
        filter_layout.addWidget(self.project, 0, 11)

        filter_layout.addWidget(QLabel("Sample name:"), 1, 0)
        self.sample_name = QLineEdit()
        filter_layout.addWidget(self.sample_name, 1, 1, 1, 2)

        filter_layout.addWidget(QLabel("Lot number:"), 1, 3)
        self.lot_number = QLineEdit()
        filter_layout.addWidget(self.lot_number, 1, 4)

        main_layout.addLayout(filter_layout)

        # ---------------- BUTTON BAR ----------------
        btn_layout = QHBoxLayout()

        self.btn_inquiry = QPushButton("Inquiry")
        self.btn_batch_delete = QPushButton("Batch Deletion")
        self.btn_tick = QPushButton("Tick")
        self.btn_export = QPushButton("Data Export")
        self.btn_import = QPushButton("Data Import")
        self.btn_spectrogram = QPushButton("Spectrogram Display")

        btn_layout.addWidget(self.btn_inquiry)
        btn_layout.addWidget(self.btn_batch_delete)
        btn_layout.addWidget(self.btn_tick)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_import)
        btn_layout.addWidget(self.btn_spectrogram)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # ---------------- MAIN CONTENT ----------------
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "", "ID", "Sample Name", "Instrument",
            "Lot Number", "Serial Number",
            "Absorb Points", "Wavelength"
        ])
        splitter.addWidget(self.table)

        self.plot = pg.PlotWidget(
            title="wavelength-absorbance spectrogram"
        )
        self.plot.setLabel("left", "Absorbance (AU)")
        self.plot.setLabel("bottom", "Wavelength (nm)")
        self.plot.showGrid(x=True, y=True)
        splitter.addWidget(self.plot)

        splitter.setSizes([900, 600])
        main_layout.addWidget(splitter)

    # ---------------- SIGNALS ----------------
    def _connect_signals(self):
        self.btn_import.clicked.connect(self.open_data_import_dialog)

    # ---------------- ACTIONS ----------------
    def open_data_import_dialog(self):
        print("Opening Data Import dialog")
        self.import_dialog = DataImportDialog(self)
        self.import_dialog.setModal(True)
        self.import_dialog.show()
