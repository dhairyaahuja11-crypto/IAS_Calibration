from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QTableWidget, QDateEdit, QDialog, QMessageBox
)
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox

from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QGridLayout, QHBoxLayout, QVBoxLayout, QCheckBox
)


class AddInstrumentDialog(QDialog):
    """
    Temporary dialog.
    Later you can move this to ui/dialogs/add_instrument_dialog.py
    """
    def __init__(self, creation_date, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Instrument Information")
        self.creation_date = creation_date
        self._build_ui()

    def _build_ui(self):
        layout = QGridLayout(self)

        row = 0

        # ---- LEFT COLUMN ----
        layout.addWidget(QLabel("Instrument name:"), row, 0)
        self.instrument_name = QLineEdit()
        layout.addWidget(self.instrument_name, row, 1)

        layout.addWidget(QLabel("Sample type:"), row, 2)
        self.sample_type = QComboBox()
        self.sample_type.addItems(["solid", "liquid", "powder"])
        layout.addWidget(self.sample_type, row, 3)

        row += 1
        layout.addWidget(QLabel("Instrument ID:"), row, 0)
        self.instrument_id = QLineEdit()
        layout.addWidget(self.instrument_id, row, 1)

        layout.addWidget(QLabel("Workflow selection:"), row, 2)
        self.workflow = QComboBox()
        self.workflow.addItem("default")
        layout.addWidget(self.workflow, row, 3)

        row += 1
        layout.addWidget(QLabel("Instrument type:"), row, 0)
        self.instrument_type = QComboBox()
        self.instrument_type.addItem("DLP")
        layout.addWidget(self.instrument_type, row, 1)

        layout.addWidget(QLabel("Initial wavelength:"), row, 2)
        self.initial_wavelength = QSpinBox()
        self.initial_wavelength.setRange(300, 2500)
        self.initial_wavelength.setValue(900)
        layout.addWidget(self.initial_wavelength, row, 3)

        row += 1
        layout.addWidget(QLabel("Instrument form:"), row, 0)
        self.instrument_form = QComboBox()
        self.instrument_form.addItem("hand-held")
        layout.addWidget(self.instrument_form, row, 1)

        layout.addWidget(QLabel("Terminal wavelength:"), row, 2)
        self.terminal_wavelength = QSpinBox()
        self.terminal_wavelength.setRange(300, 2500)
        self.terminal_wavelength.setValue(1700)
        layout.addWidget(self.terminal_wavelength, row, 3)

        row += 1
        layout.addWidget(QLabel("Wavelength points:"), row, 0)
        self.wavelength_points = QSpinBox()
        self.wavelength_points.setRange(1, 5000)
        self.wavelength_points.setValue(801)
        layout.addWidget(self.wavelength_points, row, 1)

        layout.addWidget(QLabel("Resolution:"), row, 2)
        self.resolution = QComboBox()
        self.resolution.addItem("2.34")
        layout.addWidget(self.resolution, row, 3)

        row += 1
        layout.addWidget(QLabel("Average number:"), row, 0)
        self.average_number = QSpinBox()
        self.average_number.setValue(10)
        layout.addWidget(self.average_number, row, 1)

        layout.addWidget(QLabel("Light source mode:"), row, 2)
        self.light_source = QComboBox()
        self.light_source.addItem("build-in")
        layout.addWidget(self.light_source, row, 3)

        row += 1
        layout.addWidget(QLabel("Exposure time:"), row, 0)
        self.exposure_time = QDoubleSpinBox()
        self.exposure_time.setDecimals(3)
        self.exposure_time.setValue(0.635)
        layout.addWidget(self.exposure_time, row, 1)

        self.turntable = QCheckBox("turntable enable")
        layout.addWidget(self.turntable, row, 3)

        # ---- BUTTONS ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout, row + 1, 0, 1, 4)
    '''
    def _build_ui(self):
        layout = QGridLayout(self)

        layout.addWidget(QLabel("Instrument Name:"), 0, 0)
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit, 0, 1)

        layout.addWidget(QLabel("Instrument ID:"), 1, 0)
        self.id_edit = QLineEdit()
        layout.addWidget(self.id_edit, 1, 1)

        layout.addWidget(QLabel("Instrument Type:"), 2, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["DLP", "Hand-held"])
        layout.addWidget(self.type_combo, 2, 1)

        layout.addWidget(QLabel(f"Creation Date: {self.creation_date}"), 3, 0, 1, 2)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout, 4, 0, 1, 2)
        '''

    def get_data(self):
        return {
            "instrument_id": self.id_edit.text(),
            "instrument_name": self.name_edit.text(),
            "instrument_type": self.type_combo.currentText(),
            "creation_date": self.creation_date
        }


class InstrumentManagementUI(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------------- FILTER AREA ----------------
        filter_layout = QGridLayout()

        filter_layout.addWidget(QLabel("Instrument name:"), 0, 0)
        self.instrument_name_edit = QLineEdit()
        filter_layout.addWidget(self.instrument_name_edit, 0, 1)

        filter_layout.addWidget(QLabel("Instrument type:"), 0, 2)
        self.instrument_type_combo = QComboBox()
        self.instrument_type_combo.addItem("all")
        filter_layout.addWidget(self.instrument_type_combo, 0, 3)

        filter_layout.addWidget(QLabel("Instrument ID:"), 0, 4)
        self.instrument_id_edit = QLineEdit()
        filter_layout.addWidget(self.instrument_id_edit, 0, 5)

        filter_layout.addWidget(QLabel("Creation time:"), 0, 6)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setDisplayFormat("dd MMMM yyyy")

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd MMMM yyyy")

        filter_layout.addWidget(self.date_from, 0, 7)
        filter_layout.addWidget(QLabel("~"), 0, 8)
        filter_layout.addWidget(self.date_to, 0, 9)

        main_layout.addLayout(filter_layout)

        # ---------------- BUTTON BAR ----------------
        btn_layout = QHBoxLayout()

        self.inquiry_btn = QPushButton("Inquiry")
        self.add_btn = QPushButton("Add")
        self.modify_btn = QPushButton("Modify")
        self.delete_btn = QPushButton("Delete")

        self.add_btn.clicked.connect(self.on_add_clicked)

        btn_layout.addWidget(self.inquiry_btn)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.modify_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # ---------------- TABLE ----------------
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "", "Instrument ID", "Instrument Name",
            "Instrument Type", "Model",
            "Serial Number", "User ID",
            "Creation Time", "Status", "Remark"
        ])

        main_layout.addWidget(self.table)
    def _connect_signals(self):
        self.btn_delete.clicked.connect(self.open_delete_dialog)

    def open_delete_dialog(self):
    # 🔴 TODO: replace with real selection check
        has_selection = True   # assume something is selected for now

        if not has_selection:
            QMessageBox.information(
                self,
                "Information",
                "Please select an instrument to delete!"
            )
            return

        reply = QMessageBox.question(
            self,
            "warning",
            "delete ok ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            print("Instrument deleted")
            # TODO: delete instrument from table / database
        else:
            print("Delete cancelled")


    # ---------------- ADD BUTTON LOGIC ----------------
    def on_add_clicked(self):
        creation_date = self.date_from.date().toString("yyyy-MM-dd")

        self.add_dialog = AddInstrumentDialog(creation_date, self)
        if self.add_dialog.exec():

            data = self.add_dialog.get_data()

            # TEMP: just show confirmation
            QMessageBox.information(
                self,
                "Instrument Added",
                f"Instrument '{data['instrument_name']}' added successfully.\n"
                f"Creation date: {data['creation_date']}"
            )

            # Later → call backend here
            # self.instrument_service.add_instrument(data)
            # self.refresh_table()
