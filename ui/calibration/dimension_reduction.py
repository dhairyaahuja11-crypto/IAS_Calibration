from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox, QRadioButton,
    QDoubleSpinBox, QSpinBox, QVBoxLayout, QHBoxLayout,
    QGroupBox, QMessageBox, QListWidget, QCheckBox, QMenu,
    QDialog, QDialogButtonBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
import pyqtgraph as pg
import numpy as np
from services.chemometric_service import ChemometricAnalyzer
from pathlib import Path
import json
from datetime import datetime


class DimensionReductionUI(QWidget):
    def __init__(self):
        super().__init__()
        self.analyzer = ChemometricAnalyzer()
        self.preprocessed_data = None  # Will store data from pre-treatment
        self.wavelengths = None
        self.target_values = None  # For PLSR
        self.sample_metadata = []  # Store sample names and property values
        self.excluded_indices = []  # Track excluded sample indices
        self.validation_indices = []  # Track validation set indices
        self.current_results = None
        self.analysis_indices = []  # Original sample indices used in the current result set
        
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
        self.cv_spin.setRange(2, 10)
        self.cv_spin.setValue(5)
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
        self.info_list = QListWidget()
        self.info_list.setMinimumWidth(280)
        self.info_list.setMaximumWidth(320)
        self.info_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        main_content.addWidget(self.info_list)

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
        self.score_plot = pg.PlotWidget(
            title="principal component score diagram"
        )
        self.score_plot.setLabel("left", "PC_2")
        self.score_plot.setLabel("bottom", "PC_1")
        self.score_plot.showGrid(x=True, y=True, alpha=0.3)
        self.score_plot.setBackground("w")
        # Enable antialiasing for smooth lines
        self.score_plot.setAntialiasing(True)

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
            import traceback
            traceback.print_exc()
    
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
        
        print(f"Performing PCA with {n_components} components...")
        results = self.analyzer.perform_pca(filtered_data, n_components)
        
        self.current_results = results
        
        # Update info list with PC variance information
        self.info_list.clear()
        for i in range(n_components):
            var = results['explained_variance'][i] * 100
            cum_var = results['cumulative_variance'][i] * 100
            self.info_list.addItem(f"PC{i+1}: {var:.2f}% (Cumulative: {cum_var:.2f}%)")
        
        # Plot scores (PC1 vs PC2 by default)
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
        
        filtered_data = self.preprocessed_data[valid_mask]
        filtered_targets = self.target_values[valid_mask]
        self.analysis_indices = np.flatnonzero(valid_mask).tolist()
        
        n_components = self.max_components_spin.value()
        cv_folds = self.cv_spin.value()
        optimize = self.optimize_check.isChecked()
        
        print(f"Performing PLSR with max {n_components} components, {cv_folds}-fold CV...")
        results = self.analyzer.perform_pls(
            filtered_data, 
            filtered_targets,
            n_components=n_components,
            cv=cv_folds,
            optimize=optimize
        )
        
        self.current_results = results
        
        # Update info list with detailed PLSR summary including fold metrics
        self.info_list.clear()
        summary_text = self.analyzer.get_pls_summary()
        for line in summary_text.split('\n'):
            self.info_list.addItem(line)
        
        # Plot predictions vs actual
        self._plot_plsr_predictions(results)
        
        QMessageBox.information(
            self,
            "Success",
            f"PLSR analysis completed!\n\n"
            f"Optimal components: {results['best_n_components']}\n"
            f"Calibration R²: {results['r2_train']:.4f}\n"
            f"Cross-validation R²: {results['r2_cv']:.4f}\n"
            f"RMSECV: {results['rmse_cv']:.4f}"
        )
    
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
        
        self.score_plot.clear()
        self.score_plot.setTitle("PCA Score Plot")
        self.score_plot.setLabel("left", f"PC{pc_y+1}")
        self.score_plot.setLabel("bottom", f"PC{pc_x+1}")
        
        spots = []
        for row_idx in range(scores.shape[0]):
            sample_index = self.analysis_indices[row_idx] if row_idx < len(self.analysis_indices) else row_idx
            sample_name = self._get_sample_name(sample_index)
            tooltip = (
                f"{sample_name}\n"
                f"PC{pc_x+1}: {scores[row_idx, pc_x]:.4f}\n"
                f"PC{pc_y+1}: {scores[row_idx, pc_y]:.4f}"
            )
            spots.append({
                'pos': (scores[row_idx, pc_x], scores[row_idx, pc_y]),
                'size': 10,
                'pen': self._get_point_pen(sample_index),
                'brush': self._get_point_brush(sample_index, default_color='blue'),
                'data': {'tooltip': tooltip, 'index': sample_index}
            })
        
        scatter = pg.ScatterPlotItem(spots=spots, name="PCA Scores")
        scatter.sigClicked.connect(self._on_point_clicked)
        self.score_plot.addItem(scatter)
        self.scatter_items = {'scores': scatter}
    
    def _plot_plsr_predictions(self, results):
        """Plot PLSR predicted vs actual with hover tooltips"""
        self.score_plot.clear()
        self.score_plot.setTitle("PLSR: Predicted vs Actual")
        self.score_plot.setLabel("left", "Predicted")
        self.score_plot.setLabel("bottom", "Actual")
        
        # Prepare calibration points with tooltips (skip validation points)
        spots_cal = []
        for row_idx, i in enumerate(self.analysis_indices):
            # Skip validation points - they should not be displayed
            if i in self.validation_indices:
                continue
            
            # Get sample info
            if i < len(self.sample_metadata):
                sample_name = self.sample_metadata[i].get('sample_name', f'Sample {i+1}')
                property_val = self.sample_metadata[i].get('property_value', '')
                property_name = self.sample_metadata[i].get('property_name', 'Value')
            else:
                sample_name = f'Sample {i+1}'
                property_val = self.target_values[i]
                property_name = 'Value'
            
            # Create tooltip text with sample name and property
            tooltip = f"{sample_name}\n{property_name}: {property_val}"
            
            spots_cal.append({
                'pos': (self.target_values[i], results['y_pred_train'][row_idx]),
                'size': 10,
                'pen': self._get_point_pen(i),
                'brush': self._get_point_brush(i, default_color='blue'),
                'data': {'tooltip': tooltip, 'index': i}  # Store tooltip and index
            })
        
        # Plot calibration points
        scatter_cal = pg.ScatterPlotItem(spots=spots_cal, name="Calibration")
        scatter_cal.sigClicked.connect(self._on_point_clicked)
        self.score_plot.addItem(scatter_cal)
        
        # Prepare CV points with tooltips (skip validation points)
        spots_cv = []
        for row_idx, i in enumerate(self.analysis_indices):
            # Skip validation points - they should not be displayed
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
            
            # Create tooltip text
            tooltip = f"{sample_name} (CV)\n{property_name}: {property_val}"
            
            spots_cv.append({
                'pos': (self.target_values[i], results['y_pred_cv'][row_idx]),
                'size': 8,
                'pen': self._get_point_pen(i),
                'brush': self._get_point_brush(i, default_color='red'),
                'data': {'tooltip': tooltip, 'index': i}
            })
        
        # Plot CV predictions
        scatter_cv = pg.ScatterPlotItem(spots=spots_cv, name="Cross-validation")
        scatter_cv.sigClicked.connect(self._on_point_clicked)
        self.score_plot.addItem(scatter_cv)
        
        # Store scatter items for hover detection
        self.scatter_items = {'calibration': scatter_cal, 'cv': scatter_cv}
        
        # Store tooltip text item for hover display
        if not hasattr(self, 'tooltip_text'):
            self.tooltip_text = pg.TextItem(color=(0, 0, 0), anchor=(0, 1), fill=(255, 255, 200, 230))
            self.score_plot.addItem(self.tooltip_text)
        self.tooltip_text.hide()
        
        # Connect mouse move signal for hover detection
        try:
            self.score_plot.scene().sigMouseMoved.disconnect()
        except:
            pass
        self.score_plot.scene().sigMouseMoved.connect(self._on_mouse_moved)
        
        # Add 1:1 line
        active_targets = self.target_values[self.analysis_indices]
        y_min = min(active_targets.min(), results['y_pred_train'].min())
        y_max = max(active_targets.max(), results['y_pred_train'].max())
        line = pg.PlotDataItem(
            [y_min, y_max], [y_min, y_max],
            pen=pg.mkPen('k', width=2, style=Qt.PenStyle.DashLine)
        )
        self.score_plot.addItem(line)
    
    def _on_mouse_moved(self, pos):
        """Detect mouse position and show tooltip for nearby points"""
        if not hasattr(self, 'scatter_items'):
            return
        
        # Convert scene position to plot coordinates
        mouse_point = self.score_plot.getViewBox().mapSceneToView(pos)
        
        # Check all scatter items for nearby points
        for scatter_item in self.scatter_items.values():
            points = scatter_item.points()
            for point in points:
                point_pos = point.pos()
                # Calculate distance (in plot coordinates)
                dx = mouse_point.x() - point_pos[0]
                dy = mouse_point.y() - point_pos[1]
                
                # Get view range for relative distance calculation
                view_range = self.score_plot.getViewBox().viewRange()
                x_range = view_range[0][1] - view_range[0][0]
                y_range = view_range[1][1] - view_range[1][0]
                
                # Normalize distance
                norm_dist = ((dx/x_range)**2 + (dy/y_range)**2)**0.5
                
                # If within threshold, show tooltip
                if norm_dist < 0.02:  # 2% of plot range
                    point_data = point.data()
                    if isinstance(point_data, dict):
                        tooltip_text = point_data.get('tooltip', str(point_data))
                    else:
                        tooltip_text = str(point_data)
                    self.tooltip_text.setText(tooltip_text)
                    self.tooltip_text.setPos(point_pos[0], point_pos[1])
                    self.tooltip_text.show()
                    return
        
        # No point nearby, hide tooltip
        self.tooltip_text.hide()
    
    def _on_point_clicked(self, plot, points):
        """Handle point click - either add to selection or show context menu"""
        if len(points) == 0:
            return
        
        point = points[0]
        point_data = point.data()
        
        if not isinstance(point_data, dict):
            return
        
        sample_index = point_data.get('index', -1)
        if sample_index < 0:
            return
        
        # If in selection mode, add/remove point from selection
        if self.selection_mode:
            self._toggle_point_selection(sample_index)
            return
        
        # Get sample info
        sample_name = 'Unknown'
        if sample_index < len(self.sample_metadata):
            sample_name = self.sample_metadata[sample_index].get('sample_name', 'Unknown')
        
        # Create context menu
        menu = QMenu()
        menu.setStyleSheet("QMenu { font-size: 10pt; }")
        
        # Add options
        validation_action = None
        if self.algorithm_combo.currentText() == "PLSR":
            validation_action = menu.addAction(f"Set '{sample_name}' as Validation")
        invalidation_action = menu.addAction(f"Set '{sample_name}' as Outlier (Remove)")
        
        # Show menu and get user choice
        action = menu.exec(QCursor.pos())
        
        if validation_action is not None and action == validation_action:
            self._set_as_validation(sample_index)
        elif action == invalidation_action:
            self._set_as_invalid(sample_index)
    
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
                summary_text = self.analyzer.get_pls_summary()
                for line in summary_text.split('\n'):
                    self.info_list.addItem(line)
                
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
    
    def _plot_plsr_predictions_with_exclusions(self, results, valid_mask):
        """Plot PLSR predictions showing excluded points differently"""
        self.score_plot.clear()
        self.score_plot.setTitle("PLSR: Predicted vs Actual (with exclusions)")
        self.score_plot.setLabel("left", "Predicted")
        self.score_plot.setLabel("bottom", "Actual")
        
        # Plot only valid calibration points (skip excluded and validation)
        spots_cal = []
        for row_idx, i in enumerate(self.analysis_indices):
            if i in self.validation_indices:
                continue  # Skip validation points
            
            if i < len(self.sample_metadata):
                sample_name = self.sample_metadata[i].get('sample_name', f'Sample {i+1}')
                property_val = self.sample_metadata[i].get('property_value', '')
                property_name = self.sample_metadata[i].get('property_name', 'Value')
            else:
                sample_name = f'Sample {i+1}'
                property_val = self.target_values[i]
                property_name = 'Value'
            
            tooltip = f"{sample_name}\n{property_name}: {property_val}"
            
            spots_cal.append({
                'pos': (self.target_values[i], results['y_pred_train'][row_idx]),
                'size': 10,
                'pen': self._get_point_pen(i),
                'brush': self._get_point_brush(i, default_color='blue'),
                'data': {'tooltip': tooltip, 'index': i}
            })
        
        scatter_cal = pg.ScatterPlotItem(spots=spots_cal, name="Calibration")
        scatter_cal.sigClicked.connect(self._on_point_clicked)
        self.score_plot.addItem(scatter_cal)
        
        # Plot CV predictions (skip excluded and validation)
        spots_cv = []
        for row_idx, i in enumerate(self.analysis_indices):
            if i in self.validation_indices:
                continue  # Skip validation points
            
            if i < len(self.sample_metadata):
                sample_name = self.sample_metadata[i].get('sample_name', f'Sample {i+1}')
                property_val = self.sample_metadata[i].get('property_value', '')
                property_name = self.sample_metadata[i].get('property_name', 'Value')
            else:
                sample_name = f'Sample {i+1}'
                property_val = self.target_values[i]
                property_name = 'Value'
            
            tooltip = f"{sample_name} (CV)\n{property_name}: {property_val}"
            
            spots_cv.append({
                'pos': (self.target_values[i], results['y_pred_cv'][row_idx]),
                'size': 8,
                'pen': self._get_point_pen(i),
                'brush': self._get_point_brush(i, default_color='red'),
                'data': {'tooltip': tooltip, 'index': i}
            })
        
        scatter_cv = pg.ScatterPlotItem(spots=spots_cv, name="Cross-validation")
        scatter_cv.sigClicked.connect(self._on_point_clicked)
        self.score_plot.addItem(scatter_cv)
        
        # Plot excluded points in gray
        excluded_spots = []
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
            
            # Show excluded points at their original position (x = actual value, y = 0 or minimal)
            excluded_spots.append({
                'pos': (self.target_values[i], self.target_values[i]),  # On the 1:1 line
                'size': 8,
                'pen': pg.mkPen('r', width=2),
                'brush': pg.mkBrush(128, 128, 128, 100),
                'symbol': 'x',
                'data': {'tooltip': tooltip, 'index': i}
            })
        
        if excluded_spots:
            scatter_excluded = pg.ScatterPlotItem(spots=excluded_spots, name="Excluded")
            self.score_plot.addItem(scatter_excluded)
        
        # Store scatter items for hover detection
        self.scatter_items = {'calibration': scatter_cal, 'cv': scatter_cv}
        
        # Recreate tooltip
        if hasattr(self, 'tooltip_text'):
            self.score_plot.removeItem(self.tooltip_text)
        self.tooltip_text = pg.TextItem(color=(0, 0, 0), anchor=(0, 1), fill=(255, 255, 200, 230))
        self.score_plot.addItem(self.tooltip_text)
        self.tooltip_text.hide()
        
        # Reconnect mouse move signal
        try:
            self.score_plot.scene().sigMouseMoved.disconnect()
        except:
            pass
        self.score_plot.scene().sigMouseMoved.connect(self._on_mouse_moved)
        
        # Add 1:1 line
        active_targets = self.target_values[self.analysis_indices]
        y_min = min(active_targets.min(), results['y_pred_train'].min())
        y_max = max(active_targets.max(), results['y_pred_train'].max())
        line = pg.PlotDataItem(
            [y_min, y_max], [y_min, y_max],
            pen=pg.mkPen('k', width=2, style=Qt.PenStyle.DashLine)
        )
        self.score_plot.addItem(line)
    
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
        
        try:
            import pyqtgraph.opengl as gl
            view = gl.GLViewWidget()
            view.setBackgroundColor('w')
            view.opts['distance'] = 40
            layout.addWidget(view)
            
            grid = gl.GLGridItem()
            grid.scale(2, 2, 2)
            view.addItem(grid)
            
            colors = np.array([
                [1.0, 0.65, 0.0, 0.9] if sample_index in self.selected_points else [0.0, 0.35, 0.9, 0.75]
                for sample_index in self.analysis_indices
            ])
            scatter = gl.GLScatterPlotItem(pos=scores[:, :3], color=colors, size=10, pxMode=True)
            view.addItem(scatter)
        except Exception:
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
        self.score_plot.clear()
        self.score_plot.setTitle("PLSR: Regression Coefficients")
        self.score_plot.setLabel("left", "Coefficient Value")
        self.score_plot.setLabel("bottom", "Wavelength (nm)")
        
        coefficients = self.current_results['coefficients']
        
        # Plot coefficients
        coef_plot = pg.PlotDataItem(
            x=self.wavelengths,
            y=coefficients,
            pen=pg.mkPen('b', width=2)
        )
        self.score_plot.addItem(coef_plot)
        
        # Add zero line
        self.score_plot.addItem(pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('k', width=1, style=Qt.PenStyle.DashLine)))
    
    def _plot_component_selection_curve(self):
        """Plot R² and RMSE vs number of components with dual y-axes"""
        self.score_plot.clear()
        self.score_plot.setTitle("Component Selection: CV Performance")
        self.score_plot.setLabel("left", "R² (CV)", color='b')
        self.score_plot.setLabel("bottom", "Number of Components")
        
        r2_scores = self.current_results['r2_scores']
        rmse_scores = self.current_results['rmse_scores']
        n_components = list(range(1, len(r2_scores) + 1))
        
        # Create second ViewBox for RMSE (right axis)
        p2 = pg.ViewBox()
        self.score_plot.showAxis('right')
        self.score_plot.scene().addItem(p2)
        self.score_plot.getAxis('right').linkToView(p2)
        p2.setXLink(self.score_plot)
        self.score_plot.getAxis('right').setLabel('RMSE (CV)', color='r')
        
        # Function to update views when plot is resized
        def updateViews():
            p2.setGeometry(self.score_plot.getViewBox().sceneBoundingRect())
            p2.linkedViewChanged(self.score_plot.getViewBox(), p2.XAxis)
        
        updateViews()
        self.score_plot.getViewBox().sigResized.connect(updateViews)
        
        # Plot R² scores on left axis (blue)
        r2_plot = pg.PlotDataItem(
            x=n_components,
            y=r2_scores,
            pen=pg.mkPen('b', width=2),
            symbol='o',
            symbolSize=8,
            symbolBrush='b'
        )
        self.score_plot.addItem(r2_plot)
        
        # Plot RMSE on right axis (red)
        rmse_plot = pg.PlotDataItem(
            x=n_components,
            y=rmse_scores,
            pen=pg.mkPen('r', width=2),
            symbol='s',
            symbolSize=8,
            symbolBrush='r'
        )
        p2.addItem(rmse_plot)
        
        # Set appropriate ranges
        self.score_plot.setYRange(min(r2_scores) * 0.95, max(r2_scores) * 1.05)
        p2.setYRange(min(rmse_scores) * 0.95, max(rmse_scores) * 1.05)
        
        # Mark the optimal component with vertical line
        best_n = self.current_results['best_n_components']
        
        # Use a dark green color for the optimal component line
        dark_green = (0, 100, 0)
        opt_line = pg.InfiniteLine(
            pos=best_n, 
            angle=90, 
            pen=pg.mkPen(dark_green, width=2, style=Qt.PenStyle.DashLine)
        )
        self.score_plot.addItem(opt_line)
        
        # Add text annotation for optimal component (also dark green)
        text_item = pg.TextItem(
            f'Optimal: {best_n} components',
            anchor=(0.5, 1),
            color=dark_green
        )
        text_item.setPos(best_n, max(r2_scores) * 1.03)
        self.score_plot.addItem(text_item)
    
    def load_preprocessed_data(self, spectra: np.ndarray, wavelengths: np.ndarray = None, 
                              target_values: np.ndarray = None, sample_metadata: list = None):
        """
        Load preprocessed data from pre-treatment tab
        
        Args:
            spectra: Preprocessed spectral data (n_samples x n_wavelengths)
            wavelengths: Wavelength array (optional)
            target_values: Target values for PLSR (optional)
            sample_metadata: List of dicts with sample info (optional)
        """
        self.preprocessed_data = spectra
        self.wavelengths = wavelengths
        self.target_values = target_values
        self.sample_metadata = sample_metadata if sample_metadata else []
        self.excluded_indices = []
        self.validation_indices = []
        self.current_results = None
        self.selection_mode = False
        self.selected_points = []
        self.analysis_indices = list(range(spectra.shape[0]))
        
        print(f"Loaded preprocessed data: {spectra.shape[0]} samples, {spectra.shape[1]} wavelengths")
        if target_values is not None:
            print(f"Target values loaded: {len(target_values)} values")
        if sample_metadata:
            print(f"Sample metadata loaded: {len(sample_metadata)} samples")
    
    def _get_sample_name(self, sample_index):
        """Return the display name for a sample"""
        if 0 <= sample_index < len(self.sample_metadata):
            return self.sample_metadata[sample_index].get('sample_name', f'Sample {sample_index + 1}')
        return f'Sample {sample_index + 1}'
    
    def _get_point_brush(self, sample_index, default_color='blue'):
        """Return brush for regular or selected points"""
        if sample_index in self.selected_points:
            return pg.mkBrush(255, 165, 0, 220)
        
        if default_color == 'red':
            return pg.mkBrush(255, 0, 0, 120)
        return pg.mkBrush(0, 0, 255, 120)
    
    def _get_point_pen(self, sample_index):
        """Return pen for regular or selected points"""
        if sample_index in self.selected_points:
            return pg.mkPen((255, 140, 0), width=2)
        return pg.mkPen(None)
    
    def _refresh_current_plot(self):
        """Redraw the current chart so selection state stays visible"""
        if self.current_results is None:
            return
        
        algorithm = self.algorithm_combo.currentText()
        if algorithm == "PCA" and 'scores' in self.current_results:
            x_text = self.x_axis_combo.currentText()
            y_text = self.y_axis_combo.currentText()
            pc_x = int(x_text.split('_')[1]) - 1
            pc_y = int(y_text.split('_')[1]) - 1
            self._plot_pca_scores(pc_x, pc_y)
        elif algorithm == "PLSR":
            if len(self.excluded_indices) > 0:
                valid_mask = np.ones(len(self.target_values), dtype=bool)
                for idx in self.excluded_indices:
                    if 0 <= idx < len(valid_mask):
                        valid_mask[idx] = False
                self._plot_plsr_predictions_with_exclusions(self.current_results, valid_mask)
            else:
                self._plot_plsr_predictions(self.current_results)
