"""
Chemometric Analysis Service for PCA and PLSR
Handles dimension reduction and regression modeling
"""

import numpy as np
from sklearn.decomposition import PCA
from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import cross_val_predict, KFold
from sklearn.metrics import r2_score, mean_squared_error


class ChemometricAnalyzer:
    def __init__(self):
        self.pca_model = None
        self.pls_model = None
        self.pca_results = {}
        self.pls_results = {}

    def perform_pca(self, spectra: np.ndarray, n_components: int = 3):
        """
        Perform Principal Component Analysis
        
        Args:
            spectra: Input spectral data (n_samples x n_wavelengths)
            n_components: Number of principal components to extract
            
        Returns:
            Dictionary containing PCA results
        """
        self.pca_model = PCA(n_components=n_components)
        scores = self.pca_model.fit_transform(spectra)

        self.pca_results = {
            'scores': scores,
            'loadings': self.pca_model.components_,
            'explained_variance': self.pca_model.explained_variance_ratio_,
            'cumulative_variance': np.cumsum(self.pca_model.explained_variance_ratio_),
            'n_components': n_components
        }

        return self.pca_results

    def perform_pls(self, X: np.ndarray, y: np.ndarray,
                    n_components: int = 5, cv: int = 5, optimize: bool = True):
        """
        Perform Partial Least Squares Regression
        
        Args:
            X: Input spectral data (n_samples x n_wavelengths)
            y: Target values (n_samples,)
            n_components: Maximum number of PLS components
            cv: Number of cross-validation folds
            optimize: If True, optimize number of components via CV
            
        Returns:
            Dictionary containing PLSR results
        """
        X = np.asarray(X)
        y = np.asarray(y).ravel()

        if X.ndim != 2:
            raise ValueError("PLSR input spectra must be a 2D array.")
        if len(X) != len(y):
            raise ValueError("PLSR spectra and target arrays must have the same number of samples.")

        n_samples, n_features = X.shape
        if n_samples < 5:
            raise ValueError(
                "PLSR requires at least 5 samples for a meaningful cross-validation result. "
                f"Received {n_samples} sample(s)."
            )

        cv = min(int(cv), n_samples)
        if cv < 2:
            raise ValueError("PLSR cross-validation requires at least 2 folds.")

        cv_splitter = KFold(n_splits=cv, shuffle=True, random_state=42)
        min_train_size = min(len(train_idx) for train_idx, _ in cv_splitter.split(X))
        max_components = min(int(n_components), n_features, min_train_size)

        if max_components < 1:
            raise ValueError(
                "PLSR could not determine a valid component count from the current data shape."
            )

        best_r2 = -np.inf
        best_n_comp = 1
        r2_scores = []
        rmse_scores = []

        if optimize:
            # Find optimal number of components
            for n in range(1, max_components + 1):
                pls = PLSRegression(n_components=n)

                y_pred_cv = cross_val_predict(pls, X, y, cv=cv_splitter)
                r2 = r2_score(y, y_pred_cv)
                rmse = np.sqrt(mean_squared_error(y, y_pred_cv))

                r2_scores.append(r2)
                rmse_scores.append(rmse)

                if r2 > best_r2:
                    best_r2 = r2
                    best_n_comp = n
        else:
            # Use fixed number of components
            best_n_comp = max_components
            pls = PLSRegression(n_components=best_n_comp)
            y_pred_cv = cross_val_predict(pls, X, y, cv=cv_splitter)
            r2 = r2_score(y, y_pred_cv)
            rmse = np.sqrt(mean_squared_error(y, y_pred_cv))
            r2_scores = [r2]
            rmse_scores = [rmse]

        # Train final model with optimal/fixed components
        self.pls_model = PLSRegression(n_components=best_n_comp)
        self.pls_model.fit(X, y)

        # Get predictions
        y_pred_train = self.pls_model.predict(X).ravel()
        y_pred_cv = cross_val_predict(PLSRegression(n_components=best_n_comp), X, y, cv=cv_splitter).ravel()

        # Calculate fold-by-fold metrics
        fold_metrics = []
        for fold_idx, (train_idx, test_idx) in enumerate(cv_splitter.split(X)):
            X_train_fold, X_test_fold = X[train_idx], X[test_idx]
            y_train_fold, y_test_fold = y[train_idx], y[test_idx]

            fold_model = PLSRegression(n_components=best_n_comp)
            fold_model.fit(X_train_fold, y_train_fold)
            y_pred_fold = fold_model.predict(X_test_fold).ravel()

            fold_r2 = np.nan if len(test_idx) < 2 else r2_score(y_test_fold, y_pred_fold)
            fold_rmse = np.sqrt(mean_squared_error(y_test_fold, y_pred_fold))

            fold_metrics.append({
                'fold': fold_idx + 1,
                'r2': fold_r2,
                'rmse': fold_rmse,
                'n_samples': len(test_idx)
            })

        self.pls_results = {
            'model': self.pls_model,
            'best_n_components': best_n_comp,
            'r2_scores': r2_scores,
            'rmse_scores': rmse_scores,
            'y_pred_train': y_pred_train,
            'y_pred_cv': y_pred_cv,
            'r2_train': r2_score(y, y_pred_train),
            'rmse_train': np.sqrt(mean_squared_error(y, y_pred_train)),
            'r2_cv': r2_score(y, y_pred_cv),
            'rmse_cv': np.sqrt(mean_squared_error(y, y_pred_cv)),
            'x_scores': self.pls_model.x_scores_,
            'x_loadings': self.pls_model.x_loadings_,
            'coefficients': self.pls_model.coef_.ravel(),
            'intercept': float(self.pls_model.intercept_[0]) if hasattr(self.pls_model.intercept_, '__len__') else float(self.pls_model.intercept_),
            'n_samples': len(y),
            'cv_folds': cv,
            'max_components_tested': max_components,
            'fold_metrics': fold_metrics,
            'optimized': optimize
        }

        return self.pls_results

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict using trained PLS model
        
        Args:
            X: Input spectral data
            
        Returns:
            Predicted values
        """
        if self.pls_model is None:
            raise ValueError("PLS model not trained yet")

        return self.pls_model.predict(X).ravel()

    def get_pca_summary(self) -> str:
        """Generate text summary of PCA results"""
        if not self.pca_results:
            return "No PCA analysis performed yet"

        summary = f"PCA Summary:\n"
        summary += f"Number of components: {self.pca_results['n_components']}\n\n"

        for i, (var, cum_var) in enumerate(zip(
                self.pca_results['explained_variance'],
                self.pca_results['cumulative_variance'])):
            summary += f"PC{i+1}: {var*100:.2f}% (Cumulative: {cum_var*100:.2f}%)\n"

        return summary

    def get_pls_summary(self) -> str:
        """Generate text summary of PLSR results"""
        if not self.pls_results:
            return "No PLS analysis performed yet"

        summary = f"PLS Regression Summary:\n"
        if self.pls_results.get('optimized', True):
            summary += f"Optimal components (CV-optimized): {self.pls_results['best_n_components']}\n"
        else:
            summary += f"Fixed components (user-specified): {self.pls_results['best_n_components']}\n"
        summary += f"Number of samples: {self.pls_results['n_samples']}\n\n"
        summary += f"CV folds: {self.pls_results.get('cv_folds', 'N/A')}\n"
        summary += f"Max components tested: {self.pls_results.get('max_components_tested', self.pls_results['best_n_components'])}\n\n"

        summary += f"Calibration Results:\n"
        summary += f"  R²: {self.pls_results['r2_train']:.4f}\n"
        summary += f"  RMSE: {self.pls_results['rmse_train']:.4f}\n\n"

        summary += f"Cross-Validation Results (Overall):\n"
        summary += f"  R²: {self.pls_results['r2_cv']:.4f}\n"
        summary += f"  RMSE: {self.pls_results['rmse_cv']:.4f}\n\n"

        summary += f"Cross-Validation Results (Per Fold):\n"
        summary += f"{'Fold':<8} {'R²':>10} {'RMSE':>10} {'Samples':>10}\n"
        summary += f"{'-'*42}\n"

        for fold_metric in self.pls_results['fold_metrics']:
            summary += f"{fold_metric['fold']:<8} "
            summary += f"{fold_metric['r2']:>10.4f} "
            summary += f"{fold_metric['rmse']:>10.4f} "
            summary += f"{fold_metric['n_samples']:>10}\n"

        fold_r2_mean = np.nanmean([f['r2'] for f in self.pls_results['fold_metrics']])
        fold_r2_std = np.nanstd([f['r2'] for f in self.pls_results['fold_metrics']])
        fold_rmse_mean = np.mean([f['rmse'] for f in self.pls_results['fold_metrics']])
        fold_rmse_std = np.std([f['rmse'] for f in self.pls_results['fold_metrics']])

        summary += f"{'-'*42}\n"
        summary += f"{'Mean':<8} {fold_r2_mean:>10.4f} {fold_rmse_mean:>10.4f}\n"
        summary += f"{'Std Dev':<8} {fold_r2_std:>10.4f} {fold_rmse_std:>10.4f}\n"

        return summary
