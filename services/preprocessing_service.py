"""
Preprocessing Service - for spectral data preprocessing
"""
import numpy as np
from scipy import signal
from scipy.ndimage import uniform_filter1d
from typing import Dict, Optional, Tuple
import json


class Preprocessor:
    @staticmethod
    def normalize(spectra: np.ndarray) -> np.ndarray:
        min_val = np.min(spectra, axis=1, keepdims=True)
        max_val = np.max(spectra, axis=1, keepdims=True)
        return (spectra - min_val) / (max_val - min_val + 1e-10)

    @staticmethod
    def standard_normal_variate(spectra: np.ndarray) -> np.ndarray:
        mean = np.mean(spectra, axis=1, keepdims=True)
        std = np.std(spectra, axis=1, keepdims=True)
        return (spectra - mean) / (std + 1e-10)

    @staticmethod
    def multiplicative_scatter_correction(spectra: np.ndarray) -> np.ndarray:
        mean_spectrum = np.mean(spectra, axis=0)
        corrected = np.zeros_like(spectra)

        for i in range(spectra.shape[0]):
            fit = np.polyfit(mean_spectrum, spectra[i], 1)
            corrected[i] = (spectra[i] - fit[1]) / fit[0]

        return corrected

    @staticmethod
    def savitzky_golay(spectra: np.ndarray, window_length: int = 11,
                       polyorder: int = 2, deriv: int = 0) -> np.ndarray:
        if window_length % 2 == 0:
            window_length += 1

        window_length = min(window_length, spectra.shape[1])

        filtered = np.zeros_like(spectra)
        for i in range(spectra.shape[0]):
            filtered[i] = signal.savgol_filter(
                spectra[i],
                window_length=window_length,
                polyorder=polyorder,
                deriv=deriv
            )

        return filtered

    @staticmethod
    def moving_average(spectra: np.ndarray, window_size: int = 5) -> np.ndarray:
        smoothed = np.zeros_like(spectra)
        for i in range(spectra.shape[0]):
            smoothed[i] = uniform_filter1d(spectra[i], size=window_size)
        return smoothed

    @staticmethod
    def baseline_correction(spectra: np.ndarray, degree: int = 2) -> np.ndarray:
        corrected = np.zeros_like(spectra)

        for i in range(spectra.shape[0]):
            x = np.arange(len(spectra[i]))
            coeffs = np.polyfit(x, spectra[i], degree)
            baseline = np.polyval(coeffs, x)
            corrected[i] = spectra[i] - baseline

        return corrected

    @staticmethod
    def detrend(spectra: np.ndarray) -> np.ndarray:
        detrended = np.zeros_like(spectra)
        for i in range(spectra.shape[0]):
            detrended[i] = signal.detrend(spectra[i])
        return detrended

    @staticmethod
    def mean_centering(spectra: np.ndarray) -> np.ndarray:
        return spectra - np.mean(spectra, axis=0, keepdims=True)

    @staticmethod
    def autoscaling(spectra: np.ndarray) -> np.ndarray:
        mean = np.mean(spectra, axis=0, keepdims=True)
        std = np.std(spectra, axis=0, keepdims=True)
        return (spectra - mean) / (std + 1e-10)


class PreprocessingService:
    """Service for applying preprocessing algorithms to spectral data"""
    
    # Mapping of UI names to preprocessing methods
    ALGORITHM_MAP = {
        "mean-centering": ("mean_centering", {}),
        "moving smoothing": ("moving_average", {"window_size": 5}),
        "autoscaling": ("autoscaling", {}),
        "SG smoothing": ("savitzky_golay", {"window_length": 11, "polyorder": 2, "deriv": 0}),
        "normalization": ("normalize", {}),
        "detrending": ("detrend", {}),
        "MSC": ("multiplicative_scatter_correction", {}),
        "SNV": ("standard_normal_variate", {}),
        "SG 1st derivative": ("savitzky_golay", {"window_length": 11, "polyorder": 2, "deriv": 1}),
        "SG 2nd derivative": ("savitzky_golay", {"window_length": 11, "polyorder": 2, "deriv": 2}),
    }
    
    @staticmethod
    def apply_preprocessing(data: Dict, algorithm_name: str, custom_params: Dict = None) -> Tuple[Optional[Dict], Optional[np.ndarray], str]:
        """
        Apply preprocessing algorithm to spectral data
        
        Args:
            data: Data dictionary with samples
            algorithm_name: Name of the algorithm to apply
            custom_params: Custom parameters from UI (overrides defaults)
            
        Returns:
            Tuple of (original_spectra_array, processed_spectra_array, message)
        """
        try:
            if algorithm_name not in PreprocessingService.ALGORITHM_MAP:
                return None, None, f"Unknown algorithm: {algorithm_name}"
            
            samples = data.get('samples', [])
            if not samples:
                return None, None, "No samples found in data!"
            
            # Extract spectra into numpy array
            wavelengths_list = []
            absorbances_list = []
            
            for sample in samples:
                wavelengths = sample.get('wavelengths', [])
                absorbances = sample.get('absorbances', [])
                
                if wavelengths and absorbances:
                    wavelengths_list.append(wavelengths)
                    absorbances_list.append(absorbances)
            
            if not absorbances_list:
                return None, None, "No valid spectral data found!"
            
            # Convert to numpy array (samples x wavelengths)
            original_spectra = np.array(absorbances_list)
            wavelengths = np.array(wavelengths_list[0])  # All should have same wavelengths
            
            # Get algorithm details
            method_name, default_params = PreprocessingService.ALGORITHM_MAP[algorithm_name]
            
            # Merge custom parameters with defaults (custom takes priority)
            params = default_params.copy()
            if custom_params:
                params.update(custom_params)
            
            # Apply preprocessing
            preprocessor = Preprocessor()
            method = getattr(preprocessor, method_name)
            processed_spectra = method(original_spectra, **params)
            
            success_msg = (
                f"Applied {algorithm_name} preprocessing\n"
                f"Processed {len(samples)} spectra"
            )
            
            print(f"Applied {algorithm_name} to {len(samples)} samples")
            return original_spectra, processed_spectra, success_msg
            
        except Exception as e:
            error_msg = f"Failed to apply preprocessing: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return None, None, error_msg
    
    @staticmethod
    def calculate_correlation_coefficient(spectra: np.ndarray, reference_values: np.ndarray = None) -> np.ndarray:
        """
        Calculate correlation coefficient for each wavelength
        
        Args:
            spectra: Spectral data (samples x wavelengths)
            reference_values: Reference values for each sample (optional)
            
        Returns:
            Correlation coefficients for each wavelength
        """
        try:
            if reference_values is None:
                # If no reference values, use mean spectrum as reference
                reference_values = np.mean(spectra, axis=1)
            
            correlations = np.zeros(spectra.shape[1])
            
            for i in range(spectra.shape[1]):
                correlations[i] = np.corrcoef(spectra[:, i], reference_values)[0, 1]
            
            return correlations
            
        except Exception as e:
            print(f"Error calculating correlation: {e}")
            return np.zeros(spectra.shape[1])
    
    @staticmethod
    def calculate_standard_deviation(spectra: np.ndarray) -> np.ndarray:
        """
        Calculate standard deviation for each wavelength
        
        Args:
            spectra: Spectral data (samples x wavelengths)
            
        Returns:
            Standard deviation for each wavelength
        """
        return np.std(spectra, axis=0)
