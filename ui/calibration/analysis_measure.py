from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QRadioButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QTableWidget, QTableWidgetItem, QCheckBox, QLineEdit, QSizePolicy,
    QDialog, QInputDialog,
    QMessageBox
)
from PyQt6.QtCore import Qt
from pathlib import Path
from datetime import datetime
import json
import math
import numpy as np

from services.chemometric_service import ChemometricAnalyzer
from services.model_management_service import ModelManagementService
from ui.plot_widget import PlotWidget


class AnalysisMeasureUI(QWidget):
    MAX_CELL_TEXT = 96

    def __init__(self):
        super().__init__()
        self.current_project_id = None
        self.current_project_name = None
        self.current_rows = []
        self.analysis_context = None
        self.deviation_dialog = None
        self.deviation_plot = None
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

        self.table = QTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels([
            "ID", "sample name", "serial number", "wavelength points",
            "wavelength", "absorbance", "creation time",
            "actual value", "measurement value", "deviation", "error", "relative error"
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
            ("Max E:", "e"),
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
        self.radio_cal.toggled.connect(self._refresh_context_rows_for_scope)
        self.radio_val.toggled.connect(self._refresh_context_rows_for_scope)
        self.radio_cross.toggled.connect(self._refresh_context_rows_for_scope)
        self.deviation_checkbox.toggled.connect(self._on_deviation_toggled)

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
        previous_path = self.history_model_combo.currentData()

        self.history_model_combo.clear()
        self.history_model_combo.addItem("", None)

        for record in ModelManagementService.list_models():
            label = record["model_name"]
            if record["project_name"]:
                label = f"{record['model_name']} ({record['project_name']})"
            self.history_model_combo.addItem(label, record["_path"])

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
        selected_project_id = self.current_model_combo.currentData()
        context_project_id = self.analysis_context.get("project_id") if self.analysis_context else None

        if (
            self.analysis_context
            and self.analysis_context.get("project_name")
            and (
                not selected_project_id
                or str(selected_project_id) == str(context_project_id)
            )
        ):
            try:
                rows = self._rows_from_context_scope()
                self.current_project_id = self.analysis_context.get("project_id")
                self.current_project_name = self.analysis_context.get("project_name")
                self.current_rows = rows
                self._populate_table(rows)
                self.clear_metrics()
                QMessageBox.information(
                    self,
                    "Analysis Loaded",
                    f"Loaded {len(rows)} {self._selected_data_scope()} row(s) from project '{self.current_project_name}'."
                )
                return
            except Exception as e:
                QMessageBox.warning(self, "Context Error", f"Failed to load carried analysis context:\n{e}")

        project_id = selected_project_id
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
            model_data = ModelManagementService.load_model(model_path)

            self.current_project_id = model_data.get("project_id")
            self.current_project_name = model_data.get("model_name") or model_data.get("project_name") or Path(model_path).stem
            self.current_rows = model_data.get("rows", [])
            self._populate_table(self.current_rows)
            self.update_metrics(model_data.get("metrics", {}))

            QMessageBox.information(
                self,
                "Model Loaded",
                f"Loaded saved model '{self.current_project_name}'."
            )
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load saved model:\n{e}")

    def _populate_table(self, rows):
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)

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
                row.get("deviation", ""),
                row.get("absolute_error", ""),
                row.get("relative_error", "")
            ]

            for col_idx, value in enumerate(values):
                raw_text = "" if value is None else str(value)
                display_text = self._format_table_cell(raw_text, col_idx)
                item = QTableWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, raw_text)
                item.setToolTip(raw_text if len(raw_text) > len(display_text) else "")
                self.table.setItem(row_idx, col_idx, item)

        self.table.setSortingEnabled(True)

    def _format_table_cell(self, text, col_idx):
        """Keep very large spectral strings from overloading the table view."""
        if col_idx in (4, 5) and len(text) > self.MAX_CELL_TEXT:
            return text[:self.MAX_CELL_TEXT] + "..."
        return text

    def _on_measure_clicked(self):
        """Calculate measurement/error metrics from model predictions."""
        if not self.current_rows:
            QMessageBox.warning(self, "No Data", "Please run analysis first.")
            return

        if self.analysis_context:
            if self._measure_from_context():
                return

        try:
            valid_indices, spectra, actuals = self._extract_numeric_dataset(self.current_rows)
        except ValueError as e:
            QMessageBox.warning(self, "Measure Error", str(e))
            self.clear_metrics()
            return

        if len(actuals) == 0:
            QMessageBox.information(
                self,
                "No Numeric Values",
                "The loaded rows do not contain numeric actual values to measure."
            )
            self.clear_metrics()
            return

        scope = self._selected_data_scope()
        analyzer = ChemometricAnalyzer()
        results = analyzer.perform_pls(
            spectra,
            actuals,
            n_components=min(12, spectra.shape[1], len(actuals)),
            cv=5,
            optimize=True
        )

        if scope == "cross validation set":
            predictions = results["y_pred_cv"]
        elif scope == "validation set":
            QMessageBox.information(
                self,
                "Validation Set",
                "No dedicated validation subset is defined in this tab yet.\n\n"
                "Using cross-validation predictions for deviation metrics."
            )
            predictions = results["y_pred_cv"]
        else:
            predictions = results["y_pred_train"]

        for row in self.current_rows:
            row["measurement_value"] = ""
            row["deviation"] = ""
            row["absolute_error"] = ""
            row["relative_error"] = ""

        for row_idx, actual, measurement in zip(valid_indices, actuals, predictions):
            self.current_rows[row_idx]["measurement_value"] = f"{measurement:.4f}"
            deviation = measurement - actual
            rel_error = 0.0 if actual == 0 else (deviation / actual) * 100
            self.current_rows[row_idx]["deviation"] = f"{deviation:+.4f}"
            self.current_rows[row_idx]["absolute_error"] = f"{abs(deviation):.4f}"
            self.current_rows[row_idx]["relative_error"] = f"{rel_error:.2f}%"

        self._populate_table(self.current_rows)
        metrics = self._calculate_metrics(actuals, predictions)
        metrics["sec"] = f"{results['rmse_train']:.4f}"
        metrics["secv"] = f"{results['rmse_cv']:.4f}"
        metrics["r2"] = f"{(results['r2_cv'] if scope != 'calibration set' else results['r2_train']):.4f}"
        self.update_metrics(metrics)
        self._update_deviation_diagram()

        QMessageBox.information(
            self,
            "Measurement Complete",
            f"Calculated model-based metrics for {len(actuals)} row(s)."
        )

    def _measure_from_context(self):
        """Use calibration/validation datasets carried from previous tabs."""
        scope = self._selected_data_scope()
        calibration_spectra = self.analysis_context.get("calibration_spectra")
        calibration_targets = self.analysis_context.get("calibration_targets")
        validation_spectra = self.analysis_context.get("validation_spectra")
        validation_targets = self.analysis_context.get("validation_targets")
        dim_results = self.analysis_context.get("dimension_results") or {}
        cv_folds = int(dim_results.get("cv_folds", 5) or 0)

        if calibration_spectra is None or calibration_targets is None:
            return False

        analyzer = ChemometricAnalyzer()
        if dim_results.get("best_n_components"):
            results = analyzer.perform_pls(
                calibration_spectra,
                calibration_targets,
                n_components=int(dim_results["best_n_components"]),
                cv=cv_folds,
                optimize=False
            )
        else:
            results = analyzer.perform_pls(
                calibration_spectra,
                calibration_targets,
                n_components=min(12, calibration_spectra.shape[1], len(calibration_targets)),
                cv=cv_folds,
                optimize=True
            )

        if scope == "validation set":
            if validation_spectra is None or validation_targets is None or len(validation_targets) == 0:
                QMessageBox.information(self, "No Validation Data", "No validation dataset is available.")
                self.clear_metrics()
                return True
            predictions = analyzer.predict(validation_spectra)
            actuals = validation_targets
        elif scope == "cross validation set":
            predictions = results["y_pred_cv"]
            actuals = calibration_targets
        else:
            predictions = results["y_pred_train"]
            actuals = calibration_targets

        for row in self.current_rows:
            row["measurement_value"] = ""
            row["deviation"] = ""
            row["absolute_error"] = ""
            row["relative_error"] = ""

        for row, actual, measurement in zip(self.current_rows, actuals, predictions):
            row["measurement_value"] = f"{measurement:.4f}"
            deviation = measurement - actual
            rel_error = 0.0 if actual == 0 else (deviation / actual) * 100
            row["deviation"] = f"{deviation:+.4f}"
            row["absolute_error"] = f"{abs(deviation):.4f}"
            row["relative_error"] = f"{rel_error:.2f}%"

        self._populate_table(self.current_rows)
        metrics = self._calculate_metrics(actuals, predictions)
        metrics["sec"] = f"{results['rmse_train']:.4f}"
        metrics["secv"] = f"{results['rmse_cv']:.4f}"
        if scope == "validation set":
            rmse_val = math.sqrt(sum((pred - actual) ** 2 for actual, pred in zip(actuals, predictions)) / len(actuals))
            metrics["sep"] = f"{rmse_val:.4f}"
            mean_actual = sum(actuals) / len(actuals)
            ss_tot = sum((actual - mean_actual) ** 2 for actual in actuals)
            ss_res = sum((pred - actual) ** 2 for actual, pred in zip(actuals, predictions))
            metrics["r2"] = f"{(1 - ss_res / ss_tot):.4f}" if ss_tot > 0 else "0.0000"
        elif scope == "cross validation set":
            metrics["r2"] = f"{results['r2_cv']:.4f}"
        else:
            metrics["r2"] = f"{results['r2_train']:.4f}"
        self.update_metrics(metrics)
        self._update_deviation_diagram()
        QMessageBox.information(
            self,
            "Measurement Complete",
            f"Calculated {scope} metrics for {len(actuals)} row(s)."
        )
        return True

    def load_analysis_context(self, context):
        """Load calibration/validation datasets carried from earlier tabs."""
        self.analysis_context = context
        self._refresh_context_rows_for_scope()

    def _refresh_context_rows_for_scope(self):
        """Refresh the table when the selected data scope changes."""
        if not self.analysis_context or not self.radio_current.isChecked():
            return

        rows = self._rows_from_context_scope()
        self.current_rows = rows
        self._populate_table(rows)
        self.clear_metrics()

    def _rows_from_context_scope(self):
        """Build table rows from the active calibration/validation scope."""
        if not self.analysis_context:
            return []

        scope = self._selected_data_scope()
        if scope == "validation set":
            spectra = self.analysis_context.get("validation_spectra")
            targets = self.analysis_context.get("validation_targets")
            metadata = self.analysis_context.get("validation_metadata") or []
        else:
            spectra = self.analysis_context.get("calibration_spectra")
            targets = self.analysis_context.get("calibration_targets")
            metadata = self.analysis_context.get("calibration_metadata") or []

        if spectra is None or targets is None:
            return []

        rows = []
        wavelengths = self.analysis_context.get("wavelengths")
        wavelength_text = ",".join(map(str, wavelengths.tolist())) if isinstance(wavelengths, np.ndarray) else ""

        for idx, (target, spectrum) in enumerate(zip(targets, spectra)):
            meta = metadata[idx] if idx < len(metadata) else {}
            rows.append({
                "sample_id": meta.get("sample_id", ""),
                "sample_name": meta.get("sample_name", f"Sample {idx + 1}"),
                "serial_number": meta.get("serial_number", meta.get("sample_name", f"Sample {idx + 1}")),
                "instrument": meta.get("instrument", ""),
                "user_id": meta.get("user_id", ""),
                "property_name": meta.get("property_name", ""),
                "wavelength_points": meta.get("wavelength_points", len(spectrum)),
                "wavelength": wavelength_text,
                "absorbance": ",".join(map(str, spectrum.tolist())),
                "create_time": meta.get("create_time", ""),
                "property_value": f"{float(target):.4f}",
                "measurement_value": "",
                "deviation": "",
                "absolute_error": "",
                "relative_error": ""
            })
        return rows

    def _extract_numeric_dataset(self, rows):
        """Build aligned spectra/target arrays from loaded table rows."""
        valid_indices = []
        spectra = []
        actuals = []

        for row_idx, row in enumerate(rows):
            actual = self._safe_float(row.get("property_value"))
            absorbance_text = row.get("absorbance")
            spectrum = self._parse_series(absorbance_text)

            if actual is None or spectrum is None:
                continue

            valid_indices.append(row_idx)
            actuals.append(actual)
            spectra.append(spectrum)

        if not spectra:
            raise ValueError("No rows contain both numeric absorbance data and numeric actual values.")

        lengths = {len(spectrum) for spectrum in spectra}
        if len(lengths) != 1:
            raise ValueError("Loaded rows contain inconsistent absorbance lengths, so a PLS model cannot be built.")

        return valid_indices, np.array(spectra, dtype=float), np.array(actuals, dtype=float)

    def _parse_series(self, value):
        """Parse comma-separated numeric vectors from stored row values."""
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        try:
            parts = [part.strip() for part in text.split(",") if part.strip()]
            if not parts:
                return None
            return [float(part) for part in parts]
        except ValueError:
            return None

    def _summarize_unique_values(self, rows, key):
        values = []
        for row in rows:
            value = str(row.get(key, "")).strip()
            if value and value not in values:
                values.append(value)
        return ", ".join(values)

    def _build_model_payload(self, model_name):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        context = self.analysis_context or {}
        temp_metadata = context.get("temp_metadata") or {}
        intercept_metadata = context.get("intercept_metadata") or {}
        dimension_results = context.get("dimension_results") or {}
        deployable_model = self._build_deployable_model(model_name, timestamp, created_at, context, dimension_results)

        calibration_targets = context.get("calibration_targets")
        validation_targets = context.get("validation_targets")
        calibration_count = len(calibration_targets) if calibration_targets is not None else (
            len(self.current_rows) if self._selected_data_scope() == "calibration set" else ""
        )
        validation_count = len(validation_targets) if validation_targets is not None else ""

        analysis_parameters = []
        if dimension_results.get("best_n_components"):
            analysis_parameters.append(f"components={dimension_results['best_n_components']}")
        if dimension_results.get("cv_folds"):
            analysis_parameters.append(f"cv={dimension_results['cv_folds']}")
        if dimension_results.get("optimized") is not None:
            analysis_parameters.append(f"optimized={dimension_results['optimized']}")

        model_id = f"M{timestamp}"
        return {
            "record_type": "saved_model",
            "timestamp": timestamp,
            "creation_time": created_at,
            "model_id": model_id,
            "model_name": model_name,
            "project_id": self.current_project_id,
            "project_name": self.current_project_name,
            "measurement_index": context.get("measurement_index") or self._summarize_unique_values(self.current_rows, "property_name"),
            "instrument": self._summarize_unique_values(self.current_rows, "instrument") or context.get("instrument", ""),
            "wavelength_points": self.current_rows[0].get("wavelength_points", "") if self.current_rows else "",
            "calibration_count": calibration_count,
            "validation_count": validation_count,
            "intercept_data": intercept_metadata.get("range") or temp_metadata.get("crop_range", ""),
            "average_enable": "Yes" if str(temp_metadata.get("data_type", "")).strip().lower() == "averaged" else "No",
            "pretreatment_summary": " -> ".join(context.get("pretreatment_steps") or []),
            "intercept_after_pretreatment": intercept_metadata.get("detail", ""),
            "dimension_reduction_algorithm": context.get("dimension_algorithm") or "",
            "dimension": dimension_results.get("best_n_components") or dimension_results.get("n_components", ""),
            "algorithm": self.algorithm_combo.currentText(),
            "analysis_algorithm": self.algorithm_combo.currentText(),
            "analysis_algorithm_parameters": "; ".join(analysis_parameters),
            "user_id": self._summarize_unique_values(self.current_rows, "user_id"),
            "data_scope": self._selected_data_scope(),
            "metrics": {key: field.text() for key, field in self.metric_fields.items() if field.text()},
            "rows": self.current_rows,
            "deployable_model": deployable_model,
        }

    def _build_deployable_model(self, model_name, timestamp, created_at, context, dimension_results):
        if not dimension_results:
            return {}

        coefficients = dimension_results.get("coefficients")
        intercept = dimension_results.get("intercept")
        best_n_components = dimension_results.get("best_n_components") or dimension_results.get("n_components")
        wavelengths = context.get("wavelengths")
        pretreatment_steps = list(context.get("pretreatment_steps") or [])
        intercept_metadata = context.get("intercept_metadata") or {}

        if coefficients is None or intercept is None:
            return {}

        wavelength_values = []
        if isinstance(wavelengths, np.ndarray):
            wavelength_values = wavelengths.tolist()
        elif isinstance(wavelengths, list):
            wavelength_values = wavelengths

        coefficient_values = coefficients.tolist() if hasattr(coefficients, "tolist") else list(coefficients)

        return {
            "format": "agnext_pls_v1",
            "timestamp": timestamp,
            "creation_time": created_at,
            "model_id": f"M{timestamp}",
            "model_name": model_name,
            "project_id": self.current_project_id,
            "project_name": self.current_project_name,
            "algorithm": "PLS",
            "analysis_algorithm": self.algorithm_combo.currentText(),
            "measurement_index": context.get("measurement_index") or self._summarize_unique_values(self.current_rows, "property_name"),
            "instrument": self._summarize_unique_values(self.current_rows, "instrument") or context.get("instrument", ""),
            "wavelength_points": len(wavelength_values) or (self.current_rows[0].get("wavelength_points", "") if self.current_rows else ""),
            "wavelengths": wavelength_values,
            "coefficients": coefficient_values,
            "intercept": float(intercept),
            "n_components": int(best_n_components) if best_n_components not in (None, "") else None,
            "pretreatment_steps": pretreatment_steps,
            "intercept_range": intercept_metadata.get("range") or "",
            "intercept_detail": intercept_metadata.get("detail") or "",
            "metrics": {key: field.text() for key, field in self.metric_fields.items() if field.text()},
        }

    def _on_save_model_clicked(self):
        """Save the currently loaded table and metrics as a named model JSON."""
        if not self.current_rows:
            QMessageBox.warning(self, "No Data", "Run analysis first before saving a model.")
            return

        try:
            suggested_name = self.current_project_name or "model"
            model_name, accepted = QInputDialog.getText(
                self,
                "Save Model",
                "Please input model name:",
                text=suggested_name
            )
            model_name = model_name.strip()
            if not accepted:
                return
            if not model_name:
                QMessageBox.warning(self, "Missing Name", "Please enter a model name before saving.")
                return

            save_data = self._build_model_payload(model_name)
            filepath = ModelManagementService.save_model(save_data, model_name)
            self._load_history_models()
            QMessageBox.information(self, "Saved", f"Model saved to:\n{filepath}")
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
        max_error = max(abs_errors) if abs_errors else 0.0
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
            "e": f"{max_error:.4f}",
            "r": f"{correlation:.4f}",
            "r2": f"{r2:.4f}",
            "t": f"{count}",
            "accuracy": f"{accuracy:.2f}%",
            "recall": "N/A"
        }

    def _on_deviation_toggled(self, checked):
        if checked:
            self._update_deviation_diagram()
        elif self.deviation_dialog is not None:
            self.deviation_dialog.hide()

    def _get_deviation_points(self):
        rows = []
        actuals = []
        predicted = []

        for row in self.current_rows:
            actual = self._safe_float(row.get("property_value"))
            measurement = self._safe_float(row.get("measurement_value"))
            if actual is None or measurement is None:
                continue
            rows.append(row)
            actuals.append(actual)
            predicted.append(measurement)

        if not actuals:
            return None, None, None

        return rows, np.array(actuals, dtype=float), np.array(predicted, dtype=float)

    def _ensure_deviation_dialog(self):
        if self.deviation_dialog is not None:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Deviation and Error Diagram")
        dialog.resize(760, 560)
        layout = QVBoxLayout(dialog)

        plot = PlotWidget(show_toolbar=True)
        plot.reset_axes(
            title="",
            xlabel="Actual Value",
            ylabel="Measured / Predicted Value"
        )
        plot.draw()
        layout.addWidget(plot)

        self.deviation_dialog = dialog
        self.deviation_plot = plot

    def _update_deviation_diagram(self):
        if not self.deviation_checkbox.isChecked():
            return

        rows, actuals, predicted = self._get_deviation_points()
        if rows is None or actuals is None or predicted is None or len(actuals) == 0:
            if self.deviation_dialog is not None:
                self.deviation_dialog.hide()
            return

        self._ensure_deviation_dialog()
        self.deviation_plot.clear()
        self.deviation_plot.reset_axes(
            title=f"Deviation and Error Diagram ({self._selected_data_scope()})",
            xlabel="Actual Value",
            ylabel="Measured / Predicted Value"
        )

        min_val = float(min(np.min(actuals), np.min(predicted)))
        max_val = float(max(np.max(actuals), np.max(predicted)))
        if math.isclose(min_val, max_val):
            min_val -= 1.0
            max_val += 1.0

        self.deviation_plot.ax.plot(
            [min_val, max_val],
            [min_val, max_val],
            color="#6b7280",
            linewidth=2,
            linestyle="--"
        )

        x_vals = []
        y_vals = []
        tooltips = []
        for row, actual, measurement in zip(rows, actuals, predicted):
            sample_name = row.get("sample_name", "Sample")
            deviation = measurement - actual
            x_vals.append(actual)
            y_vals.append(measurement)
            tooltips.append(
                f"{sample_name}\n"
                f"Actual: {actual:.4f}\n"
                f"Measured: {measurement:.4f}\n"
                f"Deviation: {deviation:+.4f}\n"
                f"Error: {abs(deviation):.4f}"
            )

        scatter = self.deviation_plot.ax.scatter(
            x_vals,
            y_vals,
            s=70,
            c="#2563eb",
            edgecolors="white",
            linewidths=0.8,
            alpha=0.85,
            picker=True
        )
        self.deviation_plot.ax.set_xlim(min_val, max_val)
        self.deviation_plot.ax.set_ylim(min_val, max_val)
        self.deviation_plot.draw()
        self._deviation_tooltips = tooltips
        self._deviation_scatter = scatter
        self.deviation_plot.canvas.mpl_connect("pick_event", self._on_deviation_point_clicked)

        self.deviation_dialog.show()
        self.deviation_dialog.raise_()
        self.deviation_dialog.activateWindow()

    def _on_deviation_point_clicked(self, event):
        if getattr(self, "_deviation_scatter", None) is None or event.artist is not self._deviation_scatter:
            return
        if not getattr(event, "ind", None):
            return
        point_index = event.ind[0]
        tip = self._deviation_tooltips[point_index] if point_index < len(getattr(self, "_deviation_tooltips", [])) else None
        if tip:
            QMessageBox.information(self, "Deviation Point", tip)

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
