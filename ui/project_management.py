from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox,
    QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QDateEdit, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import QDate, pyqtSignal
from ui.custom_widgets import DateEditWithToday

# Add dialog
from ui.dialogs.project_add_dialog import ProjectAddDialog

# Modify dialog
from ui.dialogs.modify_project_management import ModifyProjectDialog

# Service
from services.project_service import ProjectService
from services.data_selection_service import DataSelectionService


class ProjectManagementUI(QWidget):
    # Signal emitted when a project is added, modified, or deleted
    project_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._inquiry_run = False  # Track if inquiry has been run at least once
        self._build_ui()
        self._connect_signals()
        self.load_projects(silent=True)

    def _log(self, message):
        """Keep routine terminal output quiet."""
        return

    # ---------------- UI ----------------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        self.setObjectName("projectManagementRoot")
        self.setStyleSheet("""
            QWidget#projectManagementRoot {
                background-color: #f6f8fb;
            }
            QLabel {
                color: #1f2937;
                font-size: 12px;
            }
            QLineEdit, QComboBox, QDateEdit {
                background-color: #ffffff;
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #7aa7ff;
            }
            QPushButton {
                background-color: #ffffff;
                color: #1f2937;
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 30px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f2f6ff;
                border-color: #aac2ef;
            }
            QPushButton:pressed {
                background-color: #e7efff;
            }
        """)

        # ---------- FILTER AREA ----------
        filter_layout = QGridLayout()
        filter_layout.setHorizontalSpacing(10)
        filter_layout.setVerticalSpacing(8)

        filter_layout.addWidget(QLabel("Project name:"), 0, 0)
        self.project_name = QLineEdit()
        filter_layout.addWidget(self.project_name, 0, 1)

        filter_layout.addWidget(QLabel("Sample Type:"), 0, 2)
        self.sample_combo = QComboBox()
        self.sample_combo.addItems(["all", "granules", "powdery", "flake"])
        filter_layout.addWidget(self.sample_combo, 0, 3)

        filter_layout.addWidget(QLabel("Type:"), 0, 4)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["all", "Qualitative", "Quantitative"])
        filter_layout.addWidget(self.type_combo, 0, 5)

        filter_layout.addWidget(QLabel("Status:"), 0, 6)
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            "all", "Created", "Gathering",
            "Modelling", "ReModelling",
            "Completed", "Data Test"
        ])
        filter_layout.addWidget(self.status_combo, 0, 7)

        filter_layout.addWidget(QLabel("User ID:"), 0, 8)
        self.user_id = QLineEdit()
        filter_layout.addWidget(self.user_id, 0, 9)

        filter_layout.addWidget(QLabel("Instrument:"), 1, 4)
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItem("all")
        filter_layout.addWidget(self.instrument_combo, 1, 5)

        filter_layout.addWidget(QLabel("Creation time:"), 1, 0)

        self.date_from = DateEditWithToday(QDate(2000, 1, 1))
        self.date_from.setDisplayFormat("dd MMMM yyyy")

        self.date_to = DateEditWithToday(QDate.currentDate())
        self.date_to.setDisplayFormat("dd MMMM yyyy")

        filter_layout.addWidget(self.date_from, 1, 1)
        filter_layout.addWidget(QLabel("~"), 1, 2)
        filter_layout.addWidget(self.date_to, 1, 3)

        main_layout.addLayout(filter_layout)

        # ---------- BUTTON BAR ----------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_inquiry = QPushButton("Inquiry")
        self.btn_add = QPushButton("Add")
        self.btn_modify = QPushButton("Modify")
        self.btn_delete = QPushButton("Delete")
        self.btn_clear_selection = QPushButton("Clear Selection")

        btn_layout.addWidget(self.btn_inquiry)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_modify)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_clear_selection)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # ---------- PROJECT TABLE ----------
        self.project_table = QTableWidget(0, 12)
        self.project_table.setHorizontalHeaderLabels([
            "ID", "project name", "sample type", "instrument", "measurement type",
            "measurement index", "status", "User ID", "remark",
            "creation time", "modification time", "State"
        ])
        
        # Set column widths
        header = self.project_table.horizontalHeader()
        self.project_table.setColumnWidth(0, 60)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        
        # Enable sorting
        self.project_table.setSortingEnabled(True)
        self.project_table.setAlternatingRowColors(True)
        self.project_table.verticalHeader().setVisible(False)
        self.project_table.verticalHeader().setDefaultSectionSize(30)
        
        # Enable row selection
        self.project_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.project_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8fbff;
                color: #111827;
                border: 1px solid #d8e1eb;
                border-radius: 6px;
                selection-background-color: #dbeafe;
                selection-color: #0f172a;
                gridline-color: #e5ebf2;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #eef3f9;
                color: #1f2937;
                padding: 7px 6px;
                border: 1px solid #d8e1eb;
                border-bottom: 1px solid #c9d6e5;
                font-weight: bold;
            }
        """)
        
        # Install event filter to detect clicks on empty table space
        self.project_table.viewport().installEventFilter(self)
        
        main_layout.addWidget(self.project_table)
        
        # Don't load data on init - only load when user clicks Inquiry
        # self.load_projects()  # Removed to avoid unnecessary DB query on startup
        self._load_instruments()

    def _load_instruments(self):
        """Populate the instrument filter with known device IDs."""
        try:
            current_text = self.instrument_combo.currentText() if hasattr(self, "instrument_combo") else "all"
            instruments = DataSelectionService.get_instruments()
            self.instrument_combo.clear()
            self.instrument_combo.addItem("all")
            for instrument in instruments:
                value = str(instrument).strip()
                if value:
                    self.instrument_combo.addItem(value)
            index = self.instrument_combo.findText(current_text)
            self.instrument_combo.setCurrentIndex(index if index >= 0 else 0)
        except Exception:
            if hasattr(self, "instrument_combo") and self.instrument_combo.count() == 0:
                self.instrument_combo.addItem("all")

    # ---------------- SIGNALS ----------------
    def _connect_signals(self):
        self.btn_inquiry.clicked.connect(self.load_projects)
        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_modify.clicked.connect(self.open_modify_dialog)
        self.btn_delete.clicked.connect(self.open_delete_dialog)
        self.btn_clear_selection.clicked.connect(self.on_clear_selection_clicked)
    
    def keyPressEvent(self, event):
        """Handle key press events - Escape to clear selection"""
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Escape:
            self.project_table.clearSelection()
        else:
            super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        """Filter events to detect clicks on empty table space"""
        from PyQt6.QtCore import QEvent
        
        if obj == self.project_table.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            index = self.project_table.indexAt(event.pos())
            if not index.isValid():
                self.project_table.clearSelection()
                return True
        
        return super().eventFilter(obj, event)
    
    def on_clear_selection_clicked(self):
        """Clear all row selections"""
        self.project_table.clearSelection()

    # ---------------- DATA LOADING ----------------
    def load_projects(self, silent=False):
        """Load projects based on filter criteria
        
        Args:
            silent (bool): If True, suppress success message after loading
        """
        try:
            # Get filter values
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
            project_name = self.project_name.text().strip()
            sample_type = self.sample_combo.currentText()
            measurement_type = self.type_combo.currentText()
            status = self.status_combo.currentText()
            user_id = self.user_id.text().strip()
            instrument = self.instrument_combo.currentText().strip()
            
            # Fetch projects from database
            projects = ProjectService.get_projects_by_filters(
                date_from=date_from,
                date_to=date_to,
                status=status if status.lower() != 'all' else None,
                measurement_type=measurement_type if measurement_type.lower() != 'all' else None,
                project_name=project_name if project_name else None,
                sample_type=sample_type if sample_type.lower() != 'all' else None,
                user_id=user_id if user_id else None,
                instrument=instrument if instrument.lower() != 'all' else None
            )
            
            # Populate table
            self.populate_table(projects)
            
            # Mark that inquiry has been run at least once
            self._inquiry_run = True
            
            # Show success message only if not silent mode
            if not silent:
                if projects:
                    self._log(f"Loaded {len(projects)} projects successfully")
                else:
                    QMessageBox.information(
                        self,
                        "No Projects Found",
                        f"No projects were created between {date_from} and {date_to} for the selected filters."
                    )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load projects: {str(e)}")
    
    def populate_table(self, projects):
        """Populate the project table with data"""
        self.project_table.setRowCount(0)
        self.project_table.setSortingEnabled(False)
        
        for project in projects:
            row = self.project_table.rowCount()
            self.project_table.insertRow(row)
            
            # Handle bytes decoding
            def decode_if_bytes(value):
                if isinstance(value, bytes):
                    return value.decode('utf-8')
                return str(value) if value is not None else ''
            
            columns = [
                decode_if_bytes(project.get('project_id', '')),
                decode_if_bytes(project.get('project_name', '')),
                decode_if_bytes(project.get('sample_type', '')),
                decode_if_bytes(project.get('instrument', '')),
                decode_if_bytes(project.get('measurement_type', '')),
                decode_if_bytes(project.get('measurement_index', '')),
                decode_if_bytes(project.get('status', '')),
                decode_if_bytes(project.get('user_id', '')),
                decode_if_bytes(project.get('remark', '')),
                decode_if_bytes(project.get('creation_time', '')),
                decode_if_bytes(project.get('modification_time', '')),
                decode_if_bytes(project.get('project_state', ''))
            ]
            
            for col, value in enumerate(columns):
                item = QTableWidgetItem(value)
                self.project_table.setItem(row, col, item)
        
        self.project_table.setSortingEnabled(True)

    # ---------------- ACTIONS ----------------
    def open_add_dialog(self):
        dialog = ProjectAddDialog(self)
        if dialog.exec():
            # Notify other tabs that projects have changed
            self.project_changed.emit()
            # Reload projects after adding
            self.load_projects()

    def open_modify_dialog(self):
        """Open modify dialog with selected project data"""
        # Get selected row
        selected_rows = self.project_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a project to modify.")
            return
        
        # Get project ID from the first selected row
        row = selected_rows[0].row()
        project_id = self.project_table.item(row, 0).text()
        
        # Fetch full project details from database
        project_data = ProjectService.get_project_by_id(project_id)
        
        if not project_data:
            QMessageBox.critical(self, "Error", f"Could not load project data for ID: {project_id}")
            return
        
        # Fetch associated samples
        project_samples = ProjectService.get_project_samples(project_id)
        
        # Open dialog with data
        self.modify_dialog = ModifyProjectDialog(self, project_data, project_samples)
        self.modify_dialog.setWindowTitle(f"Modify Project - {project_data.get('project_name', '')}")
        self.modify_dialog.resize(1200, 700)
        if self.modify_dialog.exec():
            # Reload projects after modification
            self.load_projects()
            # Notify other tabs that projects have changed
            self.project_changed.emit()

    def open_delete_dialog(self):
        """Delete selected project(s)"""
        # Get all selected rows
        selected_rows = self.project_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select at least one project to delete.")
            return
        
        # Collect all selected projects
        projects_to_delete = []
        for selected_row in selected_rows:
            row = selected_row.row()
            project_id = self.project_table.item(row, 0).text()
            project_name = self.project_table.item(row, 1).text()
            projects_to_delete.append((project_id, project_name))
        
        # Build confirmation message
        count = len(projects_to_delete)
        if count == 1:
            message = f"Delete project '{projects_to_delete[0][1]}' (ID: {projects_to_delete[0][0]})?\n\nThis will also delete all associated sample links."
        else:
            project_list = "\n".join([f"- {name} (ID: {pid})" for pid, name in projects_to_delete[:5]])
            if count > 5:
                project_list += f"\n... and {count - 5} more"
            message = f"Delete {count} projects?\n\n{project_list}\n\nThis will also delete all associated sample links."
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Warning",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Delete all selected projects
            success_count = 0
            failed_count = 0
            error_messages = []
            
            for project_id, project_name in projects_to_delete:
                success, message = ProjectService.delete_project(project_id)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                    error_messages.append(f"{project_name}: {message}")
            
            # Show result
            if failed_count == 0:
                QMessageBox.information(self, "Success", f"Successfully deleted {success_count} project(s)!")
            else:
                error_text = "\n".join(error_messages)
                QMessageBox.warning(
                    self, 
                    "Partial Success", 
                    f"Deleted: {success_count}\nFailed: {failed_count}\n\nErrors:\n{error_text}"
                )
            
            # Reload projects after deletion
            self.load_projects()
            # Notify other tabs that projects have changed
            self.project_changed.emit()
