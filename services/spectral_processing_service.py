"""
Spectral Processing Service - for spectral data cropping and processing
"""
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, List, Optional


class SpectralProcessingService:
    """Service for spectral data processing operations"""
    
    @staticmethod
    def get_temp_directory() -> Path:
        """Get the temp_data directory path"""
        base_dir = Path(__file__).parent.parent
        temp_dir = base_dir / 'temp_data'
        temp_dir.mkdir(exist_ok=True)
        return temp_dir
    
    @staticmethod
    def load_latest_data() -> Optional[Dict]:
        """
        Load the most recent data from temp_data
        
        Returns:
            Dictionary with loaded data or None if no data found
        """
        try:
            temp_dir = SpectralProcessingService.get_temp_directory()
            
            # Find most recent JSON file
            json_files = sorted(temp_dir.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
            if not json_files:
                print("No data files found in temp_data")
                return None
            
            with open(json_files[0], 'r') as f:
                data = json.load(f)
            
            print(f"Loaded data from: {json_files[0].name}")
            return data
            
        except Exception as e:
            print(f"Error loading data from temp: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def load_original_uncropped_data() -> Optional[Dict]:
        """
        Load the original uncropped data for the current project
        Searches for files marked with cropped=False in metadata
        
        Returns:
            Dictionary with original uncropped data or None if not found
        """
        try:
            temp_dir = SpectralProcessingService.get_temp_directory()
            
            # Find all JSON files
            json_files = sorted(temp_dir.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
            if not json_files:
                print("No data files found in temp_data")
                return None
            
            # Get project name from the most recent file
            with open(json_files[0], 'r') as f:
                recent_data = json.load(f)
            project_name = recent_data.get('metadata', {}).get('project_name', '')
            
            # Search for the original uncropped file for this project
            for json_file in json_files:
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    
                    metadata = data.get('metadata', {})
                    file_project = metadata.get('project_name', '')
                    is_cropped = metadata.get('cropped', False)
                    
                    # Found original uncropped file for same project
                    if file_project == project_name and not is_cropped:
                        print(f"Loaded original uncropped data from: {json_file.name}")
                        return data
                
                except Exception as e:
                    print(f"Error reading {json_file.name}: {e}")
                    continue
            
            print(f"No original uncropped file found for project: {project_name}")
            return None
            
        except Exception as e:
            print(f"Error loading original uncropped data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def save_original_data(data: Dict) -> Optional[Path]:
        """
        Save original uncropped data to temp_data directory with recent timestamp
        so it becomes the latest file
        
        Args:
            data: Original data dictionary
            
        Returns:
            Path to saved file or None if save fails
        """
        try:
            temp_dir = SpectralProcessingService.get_temp_directory()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            metadata = data.get('metadata', {})
            project_name = metadata.get('project_name', 'unknown').replace(' ', '_')
            data_type = metadata.get('data_type', 'averaged')
            
            # Save as JSON with "restored" marker
            json_filename = f"{project_name}_{data_type}_restored_{timestamp}.json"
            json_path = temp_dir / json_filename
            
            # Ensure cropped flag is False
            data['metadata']['cropped'] = False
            data['metadata']['restored_timestamp'] = timestamp
            
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"Original data saved to: {json_path}")
            return json_path
            
        except Exception as e:
            print(f"Error saving original data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_wavelength_range(data: Dict) -> Tuple[float, float]:
        """
        Get the wavelength range from loaded data
        
        Args:
            data: Loaded data dictionary
            
        Returns:
            Tuple of (min_wavelength, max_wavelength)
        """
        try:
            samples = data.get('samples', [])
            if samples and samples[0].get('wavelengths'):
                wavelengths = samples[0]['wavelengths']
                return min(wavelengths), max(wavelengths)
            return 0.0, 10000.0
        except Exception as e:
            print(f"Error getting wavelength range: {e}")
            return 0.0, 10000.0
    
    @staticmethod
    def crop_spectral_data(data: Dict, crop_start: float, crop_end: float) -> Tuple[Optional[Dict], str]:
        """
        Crop spectral data to specified wavelength range
        
        Args:
            data: Data dictionary with samples
            crop_start: Start wavelength for cropping
            crop_end: End wavelength for cropping
            
        Returns:
            Tuple of (cropped_data_dict, message)
            Returns (None, error_message) if cropping fails
        """
        try:
            if crop_start >= crop_end:
                return None, "Start wavelength must be less than end wavelength!"
            
            samples = data.get('samples', [])
            if not samples:
                return None, "No samples found in data!"
            
            cropped_samples = []
            total_samples = len(samples)
            original_points = 0
            cropped_points = 0
            
            for sample in samples:
                wavelengths = np.array(sample.get('wavelengths', []))
                absorbances = np.array(sample.get('absorbances', []))
                
                if len(wavelengths) == 0:
                    continue
                
                if original_points == 0:
                    original_points = len(wavelengths)
                
                # Check if crop range is within data range
                if wavelengths[0] > crop_start or wavelengths[-1] < crop_end:
                    return None, (
                        f"Crop range ({crop_start}-{crop_end} nm) is outside data range "
                        f"({wavelengths[0]:.2f}-{wavelengths[-1]:.2f} nm)!"
                    )
                
                # Find indices that match crop range
                start_idx = np.argmin(np.abs(wavelengths - crop_start))
                end_idx = np.argmin(np.abs(wavelengths - crop_end))
                
                # Ensure proper range
                if start_idx >= end_idx:
                    # Use boolean mask as fallback
                    mask = (wavelengths >= crop_start) & (wavelengths <= crop_end)
                    cropped_wavelengths = wavelengths[mask].tolist()
                    cropped_absorbances = absorbances[mask].tolist()
                else:
                    # Crop the data
                    cropped_wavelengths = wavelengths[start_idx:end_idx+1].tolist()
                    cropped_absorbances = absorbances[start_idx:end_idx+1].tolist()
                
                if len(cropped_wavelengths) == 0:
                    continue
                
                if cropped_points == 0:
                    cropped_points = len(cropped_wavelengths)
                
                # Update sample with cropped data
                sample['wavelengths'] = cropped_wavelengths
                sample['absorbances'] = cropped_absorbances
                cropped_samples.append(sample)
            
            if len(cropped_samples) == 0:
                return None, "No samples could be cropped with the specified range!"
            
            # Store original wavelength range in metadata (only if this is FRESH data that was never cropped)
            if 'original_wavelength_range' not in data['metadata']:
                # Check if data was already cropped in a previous session
                already_cropped = data['metadata'].get('cropped', False)
                
                if not already_cropped:
                    # This is fresh, uncropped data - store current range as original
                    first_sample = samples[0]
                    orig_wavelengths = np.array(first_sample.get('wavelengths', []))
                    if len(orig_wavelengths) > 0:
                        data['metadata']['original_wavelength_range'] = {
                            'min': float(orig_wavelengths[0]),
                            'max': float(orig_wavelengths[-1])
                        }
                        print(f"Storing original wavelength range: {orig_wavelengths[0]:.2f} - {orig_wavelengths[-1]:.2f} nm")
                else:
                    # Data was already cropped before but doesn't have original_wavelength_range
                    # Use standard NIR range as fallback
                    print("Warning: Data was previously cropped but original range not stored. Using 900-1700 nm as default.")
                    data['metadata']['original_wavelength_range'] = {
                        'min': 900.0,
                        'max': 1700.0
                    }
            
            # Update the data dictionary
            data['samples'] = cropped_samples
            data['metadata']['cropped'] = True
            data['metadata']['crop_range'] = f"{crop_start}-{crop_end} nm"
            data['metadata']['cropped_timestamp'] = datetime.now().strftime('%Y%m%d_%H%M%S')
            data['metadata']['original_points'] = original_points
            data['metadata']['cropped_points'] = cropped_points
            
            success_message = (
                f"Successfully cropped {len(cropped_samples)} samples to wavelength range:\n"
                f"{crop_start} - {crop_end} nm\n\n"
                f"Original points: {original_points}\n"
                f"Cropped points: {cropped_points}"
            )
            
            print(f"Applied crop: {crop_start} nm to {crop_end} nm")
            print(f"Cropped {len(cropped_samples)}/{total_samples} samples")
            
            return data, success_message
            
        except Exception as e:
            error_msg = f"Failed to crop data: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return None, error_msg
    
    @staticmethod
    def save_cropped_data(data: Dict) -> Optional[Path]:
        """
        Save cropped data to temp_data directory
        
        Args:
            data: Cropped data dictionary
            
        Returns:
            Path to saved file or None if save fails
        """
        try:
            temp_dir = SpectralProcessingService.get_temp_directory()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            metadata = data.get('metadata', {})
            project_name = metadata.get('project_name', 'unknown').replace(' ', '_')
            data_type = metadata.get('data_type', 'cropped')
            
            # Save as JSON
            json_filename = f"{project_name}_{data_type}_cropped_{timestamp}.json"
            json_path = temp_dir / json_filename
            
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"Cropped data saved to: {json_path}")
            return json_path
            
        except Exception as e:
            print(f"Error saving cropped data: {e}")
            import traceback
            traceback.print_exc()
            return None
