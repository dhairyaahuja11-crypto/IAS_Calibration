from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QRadioButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QTableWidget, QTableWidgetItem, QCheckBox, QLineEdit, QSizePolicy,
    QMessageBox
)
from PyQt6.QtCore import Qt
from pathlib import Path
from datetime import datetime
import json
import math


class AnalysisMeasureUI(QWidget):
    def __init__(self):
        super().__init__()
        self.current_project_id = None
        self.current_project_name = None
        self.current_rows = []
        self._build_ui()
        self._connect_signals()
        self.refresh_data()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        model_group = QGroupBox("select model")
        model_group.setMinimumHeight(110)
        model_group.setMaximumHeight(130)
        model_layout = QGridLayout(model_group)
        model_layout.setContentsMargins(8, 8, 8, 8)
        model_layout.setSpacing(6)

        self.radio_current = QRadioButton("current project")
        self.radio_current.setChecked(True)
        model_layout.addWidget(self.radio_current, 0, 0)

        self.current_model_combo = QComboBox()
        self.current_model_combo.setMinimumWidth(150)
        self.current_model_combo.setMinimumHeight(32)
        model_layout.addWidget(self.current_model_combo, 0, 1)

        self.radio_history = QRadioButton("historical model")
        model_layout.addWidget(self.radio_history, 1, 0)

        self.history_model_combo = QComboBox()
        self.history_model_combo.setMinimumWidth(150)
        self.history_model_combo.setMinimumHeight(32)
        model_layout.addWidget(self.history_model_combo, 1, 1)

        top_layout.addWidget(model_group)

        data_group = QGroupBox("select data")
        data_group.setMinimumHeight(110)
        data_group.setMaximumHeight(130)
        data_layout = QVBoxLayout(data_group)
        data_layout.setContentsMargins(8, 8, 8, 8)
        data_layout.setSpacing(4)

        self.radio_cal = QRadioButton("calibration set")
        self.radio_cal.setChecked(True)
        self.radio_val = QRadioButton("validation set")
        self.radio_cross = QRadioButton("cross validation set")

        data_layout.addWidget(self.radio_cal)
        data_layout.addWidget(self.radio_val)
        data_layout.addWidget(self.radio_cross)

        top_layout.addWidget(data_group)

        algo_group = QGroupBox("analyse algorithm")
        algo_group.setMinimumHeight(110)
        algo_group.setMaximumHeight(130)
        algo_layout = QVBoxLayout(algo_group)
        algo_layout.setContentsMargins(8, 8, 8, 8)
        algo_layout.setSpacing(6)

        algo_layout.addWidget(QLabel("select algorithm:"))

        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems([
            "PLS quantification",
            "SIMCA", "BP-NN qualitation", "BP-NN quantification", "Fisher",
            "SVM qualitation", "SVM quantification"
        ])
        self.algorithm_combo.setMinimumWidth(170)
        self.algorithm_combo.setMinimumHeight(32)
        algo_layout.addWidget(self.algorithm_combo)

        top_layout.addWidget(algo_group)

        btn_group = QGroupBox()
        btn_group.setMinimumHeight(110)
        btn_group.setMaximumHeight(130)
        btn_layout = QVBoxLayout(btn_group)
        btn_layout.setContentsMargins(8, 8, 8, 8)
        btn_layout.setSpacing(6)

        self.analysis_btn = QPushButton("analysis")
        self.analysis_btn.setMinimumHeight(32)
        btn_layout.addWidget(self.analysis_btn)

        self.measure_btn = QPushButton("PLS quantification measure")
        self.measure_btn.setMinimumHeight(32)
        self.measure_btn.setMinimumWidth(180)
        btn_layout.addWidget(self.measure_btn)

        self.save_model_btn = QPushButton("save model")
        self.save_model_btn.setMinimumHeight(32)
        btn_layout.addWidget(self.save_model_btn)

        btn_layout.addStretch()

        top_layout.addWidget(btn_group)
        top_layout.addStretch()
        main_layout.addLayout(top_layout, 0)

        middle_layout = QHBoxLayout()

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "ID", "sample name", "serial number", "wavelength points",
            "wavelength", "absorbance", "creation time",
            "actual value", "measurement value", "relative error"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.viewport().installEventFilter(self)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8fbff;
                border: 1px solid #d8e1eb;
                border-radius: 8px;
                gridline-color: #e5ebf2;
            }
            QHeaderView::section {
                background-color: #eef3f9;
                border: 1px solid #d8e1eb;
                padding: 6px;
                font-weight: 600;
            }
        """)
        middle_layout.addWidget(self.table, 5)

        metrics_layout = QVBoxLayout()
        metrics_layout.setSpacing(5)

        self.deviation_checkbox = QCheckBox("display deviation diagram")
        metrics_layout.addWidget(self.deviation_checkbox)
        metrics_layout.addSpacing(5)

        self.metric_fields = {}
        metric_labels = [
            ("SEC:", "sec"),
            ("SECV:", "secv"),
            ("SEP:", "sep"),
            ("RPD:", "rpd"),
            ("E:", "e"),
            ("R:", "r"),
            ("R2:", "r2"),
            ("t:", "t"),
            ("accuracy:", "accuracy"),
            ("recall:", "recall")
        ]

        for label_text, field_name in metric_labels:
            row = QHBoxLayout()
            row.setSpacing(3)
            label = QLabel(label_text)
            label.setMinimumWidth(70)
            label.setMaximumWidth(70)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(label)

            field = QLineEdit()
            field.setReadOnly(True)
            field.setMinimumWidth(110)
            field.setMinimumHeight(30)
            field.setStyleSheet("""
                QLineEdit {
                    background-color: white;
                    border: 1px solid #c0c0c0;
                    padding: 2px;
                }
            """)
            row.addWidget(field)
            self.metric_fields[field_name] = field
            metrics_layout.addLayout(row)

        metrics_layout.addStretch()
        metrics_container = QWidget()
        metrics_container.setLayout(metrics_layout)
        metrics_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        middle_layout.addWidget(metrics_container, 1)

        main_layout.addLayout(middle_layout, 1)

    def _connect_signals(self):
        self.algorithm_combo.currentTextChanged.connect(self._on_algorithm_changed)
        self.analysis_btn.clicked.connect(self._on_analysis_clicked)
        self.measure_btn.clicked.connect(self._on_measure_clicked)
        self.save_model_btn.clicked.connect(self._on_save_model_clicked)
        self.radio_current.toggled.connect(self._sync_mode_state)
        self.radio_history.toggled.connect(self._sync_mode_state)

    def refresh_data(self):
        """Reload project/model sources when the tab becomes active."""
        self._load_current_projects()
        self._load_history_models()
        self._sync_mode_state()

    def _load_current_projects(self):
        try:
            from services.data_selection_service import DataSelectionService

            previous_project_id = self.current_model_combo.currentData()
            self.current_model_combo.clear()
            self.current_model_combo.addItem("", None)

            for project in DataSelectionService.get_all_projects():
                project_name = project.get("project_name", "")
                project_id = project.get("project_id", "")
                if project_name:
                    self.current_model_combo.addItem(project_name, project_id)

            if previous_project_id:
                index = self.current_model_combo.findData(previous_project_id)
                if index >= 0:
                    self.current_model_combo.setCurrentIndex(index)
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load current projects:\n{e}")

    def _load_history_models(self):
        base_dir = Path(__file__).parent.parent.parent
        results_dir = base_dir / "analysis_results"
        previous_path = self.history_model_combo.currentData()

        self.history_model_combo.clear()
        self.history_model_combo.addItem("", None)

        if not results_dir.exists():
            return

        files = sorted(results_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for file_path in files:
            self.history_model_combo.addItem(file_path.name, str(file_path))

        if previous_path:
            index = self.history_model_combo.findData(previous_path)
            if index >= 0:
                self.history_model_combo.setCurrentIndex(index)

    def _sync_mode_state(self):
        use_current = self.radio_current.isChecked()
        self.current_model_combo.setEnabled(use_current)
        self.history_model_combo.setEnabled(not use_current)

    def _on_algorithm_changed(self, algorithm):
        self.measure_btn.setText(f"{algorithm} measure")

    def _on_analysis_clicked(self):
        """Load project data or saved model details into the table."""
        if self.radio_current.isChecked():
            self._analyse_current_project()
        else:
            self._analyse_saved_model()

    def _analyse_current_project(self):
        project_id = self.current_model_combo.currentData()
        if not project_id:
            QMessageBox.warning(self, "No Project", "Please select a current project first.")
            return

        try:
            from services.data_selection_service import DataSelectionService

            samples = DataSelectionService.get_project_samples(project_id)
            project_info = DataSelectionService.get_project_info(project_id)
            self.current_project_id = project_id
            self.current_project_name = project_info.get("project_name") or self.current_model_combo.currentText()
            self.current_rows = samples

            self._populate_table(samples)
            self.clear_metrics()

            if samples:
                QMessageBox.information(
                    self,
                    "Analysis Loaded",
                    f"Loaded {len(samples)} sample(s) from project '{self.current_project_name}'."
                )
            else:
                QMessageBox.information(
                    self,
                    "No Samples",
                    f"No samples were found for project '{self.current_model_combo.currentText()}'."
                )
        except Exception as e:
            QMessageBox.critical(self, "Analysis Error", f"Failed to load project data:\n{e}")

    def _analyse_saved_model(self):
        model_path = self.history_model_combo.currentData()
        if not model_path:
            QMessageBox.warning(self, "No Model", "Please select a historical model first.")
            return

        try:
            with open(model_path, "r", encoding="utf-8") as handle:
                model_data = json.load(handle)

            self.current_project_id = None
            self.current_project_name = model_data.get("project_name") or Path(model_path).stem
            self.current_rows = model_data.get("rows", [])
            self._populate_table(self.current_rows)
            self.update_metrics(model_data.get("metrics", {}))

            QMessageBox.information(
                self,
                "Model Loaded",
                f"Loaded saved model '{Path(model_path).name}'."
            )
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load saved model:\n{e}")

    def _populate_table(self, rows):
        self.table.setRowCount(0)

        for row_idx, row in enumerate(rows):
            self.table.insertRow(row_idx)
            values = [
                row.get("sample_id", ""),
                row.get("sample_name", ""),
                row.get("serial_number", ""),
                row.get("wavelength_points", ""),
                row.get("wavelength", ""),
                row.get("absorbance", ""),
                str(row.get("create_time", "")),
                row.get("property_value", ""),
                row.get("measurement_value", ""),
                row.get("relative_error", "")
            ]

            for col_idx, value in enumerate(values):
                item = QTableWidgetItem("" if value is None else str(value))
                self.table.setItem(row_idx, col_idx, item)

    def _on_measure_clicked(self):
        """Calculate simple measurement/error metrics from loaded rows."""
        if not self.current_rows:
            QMessageBox.warning(self, "No Data", "Please run analysis first.")
            return

        actuals = []
        measurements = []

        for row_idx, row in enumerate(self.current_rows):
            actual = self._safe_float(row.get("property_value"))
            measurement = self._safe_float(row.get("measurement_value"))

            if measurement is None:
                measurement = actual
                self.current_rows[row_idx]["measurement_value"] = "" if actual is None else f"{actual:.4f}"

            if actual is not None and measurement is not None:
                actuals.append(actual)
                measurements.append(measurement)
                rel_error = 0.0 if actual == 0 else ((measurement - actual) / actual) * 100
                self.current_rows[row_idx]["relative_error"] = f"{rel_error:.2f}%"
            else:
                self.current_rows[row_idx]["relative_error"] = ""

        self._populate_table(self.current_rows)

        if not actuals:
            QMessageBox.information(
                self,
                "No Numeric Values",
                "The loaded rows do not contain numeric actual values to measure."
            )
            self.clear_metrics()
            return

        metrics = self._calculate_metrics(actuals, measurements)
        self.update_metrics(metrics)

        QMessageBox.information(
            self,
            "Measurement Complete",
            f"Calculated metrics for {len(actuals)} row(s)."
        )

    def _on_save_model_clicked(self):
        """Save the currently loaded table and metrics as a JSON report."""
        if not self.current_rows:
            QMessageBox.warning(self, "No Data", "Run analysis first before saving a model.")
            return

        try:
            base_dir = Path(__file__).parent.parent.parent
            results_dir = base_dir / "analysis_results"
            results_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            source_name = self.current_project_name or "analysis_measure"
            safe_source_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in source_name)
            filename = f"analysis_measure_{safe_source_name}_{timestamp}.json"
            filepath = results_dir / filename

            save_data = {
                "timestamp": timestamp,
                "project_id": self.current_project_id,
                "project_name": self.current_project_name,
                "algorithm": self.algorithm_combo.currentText(),
                "data_scope": self._selected_data_scope(),
                "metrics": {key: field.text() for key, field in self.metric_fields.items() if field.text()},
                "rows": self.current_rows
            }

            with open(filepath, "w", encoding="utf-8") as handle:
                json.dump(save_data, handle, indent=2, default=str)

            self._load_history_models()
            QMessageBox.information(self, "Saved", f"Model/report saved to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save model:\n{e}")

    def _selected_data_scope(self):
        if self.radio_val.isChecked():
            return "validation set"
        if self.radio_cross.isChecked():
            return "cross validation set"
        return "calibration set"

    def _calculate_metrics(self, actuals, measurements):
        count = len(actuals)
        errors = [pred - actual for actual, pred in zip(actuals, measurements)]
        abs_errors = [abs(err) for err in errors]
        squared_errors = [err * err for err in errors]

        mean_actual = sum(actuals) / count if count else 0.0
        rmse = math.sqrt(sum(squared_errors) / count) if count else 0.0
        mae = sum(abs_errors) / count if count else 0.0
        bias = sum(errors) / count if count else 0.0
        accuracy = 0.0

        percentage_errors = []
        for actual, predicted in zip(actuals, measurements):
            if actual != 0:
                percentage_errors.append(abs((predicted - actual) / actual) * 100)

        if percentage_errors:
            accuracy = max(0.0, 100.0 - (sum(percentage_errors) / len(percentage_errors)))

        numerator = sum((a - mean_actual) * (p - (sum(measurements) / count)) for a, p in zip(actuals, measurements))
        denom_a = math.sqrt(sum((a - mean_actual) ** 2 for a in actuals))
        mean_pred = sum(measurements) / count if count else 0.0
        denom_p = math.sqrt(sum((p - mean_pred) ** 2 for p in measurements))
        correlation = numerator / (denom_a * denom_p) if denom_a > 0 and denom_p > 0 else 0.0
        r2 = correlation ** 2

        std_actual = math.sqrt(sum((a - mean_actual) ** 2 for a in actuals) / count) if count else 0.0
        rpd = std_actual / rmse if rmse > 0 else 0.0

        return {
            "sec": f"{rmse:.4f}",
            "secv": f"{rmse:.4f}",
            "sep": f"{mae:.4f}",
            "rpd": f"{rpd:.4f}",
            "e": f"{bias:.4f}",
            "r": f"{correlation:.4f}",
            "r2": f"{r2:.4f}",
            "t": f"{count}",
            "accuracy": f"{accuracy:.2f}%",
            "recall": "N/A"
        }

    def _safe_float(self, value):
        if value is None:
            return None
        text = str(value).strip().replace("%", "")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def update_metrics(self, metrics_dict):
        for field_name, value in metrics_dict.items():
            if field_name in self.metric_fields:
                self.metric_fields[field_name].setText("" if value is None else str(value))

    def clear_metrics(self):
        for field in self.metric_fields.values():
            field.clear()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.table.clearSelection()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent

        if obj == self.table.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            index = self.table.indexAt(event.pos())
            if not index.isValid():
                self.table.clearSelection()
                return True

        return super().eventFilter(obj, event)
