from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QRadioButton,
    QDoubleSpinBox, QSpinBox, QVBoxLayout, QHBoxLayout,
    QGroupBox, QMessageBox, QListWidget, QCheckBox, QMenu,
    QDialog, QDialogButtonBox, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
import numpy as np
from services.chemometric_service import ChemometricAnalyzer
from pathlib import Path
import json
from datetime import datetime
from ui.plot_widget import PlotWidget


class DimensionReductionUI(QWidget):
    def __init__(self):
        super().__init__()
        self.analyzer = ChemometricAnalyzer()
        self.preprocessed_data = None  # Will store data from pre-treatment
        self.wavelengths = None
        self.target_values = None  # For PLSR
        self.sample_metadata = []  # Store sample names and property values
        self.validation_data = None
        self.excluded_indices = []  # Track excluded sample indices
        self.validation_indices = []  # Track validation set indices
        self.current_results = None
        self.analysis_indices = []  # Original sample indices used in the current result set
        self.current_plot_mode = None
        self.current_plot_payload = {}
        self._secondary_axis = None
        self._mpl_pick_map = {}
        self._mpl_pick_connection = None
        self._mpl_hover_connection = None
        self.tooltip_text = None
        
        # Multi-select outlier removal state
        self.selection_mode = False
        self.selected_points = []  # List of selected sample indices
        
        self._build_ui()
        self._connect_signals()
        
    def _connect_signals(self):
        """Connect UI signals"""
        self.reduce_btn.clicked.connect(self.on_dimension_reduction_clicked)
        self.select_dim_btn.clicked.connect(self.on_select_dimension_clicked)
        self.display_btn.clicked.connect(self.on_display_clicked)
        self.diagram_3d_btn.clicked.connect(self.on_3d_diagram_clicked)
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.algorithm_combo.currentTextChanged.connect(self.on_algorithm_changed)
        self.select_outliers_btn.clicked.connect(self.on_select_outliers_clicked)
        
        # Connect PLSR-specific buttons
        self.plot_predictions_btn.clicked.connect(self.on_plot_predictions_clicked)
        self.plot_coefficients_btn.clicked.connect(self.on_plot_coefficients_clicked)
        self.plot_component_selection_btn.clicked.connect(self.on_plot_component_selection_clicked)
        
        # Set initial visibility for PLSR controls
        self.on_algorithm_changed(self.algorithm_combo.currentText())
    
    def on_algorithm_changed(self, algorithm):
        """Show/hide PLSR-specific controls"""
        is_plsr = (algorithm == "PLSR")
        self.cv_label.setVisible(is_plsr)
        self.cv_spin.setVisible(is_plsr)
        self.optimize_check.setVisible(is_plsr)
        
        # Show/hide PLSR-specific plot buttons
        self.plot_predictions_btn.setVisible(is_plsr)
        self.plot_coefficients_btn.setVisible(is_plsr)
        self.plot_component_selection_btn.setVisible(is_plsr)
        
        # Show/hide PCA-specific controls
        is_pca = (algorithm == "PCA")
        self.x_axis_combo.setVisible(is_pca)
        self.y_axis_combo.setVisible(is_pca)
        self.display_btn.setVisible(is_pca)
        self.diagram_3d_btn.setVisible(is_pca)
        # Labels for axis selection
        for i in range(self.x_axis_combo.parent().layout().count()):
            widget = self.x_axis_combo.parent().layout().itemAt(i).widget()
            if isinstance(widget, QLabel) and ("X axis" in widget.text() or "Y axis" in widget.text()):
                widget.setVisible(is_pca)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ================= TOP BAR =================
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        top_layout.addWidget(QLabel("select algorithm:"))

        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["PCA", "PLSR"])
        self.algorithm_combo.setMinimumWidth(90)
        self.algorithm_combo.setMinimumHeight(34)
        top_layout.addWidget(self.algorithm_combo)
        
        # Max components input
        top_layout.addWidget(QLabel("max components:"))
        self.max_components_spin = QSpinBox()
        self.max_components_spin.setRange(1, 20)
        self.max_components_spin.setValue(10)
        self.max_components_spin.setMinimumWidth(90)
        self.max_components_spin.setMinimumHeight(34)
        top_layout.addWidget(self.max_components_spin)
        
        # CV folds (for PLSR)
        self.cv_label = QLabel("CV folds:")
        top_layout.addWidget(self.cv_label)
        self.cv_spin = QSpinBox()
        self.cv_spin.setRange(0, 10)
        self.cv_spin.setValue(5)
        self.cv_spin.setToolTip("Set to 0 to disable cross-validation and train on all samples.")
        self.cv_spin.setMinimumWidth(80)
        self.cv_spin.setMinimumHeight(34)
        top_layout.addWidget(self.cv_spin)
        
        # Optimize checkbox (for PLSR)
        self.optimize_check = QCheckBox("Optimize components")
        self.optimize_check.setChecked(True)
        top_layout.addWidget(self.optimize_check)

        top_layout.addStretch()

        self.reduce_btn = QPushButton("dimension reduction")
        self.reduce_btn.setMinimumHeight(36)
        self.reduce_btn.setMinimumWidth(170)
        top_layout.addWidget(self.reduce_btn)

        main_layout.addLayout(top_layout)

        # ================= MAIN CONTENT AREA =================
        main_content = QHBoxLayout()

        # -------- LEFT: Info Display Area --------
        left_panel = QVBoxLayout()
        left_panel.setSpacing(8)

        self.info_list = QListWidget()
        self.info_list.setMinimumWidth(300)
        self.info_list.setMaximumWidth(360)
        self.info_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        left_panel.addWidget(self.info_list, 2)

        component_table_label = QLabel("Component Iterations")
        left_panel.addWidget(component_table_label)

        self.component_table = QTableWidget(0, 3)
        self.component_table.setHorizontalHeaderLabels(["Comp", "R2(CV)", "RMSE(CV)"])
        self.component_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.component_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.component_table.verticalHeader().setVisible(False)
        self.component_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.component_table.horizontalHeader().setStretchLastSection(True)
        self.component_table.setMinimumWidth(300)
        self.component_table.setMaximumWidth(360)
        self.component_table.setMaximumHeight(180)
        left_panel.addWidget(self.component_table)

        fold_table_label = QLabel("Cross-Validation Folds")
        left_panel.addWidget(fold_table_label)

        self.fold_table = QTableWidget(0, 4)
        self.fold_table.setHorizontalHeaderLabels(["Fold", "R2", "RMSE", "Samples"])
        self.fold_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fold_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.fold_table.verticalHeader().setVisible(False)
        self.fold_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fold_table.horizontalHeader().setStretchLastSection(True)
        self.fold_table.setMinimumWidth(300)
        self.fold_table.setMaximumWidth(360)
        self.fold_table.setMaximumHeight(220)
        left_panel.addWidget(self.fold_table)

        main_content.addLayout(left_panel)

        # -------- RIGHT: Controls + Plot --------
        right_layout = QVBoxLayout()

        # ===== Choose Group =====
        choose_group = QGroupBox("choose")
        choose_layout = QHBoxLayout(choose_group)
        choose_layout.setSpacing(8)

        self.radio_contribution = QRadioButton("contribution rate")
        self.radio_contribution.setChecked(True)
        choose_layout.addWidget(self.radio_contribution)

        self.contribution_spin = QDoubleSpinBox()
        self.contribution_spin.setRange(0.0, 1.0)
        self.contribution_spin.setSingleStep(0.01)
        self.contribution_spin.setValue(0.95)
        self.contribution_spin.setFixedWidth(90)
        self.contribution_spin.setMinimumHeight(32)
        choose_layout.addWidget(self.contribution_spin)

        self.radio_pc_num = QRadioButton("number of principal components")
        choose_layout.addWidget(self.radio_pc_num)

        self.pc_spin = QSpinBox()
        self.pc_spin.setRange(1, 50)
        self.pc_spin.setValue(1)
        self.pc_spin.setFixedWidth(90)
        self.pc_spin.setMinimumHeight(32)
        choose_layout.addWidget(self.pc_spin)

        choose_layout.addStretch()

        self.select_dim_btn = QPushButton("select dimension")
        self.select_dim_btn.setMinimumHeight(34)
        self.select_dim_btn.setMinimumWidth(140)
        choose_layout.addWidget(self.select_dim_btn)

        right_layout.addWidget(choose_group)

        # ===== Axis Selection & Buttons =====
        axis_layout = QHBoxLayout()
        axis_layout.setSpacing(8)

        axis_layout.addWidget(QLabel("X axis:"))
        self.x_axis_combo = QComboBox()
        self.x_axis_combo.addItems(["PC_1", "PC_2", "PC_3", "PC_4", "PC_5", "PC_6", 
                                    "PC_7", "PC_8", "PC_9", "PC_10"])
        self.x_axis_combo.setMinimumHeight(32)
        self.x_axis_combo.setMinimumWidth(90)
        axis_layout.addWidget(self.x_axis_combo)

        axis_layout.addWidget(QLabel("Y axis:"))
        self.y_axis_combo = QComboBox()
        self.y_axis_combo.addItems(["PC_1", "PC_2", "PC_3", "PC_4", "PC_5", "PC_6", 
                                    "PC_7", "PC_8", "PC_9", "PC_10"])
        self.y_axis_combo.setCurrentIndex(1)  # Default to PC_2
        self.y_axis_combo.setMinimumHeight(32)
        self.y_axis_combo.setMinimumWidth(90)
        axis_layout.addWidget(self.y_axis_combo)

        axis_layout.addSpacing(20)

        self.display_btn = QPushButton("display")
        self.display_btn.setMinimumHeight(34)
        self.display_btn.setMinimumWidth(92)
        axis_layout.addWidget(self.display_btn)

        self.diagram_3d_btn = QPushButton("3D diagram")
        self.diagram_3d_btn.setMinimumHeight(34)
        self.diagram_3d_btn.setMinimumWidth(92)
        axis_layout.addWidget(self.diagram_3d_btn)

        self.save_btn = QPushButton("save score matrix")
        self.save_btn.setMinimumHeight(34)
        self.save_btn.setMinimumWidth(140)
        axis_layout.addWidget(self.save_btn)
        
        # PLSR-specific buttons (hidden by default)
        self.plot_predictions_btn = QPushButton("Plot Predictions")
        self.plot_predictions_btn.setMinimumHeight(34)
        self.plot_predictions_btn.setMinimumWidth(130)
        axis_layout.addWidget(self.plot_predictions_btn)
        
        self.plot_coefficients_btn = QPushButton("Plot Coefficients")
        self.plot_coefficients_btn.setMinimumHeight(34)
        self.plot_coefficients_btn.setMinimumWidth(130)
        axis_layout.addWidget(self.plot_coefficients_btn)
        
        self.plot_component_selection_btn = QPushButton("Plot Component Selection")
        self.plot_component_selection_btn.setMinimumHeight(34)
        self.plot_component_selection_btn.setMinimumWidth(170)
        axis_layout.addWidget(self.plot_component_selection_btn)
        
        axis_layout.addSpacing(30)
        
        # Multi-select outlier removal button
        self.select_outliers_btn = QPushButton("Select Outliers")
        self.select_outliers_btn.setMinimumHeight(34)
        self.select_outliers_btn.setMinimumWidth(130)
        self.select_outliers_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        axis_layout.addWidget(self.select_outliers_btn)

        axis_layout.addStretch()
        right_layout.addLayout(axis_layout)

        # ===== Plot =====
        self.score_plot = PlotWidget(show_toolbar=True)
        self.score_plot.reset_axes(
            title="principal component score diagram",
            xlabel="PC_1",
            ylabel="PC_2"
        )
        self.score_plot.draw()

        right_layout.addWidget(self.score_plot, 1)

        main_content.addLayout(right_layout, 1)

        main_layout.addLayout(main_content)
    
    def on_dimension_reduction_clicked(self):
        """Perform PCA or PLSR analysis on preprocessed data"""
        # Check if preprocessed data is loaded
        if self.preprocessed_data is None:
            QMessageBox.warning(
                self,
                "No Data",
                "Please load preprocessed data first!\n\n"
                "Go to 'pre-treatment' tab, apply preprocessing algorithms, "
                "then return here to perform dimension reduction."
            )
            return
        
        algorithm = self.algorithm_combo.currentText()
        
        try:
            if algorithm == "PCA":
                self._perform_pca_analysis()
            elif algorithm == "PLSR":
                self._perform_plsr_analysis()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Analysis failed: {str(e)}")
    
    def _perform_pca_analysis(self):
        """Perform PCA analysis"""
        valid_mask = np.ones(self.preprocessed_data.shape[0], dtype=bool)
        for idx in self.excluded_indices:
            if 0 <= idx < len(valid_mask):
                valid_mask[idx] = False
        filtered_data = self.preprocessed_data[valid_mask]
        self.analysis_indices = np.flatnonzero(valid_mask).tolist()
        
        n_components = min(self.max_components_spin.value(), 
                          filtered_data.shape[0], 
                          filtered_data.shape[1])
        
        results = self.analyzer.perform_pca(filtered_data, n_components)
        
        self.current_results = results
        
        # Update info list with PC variance information
        self.info_list.clear()
        for i in range(n_components):
            var = results['explained_variance'][i] * 100
            cum_var = results['cumulative_variance'][i] * 100
            self.info_list.addItem(f"PC{i+1}: {var:.2f}% (Cumulative: {cum_var:.2f}%)")
        
        # Plot scores (PC1 vs PC2 by default)
        self.current_plot_mode = "pca_scores"
        self.current_plot_payload = {"pc_x": 0, "pc_y": 1 if n_components > 1 else 0}
        self._plot_pca_scores(0, 1 if n_components > 1 else 0)
        
        QMessageBox.information(
            self,
            "Success",
            f"PCA analysis completed!\n\n"
            f"Components extracted: {n_components}\n"
            f"Variance explained (PC1): {results['explained_variance'][0]*100:.2f}%\n"
            f"Cumulative variance: {results['cumulative_variance'][-1]*100:.2f}%"
        )
    
    def _perform_plsr_analysis(self):
        """Perform PLSR analysis"""
        # Check if target values are available
        if self.target_values is None or len(self.target_values) == 0:
            QMessageBox.warning(
                self,
                "No Target Values",
                "PLSR requires target values (Y variable).\n\n"
                "Please ensure your data includes property values for each sample."
            )
            return
        
        valid_mask = np.ones(len(self.target_values), dtype=bool)
        for idx in self.excluded_indices:
            if 0 <= idx < len(valid_mask):
                valid_mask[idx] = False
        for idx in self.validation_indices:
            if 0 <= idx < len(valid_mask):
                valid_mask[idx] = False
        
        filtered_data = self.preprocessed_data[valid_mask]
        filtered_targets = self.target_values[valid_mask]
        self.analysis_indices = np.flatnonzero(valid_mask).tolist()
        
        n_components = self.max_components_spin.value()
        cv_folds = self.cv_spin.value()
        optimize = self.optimize_check.isChecked()
        
        results = self.analyzer.perform_pls(
            filtered_data, 
            filtered_targets,
            n_components=n_components,
            cv=cv_folds,
            optimize=optimize
        )

        validation_points = []
        for idx in self.validation_indices:
            if 0 <= idx < len(self.target_values):
                validation_points.append({
                    'index': idx,
                    'actual': float(self.target_values[idx]),
                    'predicted': float(self.analyzer.predict(self.preprocessed_data[idx:idx + 1])[0])
                })

        external_validation = self.validation_data or {}
        validation_spectra = external_validation.get('spectra')
        validation_targets = external_validation.get('targets')
        if validation_spectra is not None and validation_targets is not None and len(validation_targets) > 0:
            validation_predictions = self.analyzer.predict(validation_spectra)
            for idx, (actual, predicted) in enumerate(zip(validation_targets, validation_predictions)):
                validation_points.append({
                    'index': idx,
                    'actual': float(actual),
                    'predicted': float(predicted),
                    'external': True
                })

        if validation_points:
            y_val_actual = np.array([point['actual'] for point in validation_points])
            y_val_pred = np.array([point['predicted'] for point in validation_points])
            results['validation_points'] = validation_points
            results['rmse_validation'] = float(np.sqrt(np.mean((y_val_actual - y_val_pred) ** 2)))
            results['r2_validation'] = (
                float(np.corrcoef(y_val_actual, y_val_pred)[0, 1] ** 2)
                if len(y_val_actual) > 1 and np.std(y_val_actual) > 0 and np.std(y_val_pred) > 0
                else None
            )
        else:
            results['validation_points'] = []
            results['rmse_validation'] = None
            results['r2_validation'] = None
        
        self.current_results = results
        
        self._populate_plsr_info_list(results, filtered_targets)
        
        # Plot predictions vs actual
        self.current_plot_mode = "plsr_predictions"
        self.current_plot_payload = {}
        self._plot_plsr_predictions(results)

        message = (
            f"PLSR analysis completed!\n\n"
            f"Optimal components: {results['best_n_components']}\n"
            f"Calibration R²: {results['r2_train']:.4f}\n"
            f"Cross-validation R²: {results['r2_cv']:.4f}\n"
            f"RMSECV: {results['rmse_cv']:.4f}"
        )
        if results['validation_points']:
            message += (
                f"\nValidation samples: {len(results['validation_points'])}\n"
                f"Validation RMSE: {results['rmse_validation']:.4f}"
            )
            if results['r2_validation'] is not None:
                message += f"\nValidation R²: {results['r2_validation']:.4f}"
        QMessageBox.information(self, "Success", message)
        return
        
        QMessageBox.information(
            self,
            "Success",
            f"PLSR analysis completed!\n\n"
            f"Optimal components: {results['best_n_components']}\n"
            f"Calibration R²: {results['r2_train']:.4f}\n"
            f"Cross-validation R²: {results['r2_cv']:.4f}\n"
            f"RMSECV: {results['rmse_cv']:.4f}"
        )
    
    def _reset_plot_canvas(self):
        """Clear shared plot state so each button shows an isolated graph."""
        for extra_ax in list(self.score_plot.figure.axes)[1:]:
            try:
                self.score_plot.figure.delaxes(extra_ax)
            except Exception:
                pass
        self.score_plot.clear()
        self._secondary_axis = None
        self._mpl_pick_map = {}
        self.score_plot.ax.grid(True, alpha=0.3)

        if self.tooltip_text is not None:
            try:
                self.tooltip_text.remove()
            except Exception:
                pass
            self.tooltip_text = None

        if self._mpl_pick_connection is None:
            self._mpl_pick_connection = self.score_plot.canvas.mpl_connect("pick_event", self._on_mpl_pick)
        if self._mpl_hover_connection is None:
            self._mpl_hover_connection = self.score_plot.canvas.mpl_connect("motion_notify_event", self._on_mpl_motion)

    def _register_pick_artist(self, artist, metadata):
        self._mpl_pick_map[artist] = metadata

    def _point_style(self, sample_index, default_color='blue'):
        if sample_index in self.selected_points:
            return '#ff9800', '#ff8c00', 90
        if default_color == 'red':
            return '#ef4444', '#b91c1c', 60
        if default_color == 'green':
            return '#22c55e', '#166534', 85
        if default_color == 'gray':
            return '#9ca3af', '#dc2626', 60
        return '#2563eb', '#1d4ed8', 70

    def _on_mpl_pick(self, event):
        metadata = self._mpl_pick_map.get(event.artist)
        if not metadata or not getattr(event, "ind", None):
            return
        point_index = int(event.ind[0])
        if point_index >= len(metadata):
            return
        sample_index = metadata[point_index].get('index', -1)
        if sample_index < 0:
            return
        self._handle_sample_point_clicked(sample_index)

    def _on_mpl_motion(self, event):
        if event.inaxes is None or not self._mpl_pick_map:
            if self.tooltip_text is not None:
                self.tooltip_text.set_visible(False)
                self.score_plot.canvas.draw_idle()
            return

        for artist, metadata in self._mpl_pick_map.items():
            contains, info = artist.contains(event)
            if not contains:
                continue
            indices = info.get("ind") or []
            if not indices:
                continue
            point_index = int(indices[0])
            if point_index >= len(metadata):
                continue
            tooltip = metadata[point_index].get("tooltip")
            if not tooltip:
                continue
            if self.tooltip_text is None:
                self.tooltip_text = event.inaxes.annotate(
                    "",
                    xy=(0, 0),
                    xytext=(10, 10),
                    textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.4", fc="#fff7cc", alpha=0.95),
                    fontsize=9
                )
            self.tooltip_text.xy = (event.xdata, event.ydata)
            self.tooltip_text.set_text(tooltip)
            self.tooltip_text.set_visible(True)
            self.score_plot.canvas.draw_idle()
            return

        if self.tooltip_text is not None and self.tooltip_text.get_visible():
            self.tooltip_text.set_visible(False)
            self.score_plot.canvas.draw_idle()

    def _handle_sample_point_clicked(self, sample_index):
        """Handle point click - either add to selection or show context menu."""
        if self.selection_mode:
            self._toggle_point_selection(sample_index)
            return

        sample_name = 'Unknown'
        if sample_index < len(self.sample_metadata):
            sample_name = self.sample_metadata[sample_index].get('sample_name', 'Unknown')

        menu = QMenu()
        menu.setStyleSheet("QMenu { font-size: 10pt; }")
        validation_action = None
        if self.algorithm_combo.currentText() == "PLSR":
            validation_action = menu.addAction(f"Set '{sample_name}' as Validation")
        invalidation_action = menu.addAction(f"Set '{sample_name}' as Outlier (Remove)")
        action = menu.exec(QCursor.pos())

        if validation_action is not None and action == validation_action:
            self._set_as_validation(sample_index)
        elif action == invalidation_action:
            self._set_as_invalid(sample_index)

    def _plot_pca_scores(self, pc_x, pc_y):
        """Plot PCA scores"""
        if self.current_results is None or 'scores' not in self.current_results:
            return
        
        scores = self.current_results['scores']
        n_components = scores.shape[1]
        if pc_x >= n_components or pc_y >= n_components:
            QMessageBox.warning(
                self,
                "Unavailable Component",
                f"This PCA result only has {n_components} component(s)."
            )
            return
        
        self._reset_plot_canvas()
        self.current_plot_mode = "pca_scores"
        self.current_plot_payload = {"pc_x": pc_x, "pc_y": pc_y}
        self.score_plot.reset_axes(
            title="PCA Score Plot",
            xlabel=f"PC{pc_x+1}",
            ylabel=f"PC{pc_y+1}"
        )

        x_vals = []
        y_vals = []
        metadata = []
        for row_idx in range(scores.shape[0]):
            sample_index = self.analysis_indices[row_idx] if row_idx < len(self.analysis_indices) else row_idx
            sample_name = self._get_sample_name(sample_index)
            tooltip = (
                f"{sample_name}\n"
                f"PC{pc_x+1}: {scores[row_idx, pc_x]:.4f}\n"
                f"PC{pc_y+1}: {scores[row_idx, pc_y]:.4f}"
            )
            x_vals.append(scores[row_idx, pc_x])
            y_vals.append(scores[row_idx, pc_y])
            metadata.append({'tooltip': tooltip, 'index': sample_index})

        colors = [self._point_style(meta['index'], 'blue')[0] for meta in metadata]
        edges = [self._point_style(meta['index'], 'blue')[1] for meta in metadata]
        sizes = [self._point_style(meta['index'], 'blue')[2] for meta in metadata]
        scatter = self.score_plot.ax.scatter(x_vals, y_vals, c=colors, edgecolors=edges, s=sizes, alpha=0.8, picker=True)
        self._register_pick_artist(scatter, metadata)
        self.score_plot.draw()
    
    def _plot_plsr_predictions(self, results):
        """Plot PLSR predicted vs actual with hover tooltips"""
        self._reset_plot_canvas()
        force_base_view = self.current_plot_payload.get("force_base_view", False)
        self.current_plot_mode = "plsr_predictions"
        self.current_plot_payload = {"force_base_view": force_base_view}
        self.score_plot.reset_axes(
            title="PLSR: Predicted vs Actual",
            xlabel="Actual",
            ylabel="Predicted"
        )
        
        cal_x = []
        cal_y = []
        cal_meta = []
        for row_idx, i in enumerate(self.analysis_indices):
            if i in self.validation_indices:
                continue
            if i < len(self.sample_metadata):
                sample_name = self.sample_metadata[i].get('sample_name', f'Sample {i+1}')
                property_val = self.sample_metadata[i].get('property_value', '')
                property_name = self.sample_metadata[i].get('property_name', 'Value')
            else:
                sample_name = f'Sample {i+1}'
                property_val = self.target_values[i]
                property_name = 'Value'
            tooltip = f"{sample_name}\n{property_name}: {property_val}"
            cal_x.append(self.target_values[i])
            cal_y.append(results['y_pred_train'][row_idx])
            cal_meta.append({'tooltip': tooltip, 'index': i})

        cv_x = []
        cv_y = []
        cv_meta = []
        for row_idx, i in enumerate(self.analysis_indices):
            if i in self.validation_indices:
                continue
            if i < len(self.sample_metadata):
                sample_name = self.sample_metadata[i].get('sample_name', f'Sample {i+1}')
                property_val = self.sample_metadata[i].get('property_value', '')
                property_name = self.sample_metadata[i].get('property_name', 'Value')
            else:
                sample_name = f'Sample {i+1}'
                property_val = self.target_values[i]
                property_name = 'Value'
            tooltip = f"{sample_name} (CV)\n{property_name}: {property_val}"
            cv_x.append(self.target_values[i])
            cv_y.append(results['y_pred_cv'][row_idx])
            cv_meta.append({'tooltip': tooltip, 'index': i})

        validation_x = []
        validation_y = []
        validation_meta = []
        for point in results.get('validation_points', []):
            i = point['index']
            point_meta = None
            if point.get('external'):
                validation_meta = (self.validation_data or {}).get('metadata', [])
                if i < len(validation_meta):
                    point_meta = validation_meta[i]
            elif i < len(self.sample_metadata):
                point_meta = self.sample_metadata[i]

            if point_meta is not None:
                sample_name = point_meta.get('sample_name', f'Sample {i+1}')
                property_val = point_meta.get('property_value', '')
                property_name = point_meta.get('property_name', 'Value')
            else:
                sample_name = f'Sample {i+1}'
                property_val = point['actual']
                property_name = 'Value'

            tooltip = f"{sample_name} (Validation)\n{property_name}: {property_val}"
            validation_x.append(point['actual'])
            validation_y.append(point['predicted'])
            validation_meta.append({'tooltip': tooltip, 'index': i})

        if cal_x:
            scatter_cal = self.score_plot.ax.scatter(cal_x, cal_y, c='#2563eb', edgecolors='#1d4ed8', s=70, alpha=0.8, label='Calibration', picker=True)
            self._register_pick_artist(scatter_cal, cal_meta)
        if cv_x:
            scatter_cv = self.score_plot.ax.scatter(cv_x, cv_y, c='#ef4444', edgecolors='#b91c1c', s=55, alpha=0.7, label='Cross-validation', picker=True)
            self._register_pick_artist(scatter_cv, cv_meta)
        if validation_x:
            scatter_validation = self.score_plot.ax.scatter(validation_x, validation_y, c='#22c55e', edgecolors='#166534', marker='^', s=85, alpha=0.8, label='Validation', picker=True)
            self._register_pick_artist(scatter_validation, validation_meta)
        
        # Add 1:1 line
        active_targets = self.target_values[self.analysis_indices]
        y_min = min(active_targets.min(), results['y_pred_train'].min())
        y_max = max(active_targets.max(), results['y_pred_train'].max())
        self.score_plot.ax.plot([y_min, y_max], [y_min, y_max], color='black', linewidth=2, linestyle='--')
        self.score_plot.ax.legend(loc='best')
        self.score_plot.draw()
    
    def _set_as_validation(self, sample_index):
        """Move sample to validation set"""
        if sample_index in self.validation_indices:
            QMessageBox.information(self, "Info", "This sample is already in the validation set.")
            return
        
        # Add to validation set
        self.validation_indices.append(sample_index)
        
        sample_name = 'Unknown'
        if sample_index < len(self.sample_metadata):
            sample_name = self.sample_metadata[sample_index].get('sample_name', 'Unknown')
        
        QMessageBox.information(
            self, 
            "Validation Set", 
            f"Sample '{sample_name}' moved to validation set.\n\n"
            f"Point removed from plot."
        )
        
        # Refresh plot to remove validation point
        if self.current_results is not None:
            self._refresh_current_plot()
    
    def _set_as_invalid(self, sample_index):
        """Mark sample as invalid and remove from analysis"""
        if sample_index in self.excluded_indices:
            QMessageBox.information(self, "Info", "This sample is already marked as invalid.")
            return
        
        sample_name = 'Unknown'
        if sample_index < len(self.sample_metadata):
            sample_name = self.sample_metadata[sample_index].get('sample_name', 'Unknown')
        
        # Confirm removal
        reply = QMessageBox.question(
            self,
            "Remove Sample",
            f"Mark '{sample_name}' as invalid and exclude from analysis?\n\n"
            f"This will remove the point and re-run the current analysis.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Add to excluded indices
            self.excluded_indices.append(sample_index)
            
            # Remove from validation if it was there
            if sample_index in self.validation_indices:
                self.validation_indices.remove(sample_index)
            
            # Re-run analysis with excluded samples
            self._rerun_analysis_with_exclusions()
    
    def on_select_outliers_clicked(self):
        """Toggle outlier selection mode"""
        if self.current_results is None:
            QMessageBox.warning(
                self,
                "No Plot",
                "Run PCA or PLSR first, then select the points you want to remove."
            )
            return
        
        if not self.selection_mode:
            # Enter selection mode
            self.selection_mode = True
            self.selected_points = []
            self.select_outliers_btn.setText("Done Selecting")
            self.select_outliers_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff9800;
                    color: white;
                    font-weight: bold;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #e68900;
                }
                QPushButton:pressed {
                    background-color: #cc7a00;
                }
            """)
            QMessageBox.information(
                self,
                "Selection Mode",
                "Click on points in the plot to select them.\n"
                "Selected points will be highlighted in orange.\n\n"
                "Click 'Done Selecting' when finished."
            )
        else:
            # Exit selection mode and process selected points
            self._process_selected_points()
    
    def _toggle_point_selection(self, sample_index):
        """Add or remove point from selection"""
        if sample_index in self.selected_points:
            self.selected_points = [idx for idx in self.selected_points if idx != sample_index]
        else:
            self.selected_points.append(sample_index)
        
        self._refresh_current_plot()
    
    def _process_selected_points(self):
        """Show dialog and process selected outliers"""
        if len(self.selected_points) == 0:
            QMessageBox.warning(
                self,
                "No Selection",
                "No points were selected.\n\nSelection mode cancelled."
            )
            self._exit_selection_mode()
            return
        
        # Show choice dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Process Selected Outliers")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Add description
        count = len(self.selected_points)
        desc_label = QLabel(f"You have selected {count} point(s).\n\nChoose an action:")
        desc_label.setStyleSheet("font-size: 11pt; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Radio buttons for options
        validation_radio = None
        if self.algorithm_combo.currentText() == "PLSR":
            validation_radio = QRadioButton("Move to Validation Set")
            validation_radio.setStyleSheet("font-size: 10pt; margin: 5px;")
            layout.addWidget(validation_radio)
        
        invalid_radio = QRadioButton("Mark as Outliers and Remove")
        invalid_radio.setChecked(True)
        invalid_radio.setStyleSheet("font-size: 10pt; margin: 5px;")
        layout.addWidget(invalid_radio)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Execute dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if validation_radio is not None and validation_radio.isChecked():
                self._batch_set_as_validation()
            else:
                self._batch_set_as_invalid()
        
        self._exit_selection_mode()
    
    def _exit_selection_mode(self):
        """Exit selection mode and reset UI"""
        self.selection_mode = False
        self.selected_points = []
        self.select_outliers_btn.setText("Select Outliers")
        self.select_outliers_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        # Refresh plot to remove orange highlighting
        if self.current_results is not None:
            self._refresh_current_plot()
    
    def _batch_set_as_validation(self):
        """Move all selected points to validation set"""
        added_count = 0
        for sample_index in self.selected_points:
            if sample_index not in self.validation_indices:
                self.validation_indices.append(sample_index)
                added_count += 1
        
        QMessageBox.information(
            self,
            "Validation Set",
            f"Moved {added_count} sample(s) to validation set.\n\n"
            f"Points removed from plot."
        )
        
        # Refresh plot to remove validation points
        if self.current_results is not None:
            self._refresh_current_plot()
    
    def _batch_set_as_invalid(self):
        """Mark all selected points as invalid and exclude from analysis"""
        # Confirm removal
        count = len(self.selected_points)
        reply = QMessageBox.question(
            self,
            "Remove Samples",
            f"Mark {count} sample(s) as invalid and exclude from analysis?\n\n"
            f"This will remove the points and re-run the current analysis.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Add all to excluded indices
            for sample_index in self.selected_points:
                if sample_index not in self.excluded_indices:
                    self.excluded_indices.append(sample_index)
                # Remove from validation if it was there
                if sample_index in self.validation_indices:
                    self.validation_indices.remove(sample_index)
            
            # Re-run analysis with excluded samples
            self._rerun_analysis_with_exclusions()
    
    def _rerun_analysis_with_exclusions(self):
        """Re-run current analysis excluding marked samples"""
        if self.preprocessed_data is None:
            return
        
        # Create mask for valid samples (not excluded)
        valid_mask = np.ones(self.preprocessed_data.shape[0], dtype=bool)
        for idx in self.excluded_indices:
            if 0 <= idx < len(valid_mask):
                valid_mask[idx] = False
        
        # Filter data
        filtered_data = self.preprocessed_data[valid_mask]
        self.analysis_indices = np.flatnonzero(valid_mask).tolist()
        
        if len(filtered_data) < 5:
            QMessageBox.warning(
                self,
                "Insufficient Data",
                "Not enough samples remaining for analysis.\n"
                "At least 5 samples are required."
            )
            return
        
        # Re-run current algorithm with filtered data
        n_components = self.max_components_spin.value()
        cv_folds = self.cv_spin.value()
        optimize = self.optimize_check.isChecked()
        algorithm = self.algorithm_combo.currentText()
        
        try:
            if algorithm == "PCA":
                n_components = min(n_components, filtered_data.shape[0], filtered_data.shape[1])
                results = self.analyzer.perform_pca(filtered_data, n_components)
            else:
                filtered_targets = self.target_values[valid_mask]
                results = self.analyzer.perform_pls(
                    filtered_data,
                    filtered_targets,
                    n_components=n_components,
                    cv=cv_folds,
                    optimize=optimize
                )
            
            self.current_results = results
            
            self.info_list.clear()
            if algorithm == "PCA":
                for i in range(n_components):
                    var = results['explained_variance'][i] * 100
                    cum_var = results['cumulative_variance'][i] * 100
                    self.info_list.addItem(f"PC{i+1}: {var:.2f}% (Cumulative: {cum_var:.2f}%)")
                
                self.info_list.addItem("")
                self.info_list.addItem(f"Excluded samples: {len(self.excluded_indices)}")
                self._plot_pca_scores(0, 1 if n_components > 1 else 0)
                QMessageBox.information(
                    self,
                    "Analysis Updated",
                    f"PCA re-run with {len(filtered_data)} samples.\n\n"
                    f"Excluded: {len(self.excluded_indices)} samples"
                )
                return
            else:
                self._populate_plsr_info_list(results, filtered_targets)
                self.info_list.addItem("")
                self.info_list.addItem(f"Excluded samples: {len(self.excluded_indices)}")
                self._plot_plsr_predictions_with_exclusions(results, valid_mask)
                QMessageBox.information(
                    self,
                    "Analysis Updated",
                    f"PLSR re-run with {len(filtered_data)} samples.\n\n"
                    f"Excluded: {len(self.excluded_indices)} samples\n"
                    f"R2: {results['r2_cv']:.4f}"
                )
                return
            
            QMessageBox.information(
                self,
                "Analysis Updated",
                f"PLSR re-run with {len(filtered_data)} samples.\n\n"
                f"Excluded: {len(self.excluded_indices)} samples\n"
                f"R²: {results['r2_cv']:.4f}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to re-run analysis: {str(e)}")

    def _populate_plsr_info_list(self, results, filtered_targets):
        """Show PLSR settings, component iterations, and per-fold CV rows clearly."""
        self.info_list.clear()
        self.component_table.setRowCount(0)
        self.fold_table.setRowCount(0)

        optimize_enabled = results.get('optimized', True)
        max_tested = results.get('max_components_tested', results.get('best_n_components', ''))
        iteration_count = results.get('optimization_iterations', 0)
        best_components = results.get('best_n_components', '')
        cv_folds = results.get('cv_folds', '')

        self.info_list.addItem("PLSR Regression Summary")
        self.info_list.addItem(f"Samples: {results.get('n_samples', 0)}")
        self.info_list.addItem(f"CV folds: {cv_folds}")
        self.info_list.addItem(f"Optimization: {'On' if optimize_enabled else 'Off'}")
        if optimize_enabled:
            self.info_list.addItem(f"Max components to test: {max_tested}")
            self.info_list.addItem(f"Iterations run: {iteration_count}")
        else:
            self.info_list.addItem(f"Fixed components requested: {max_tested}")
            self.info_list.addItem(f"Iterations run: {iteration_count}")
        self.info_list.addItem(f"Optimal components selected: {best_components}")
        self.info_list.addItem(
            f"Overall CV: R2={results.get('r2_cv', 0.0):.4f}, RMSE={results.get('rmse_cv', 0.0):.4f}"
        )
        self.info_list.addItem(
            f"Calibration: R2={results.get('r2_train', 0.0):.4f}, RMSE={results.get('rmse_train', 0.0):.4f}"
        )

        if len(filtered_targets) > 0:
            self.info_list.addItem(
                f"Target stats: min={filtered_targets.min():.4f}, max={filtered_targets.max():.4f}, unique={len(np.unique(np.round(filtered_targets, 8)))}"
            )

        component_metrics = results.get('component_metrics') or []
        if component_metrics:
            self.component_table.setRowCount(len(component_metrics))
            for row, metric in enumerate(component_metrics):
                component = metric.get('component', '')
                component_item = QTableWidgetItem(str(component))
                if component == best_components:
                    component_item.setBackground(Qt.GlobalColor.yellow)
                self.component_table.setItem(row, 0, component_item)
                self.component_table.setItem(row, 1, QTableWidgetItem(f"{metric.get('r2_cv', 0.0):.4f}"))
                self.component_table.setItem(row, 2, QTableWidgetItem(f"{metric.get('rmse_cv', 0.0):.4f}"))
            self.component_table.resizeRowsToContents()

        fold_metrics = results.get('fold_metrics') or []
        if fold_metrics:
            self.fold_table.setRowCount(len(fold_metrics))
            for row, metric in enumerate(fold_metrics):
                fold_r2 = metric.get('r2')
                r2_text = "nan" if fold_r2 is None or np.isnan(fold_r2) else f"{fold_r2:.4f}"
                self.fold_table.setItem(row, 0, QTableWidgetItem(str(metric.get('fold', ''))))
                self.fold_table.setItem(row, 1, QTableWidgetItem(r2_text))
                self.fold_table.setItem(row, 2, QTableWidgetItem(f"{metric.get('rmse', 0.0):.4f}"))
                self.fold_table.setItem(row, 3, QTableWidgetItem(str(metric.get('n_samples', 0))))
            self.fold_table.resizeRowsToContents()
    
    def _plot_plsr_predictions_with_exclusions(self, results, valid_mask):
        """Plot PLSR predictions showing excluded points differently"""
        self._reset_plot_canvas()
        self.current_plot_mode = "plsr_predictions_with_exclusions"
        self.current_plot_payload = {"valid_mask": valid_mask.copy()}
        self.score_plot.reset_axes(
            title="PLSR: Predicted vs Actual (with exclusions)",
            xlabel="Actual",
            ylabel="Predicted"
        )

        cal_x = []
        cal_y = []
        cal_meta = []
        for row_idx, i in enumerate(self.analysis_indices):
            if i in self.validation_indices:
                continue
            if i < len(self.sample_metadata):
                sample_name = self.sample_metadata[i].get('sample_name', f'Sample {i+1}')
                property_val = self.sample_metadata[i].get('property_value', '')
                property_name = self.sample_metadata[i].get('property_name', 'Value')
            else:
                sample_name = f'Sample {i+1}'
                property_val = self.target_values[i]
                property_name = 'Value'
            tooltip = f"{sample_name}\n{property_name}: {property_val}"
            cal_x.append(self.target_values[i])
            cal_y.append(results['y_pred_train'][row_idx])
            cal_meta.append({'tooltip': tooltip, 'index': i})

        cv_x = []
        cv_y = []
        cv_meta = []
        for row_idx, i in enumerate(self.analysis_indices):
            if i in self.validation_indices:
                continue
            if i < len(self.sample_metadata):
                sample_name = self.sample_metadata[i].get('sample_name', f'Sample {i+1}')
                property_val = self.sample_metadata[i].get('property_value', '')
                property_name = self.sample_metadata[i].get('property_name', 'Value')
            else:
                sample_name = f'Sample {i+1}'
                property_val = self.target_values[i]
                property_name = 'Value'
            tooltip = f"{sample_name} (CV)\n{property_name}: {property_val}"
            cv_x.append(self.target_values[i])
            cv_y.append(results['y_pred_cv'][row_idx])
            cv_meta.append({'tooltip': tooltip, 'index': i})

        excluded_x = []
        excluded_y = []
        excluded_meta = []
        for i in self.excluded_indices:
            if i >= len(self.target_values):
                continue
            if i < len(self.sample_metadata):
                sample_name = self.sample_metadata[i].get('sample_name', f'Sample {i+1}')
                property_val = self.sample_metadata[i].get('property_value', '')
                property_name = self.sample_metadata[i].get('property_name', 'Value')
            else:
                sample_name = f'Sample {i+1}'
                property_val = self.target_values[i]
                property_name = 'Value'
            tooltip = f"{sample_name} (EXCLUDED)\n{property_name}: {property_val}"
            excluded_x.append(self.target_values[i])
            excluded_y.append(self.target_values[i])
            excluded_meta.append({'tooltip': tooltip, 'index': i})

        if cal_x:
            scatter_cal = self.score_plot.ax.scatter(cal_x, cal_y, c='#2563eb', edgecolors='#1d4ed8', s=70, alpha=0.8, label='Calibration', picker=True)
            self._register_pick_artist(scatter_cal, cal_meta)
        if cv_x:
            scatter_cv = self.score_plot.ax.scatter(cv_x, cv_y, c='#ef4444', edgecolors='#b91c1c', s=55, alpha=0.7, label='Cross-validation', picker=True)
            self._register_pick_artist(scatter_cv, cv_meta)
        if excluded_x:
            scatter_excluded = self.score_plot.ax.scatter(excluded_x, excluded_y, c='#9ca3af', edgecolors='#dc2626', marker='x', s=65, alpha=0.8, label='Excluded', picker=True)
            self._register_pick_artist(scatter_excluded, excluded_meta)
        
        # Add 1:1 line
        active_targets = self.target_values[self.analysis_indices]
        y_min = min(active_targets.min(), results['y_pred_train'].min())
        y_max = max(active_targets.max(), results['y_pred_train'].max())
        self.score_plot.ax.plot([y_min, y_max], [y_min, y_max], color='black', linewidth=2, linestyle='--')
        self.score_plot.ax.legend(loc='best')
        self.score_plot.draw()
    
    def on_select_dimension_clicked(self):
        """Select dimensions based on contribution rate or PC number"""
        if self.current_results is None:
            QMessageBox.warning(self, "Warning", "Please perform analysis first!")
            return
        
        if self.radio_contribution.isChecked():
            # Select by contribution rate
            target_var = self.contribution_spin.value()
            cum_var = self.current_results.get('cumulative_variance', [])
            
            selected = 0
            for i, cv in enumerate(cum_var):
                if cv >= target_var:
                    selected = i + 1
                    break
            
            if selected == 0:
                selected = len(cum_var)
            
            QMessageBox.information(
                self,
                "Selection",
                f"Selected {selected} components to achieve {target_var*100:.1f}% variance"
            )
        else:
            # Select by PC number
            selected = self.pc_spin.value()
            QMessageBox.information(
                self,
                "Selection",
                f"Selected {selected} principal components"
            )
    
    def on_display_clicked(self):
        """Display selected PC axes"""
        if self.current_results is None:
            QMessageBox.warning(self, "Warning", "Please perform analysis first!")
            return
        
        if 'scores' not in self.current_results:
            return
        
        # Get selected axes
        x_text = self.x_axis_combo.currentText()
        y_text = self.y_axis_combo.currentText()
        
        # Extract PC numbers
        pc_x = int(x_text.split('_')[1]) - 1
        pc_y = int(y_text.split('_')[1]) - 1

        self.current_plot_mode = "pca_scores"
        self.current_plot_payload = {"pc_x": pc_x, "pc_y": pc_y}
        self._plot_pca_scores(pc_x, pc_y)
    
    def on_3d_diagram_clicked(self):
        """Display a 3D PCA score plot when available"""
        if self.algorithm_combo.currentText() != "PCA":
            QMessageBox.information(self, "3D Plot", "3D plotting is available for PCA only.")
            return
        
        if self.current_results is None or 'scores' not in self.current_results:
            QMessageBox.warning(self, "3D Plot", "Run PCA first to open the 3D score plot.")
            return
        
        scores = self.current_results['scores']
        if scores.shape[1] < 3:
            QMessageBox.information(
                self,
                "3D Plot",
                "At least 3 principal components are required to display a 3D score plot."
            )
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("PCA 3D Score Plot")
        dialog.resize(900, 700)
        layout = QVBoxLayout(dialog)
        
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
        
        figure = Figure(figsize=(8, 6), tight_layout=True)
        canvas = FigureCanvas(figure)
        layout.addWidget(canvas)
        
        ax = figure.add_subplot(111, projection='3d')
        x_vals = scores[:, 0]
        y_vals = scores[:, 1]
        z_vals = scores[:, 2]
        colors = [
            '#ff9800' if sample_index in self.selected_points else '#1565c0'
            for sample_index in self.analysis_indices
        ]
        
        ax.scatter(x_vals, y_vals, z_vals, c=colors, s=45, depthshade=True)
        ax.set_xlabel('PC1')
        ax.set_ylabel('PC2')
        ax.set_zlabel('PC3')
        ax.set_title('PCA 3D Score Plot')
        ax.grid(True, alpha=0.3)
        canvas.draw()
        
        dialog.exec()
    
    def on_save_clicked(self):
        """Save analysis results"""
        if self.current_results is None:
            QMessageBox.warning(self, "Warning", "No results to save!")
            return
        
        try:
            # Create results directory
            base_dir = Path(__file__).parent.parent.parent
            results_dir = base_dir / 'analysis_results'
            results_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            algorithm = self.algorithm_combo.currentText()
            
            # Save results as JSON
            filename = f"{algorithm}_results_{timestamp}.json"
            filepath = results_dir / filename
            
            # Prepare data for serialization
            save_data = {}
            if algorithm == "PCA":
                save_data = {
                    'algorithm': 'PCA',
                    'timestamp': timestamp,
                    'n_components': self.current_results['n_components'],
                    'explained_variance': self.current_results['explained_variance'].tolist(),
                    'cumulative_variance': self.current_results['cumulative_variance'].tolist(),
                    'scores': self.current_results['scores'].tolist(),
                    'loadings': self.current_results['loadings'].tolist()
                }
            elif algorithm == "PLSR":
                save_data = {
                    'algorithm': 'PLSR',
                    'timestamp': timestamp,
                    'best_n_components': self.current_results['best_n_components'],
                    'r2_train': self.current_results['r2_train'],
                    'rmse_train': self.current_results['rmse_train'],
                    'r2_cv': self.current_results['r2_cv'],
                    'rmse_cv': self.current_results['rmse_cv'],
                    'coefficients': self.current_results['coefficients'].tolist(),
                    'intercept': self.current_results['intercept'],
                    'fold_metrics': self.current_results['fold_metrics']
                }
            
            with open(filepath, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            QMessageBox.information(
                self,
                "Success",
                f"Results saved to:\n{filepath}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save results: {str(e)}")
    
    def on_plot_predictions_clicked(self):
        """Plot PLSR predictions vs actual values"""
        if self.current_results is None or self.algorithm_combo.currentText() != "PLSR":
            QMessageBox.warning(self, "Warning", "No PLSR results available!\n\nPlease run PLSR analysis first.")
            return
        
        try:
            self.current_plot_mode = "plsr_predictions"
            self.current_plot_payload = {"force_base_view": True}
            self._plot_plsr_predictions(self.current_results)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to plot predictions: {str(e)}")
    
    def on_plot_coefficients_clicked(self):
        """Plot PLSR regression coefficients vs wavelengths"""
        if self.current_results is None or self.algorithm_combo.currentText() != "PLSR":
            QMessageBox.warning(self, "Warning", "No PLSR results available!\n\nPlease run PLSR analysis first.")
            return
        
        if self.wavelengths is None:
            QMessageBox.warning(self, "Warning", "Wavelength data not available!")
            return
        
        try:
            self._plot_coefficients()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to plot coefficients: {str(e)}")
    
    def on_plot_component_selection_clicked(self):
        """Plot component selection curve (R² and RMSE vs number of components)"""
        if self.current_results is None or self.algorithm_combo.currentText() != "PLSR":
            QMessageBox.warning(self, "Warning", "No PLSR results available!\n\nPlease run PLSR analysis first.")
            return
        
        if not self.current_results.get('cv_enabled', True):
            QMessageBox.information(
                self,
                "Information",
                "Cross-validation is disabled (CV folds = 0).\n\n"
                "Component selection curve is only available when CV is enabled."
            )
            return

        if not self.current_results.get('optimized', True):
            QMessageBox.information(
                self, 
                "Information", 
                "Component optimization was not performed.\n\n"
                "Enable 'Optimize components' checkbox before running PLSR to see the selection curve."
            )
            return
        
        try:
            self._plot_component_selection_curve()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to plot component selection: {str(e)}")
    
    def _plot_coefficients(self):
        """Plot regression coefficients vs wavelengths"""
        self._reset_plot_canvas()
        self.current_plot_mode = "plsr_coefficients"
        self.current_plot_payload = {}
        self.score_plot.reset_axes(
            title="PLSR: Regression Coefficients",
            xlabel="Wavelength (nm)",
            ylabel="Coefficient Value"
        )
        
        coefficients = self.current_results['coefficients']
        wavelengths = self.wavelengths
        if wavelengths is None or len(wavelengths) != len(coefficients):
            wavelengths = np.arange(1, len(coefficients) + 1)
            self.score_plot.ax.set_xlabel("Variable Index")

        self.score_plot.ax.plot(
            wavelengths,
            coefficients,
            color='#1d4ed8',
            linewidth=2.4,
            zorder=3
        )
        self.score_plot.ax.fill_between(
            wavelengths,
            0,
            coefficients,
            where=coefficients >= 0,
            color='#93c5fd',
            alpha=0.25,
            zorder=2
        )
        self.score_plot.ax.fill_between(
            wavelengths,
            0,
            coefficients,
            where=coefficients < 0,
            color='#bfdbfe',
            alpha=0.18,
            zorder=2
        )
        self.score_plot.ax.axhline(0, color='black', linewidth=1, linestyle='--', zorder=1)
        self.score_plot.ax.margins(x=0.02, y=0.08)
        self.score_plot.draw()
    
    def _plot_component_selection_curve(self):
        """Plot R² and RMSE vs number of components with dual y-axes"""
        self._reset_plot_canvas()
        self.current_plot_mode = "plsr_component_selection"
        self.current_plot_payload = {}
        self.score_plot.reset_axes(
            title="Component Selection: CV Performance",
            xlabel="Number of Components",
            ylabel="R² (CV)"
        )
        
        r2_scores = self.current_results['r2_scores']
        rmse_scores = self.current_results['rmse_scores']
        n_components = list(range(1, len(r2_scores) + 1))
        self._secondary_axis = self.score_plot.ax.twinx()
        self._secondary_axis.set_ylabel("RMSE (CV)")
        self._secondary_axis.grid(False)
        self.score_plot.ax.plot(n_components, r2_scores, color='#2563eb', linewidth=2, marker='o', label='R² (CV)')
        self._secondary_axis.plot(n_components, rmse_scores, color='#dc2626', linewidth=2, marker='s', label='RMSE (CV)')

        best_n = self.current_results['best_n_components']
        self.score_plot.ax.axvline(best_n, color='#166534', linewidth=2, linestyle='--')
        self.score_plot.ax.annotate(
            f'Optimal: {best_n} components',
            xy=(best_n, max(r2_scores)),
            xytext=(8, 8),
            textcoords='offset points',
            color='#166534',
            fontsize=9,
            fontweight='bold'
        )
        self.score_plot.draw()
    
    def load_preprocessed_data(self, spectra: np.ndarray, wavelengths: np.ndarray = None, 
                              target_values: np.ndarray = None, sample_metadata: list = None,
                              validation_spectra: np.ndarray = None, validation_targets: np.ndarray = None,
                              validation_metadata: list = None):
        """
        Load preprocessed data from pre-treatment tab
        
        Args:
            spectra: Preprocessed spectral data (n_samples x n_wavelengths)
            wavelengths: Wavelength array (optional)
            target_values: Target values for PLSR (optional)
            sample_metadata: List of dicts with sample info (optional)
        """
        same_dataset = self._is_same_loaded_dataset(
            spectra,
            target_values,
            sample_metadata,
            validation_spectra,
            validation_targets,
            validation_metadata
        )

        self.preprocessed_data = spectra
        self.wavelengths = wavelengths
        self.target_values = target_values
        self.sample_metadata = sample_metadata if sample_metadata else []
        self.validation_data = {
            'spectra': validation_spectra,
            'targets': validation_targets,
            'metadata': validation_metadata if validation_metadata else []
        }
        if same_dataset:
            self.analysis_indices = [
                idx for idx in range(spectra.shape[0])
                if idx not in self.excluded_indices and idx not in self.validation_indices
            ]
        else:
            self.excluded_indices = []
            self.validation_indices = []
            self.current_results = None
            self.current_plot_mode = None
            self.current_plot_payload = {}
            self.selection_mode = False
            self.selected_points = []
            self.analysis_indices = list(range(spectra.shape[0]))
        

    def _is_same_loaded_dataset(
        self,
        spectra,
        target_values,
        sample_metadata,
        validation_spectra,
        validation_targets,
        validation_metadata
    ):
        """Detect a no-op reload so validation/exclusion selections survive tab switches."""
        if self.preprocessed_data is None:
            return False

        current_meta = self.sample_metadata or []
        next_meta = sample_metadata or []
        current_val_meta = (self.validation_data or {}).get('metadata', []) if self.validation_data else []
        next_val_meta = validation_metadata or []

        return (
            np.array_equal(self.preprocessed_data, spectra)
            and np.array_equal(self.target_values, target_values)
            and current_meta == next_meta
            and np.array_equal((self.validation_data or {}).get('spectra'), validation_spectra)
            and np.array_equal((self.validation_data or {}).get('targets'), validation_targets)
            and current_val_meta == next_val_meta
        )
    
    def _get_sample_name(self, sample_index):
        """Return the display name for a sample"""
        if 0 <= sample_index < len(self.sample_metadata):
            return self.sample_metadata[sample_index].get('sample_name', f'Sample {sample_index + 1}')
        return f'Sample {sample_index + 1}'
    
    def _refresh_current_plot(self):
        """Redraw the current chart so selection state stays visible"""
        if self.current_results is None:
            return

        if self.current_plot_mode == "pca_scores" and 'scores' in self.current_results:
            pc_x = self.current_plot_payload.get("pc_x", 0)
            pc_y = self.current_plot_payload.get("pc_y", 1)
            self._plot_pca_scores(pc_x, pc_y)
        elif self.current_plot_mode == "plsr_coefficients":
            self._plot_coefficients()
        elif self.current_plot_mode == "plsr_component_selection":
            self._plot_component_selection_curve()
        elif self.current_plot_mode == "plsr_predictions_with_exclusions":
            if self.current_plot_payload.get("force_base_view"):
                self._plot_plsr_predictions(self.current_results)
                return
            valid_mask = self.current_plot_payload.get("valid_mask")
            if valid_mask is None and self.target_values is not None:
                valid_mask = np.ones(len(self.target_values), dtype=bool)
                for idx in self.excluded_indices:
                    if 0 <= idx < len(valid_mask):
                        valid_mask[idx] = False
            if valid_mask is not None:
                self._plot_plsr_predictions_with_exclusions(self.current_results, valid_mask)
            else:
                self._plot_plsr_predictions(self.current_results)
        elif self.current_plot_mode == "plsr_predictions":
            if self.current_plot_payload.get("force_base_view"):
                self._plot_plsr_predictions(self.current_results)
                return
            if len(self.excluded_indices) > 0 and self.target_values is not None:
                valid_mask = np.ones(len(self.target_values), dtype=bool)
                for idx in self.excluded_indices:
                    if 0 <= idx < len(valid_mask):
                        valid_mask[idx] = False
                self._plot_plsr_predictions_with_exclusions(self.current_results, valid_mask)
            else:
                self._plot_plsr_predictions(self.current_results)
