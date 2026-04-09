"""
Data Selection Service - for calibration data selection tab
"""
from database.db import get_connection
from typing import List, Dict, Tuple
import numpy as np
from services.project_service import ProjectService


class DataSelectionService:
    """
    Service for data selection operations in calibration
    """
    
    @staticmethod
    def get_all_projects() -> List[Dict]:
        """
        Get list of all non-deleted projects
        
        Returns:
            List of project dictionaries with id and name
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT project_id, project_name, sample_type, analysis_type, 
                       analysis_object, project_progress, create_time
                FROM project 
                WHERE project_state IS NULL OR project_state != 'Deleted'
                ORDER BY create_time DESC
            """
            cursor.execute(query)
            
            projects = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return projects
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def get_instruments() -> List[str]:
        """
        Get list of unique instruments from model_data
        
        Returns:
            List of instrument names
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            query = "SELECT DISTINCT device_id FROM model_data WHERE device_id IS NOT NULL ORDER BY device_id"
            cursor.execute(query)
            
            results = cursor.fetchall()
            instruments = [row['device_id'] for row in results]
            
            cursor.close()
            conn.close()
            
            return instruments
            
        except Exception as e:
            return []
    
    @staticmethod
    def get_project_info(project_id: str) -> Dict:
        """
        Get project information including analysis_object
        
        Args:
            project_id: Project ID
            
        Returns:
            Dictionary with project information
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            project = ProjectService.get_project_by_id(project_id)
            
            cursor.close()
            conn.close()
            
            return project if project else {}
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {}
    
    @staticmethod
    def get_project_samples(project_id: str) -> List[Dict]:
        """
        Get all samples that were explicitly associated with a project.
        Returns ONLY the samples stored in project_sample table (no extra replicates).
        
        Args:
            project_id: Project ID
            
        Returns:
            List of sample dictionaries with spectral information
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()

            project_info = DataSelectionService.get_project_info(project_id)
            measurement_index = (project_info.get('analysis_object') or '').strip()
            if ',' in measurement_index:
                measurement_index = measurement_index.split(',', 1)[0].strip()
            
            # First check if project has samples
            check_query = """
                SELECT COUNT(*) as count 
                FROM project_sample 
                WHERE project_id = %s
            """
            cursor.execute(check_query, (project_id,))
            result = cursor.fetchone()
            
            # Get ONLY the samples that were actually associated with this project
            # No self-join - only fetch samples explicitly stored in project_sample
            query = """
                SELECT 
                    s.sample_id,
                    s.sample_name,
                    s.create_time,
                    s.create_person as user_id,
                    s.property_name1, s.property_value1,
                    s.property_name2, s.property_value2,
                    s.property_name3, s.property_value3,
                    s.property_name4, s.property_value4,
                    s.property_name5, s.property_value5,
                    s.property_name6, s.property_value6,
                    s.property_name7, s.property_value7,
                    s.property_name8, s.property_value8,
                    s.property_name9, s.property_value9,
                    s.property_name10, s.property_value10,
                    md.device_id as instrument,
                    md.model_sno as serial_number,
                    md.wave as wavelength,
                    md.absorb as absorbance
                FROM project_sample ps
                INNER JOIN sample s ON ps.sample_id = s.sample_id
                INNER JOIN model_data md ON s.sample_id = md.sample_id
                WHERE ps.project_id = %s
                    AND (s.sample_state IS NULL OR s.sample_state != 'Deleted')
                ORDER BY s.sample_name, md.model_sno
            """
            
            cursor.execute(query, (project_id,))
            samples = cursor.fetchall()
            # Process each record
            for sample in samples:
                # Calculate wavelength points from comma-separated values
                if sample.get('wavelength'):
                    sample['wavelength_points'] = len(sample['wavelength'].split(','))
                else:
                    sample['wavelength_points'] = 0

                sample['property_name'], sample['property_value'] = DataSelectionService._resolve_sample_property(
                    cursor,
                    sample,
                    measurement_index
                )

            # Fill missing property values across scans of the same sample name/timestamp group.
            DataSelectionService._propagate_group_property_values(samples)
            
            cursor.close()
            conn.close()
            
            return samples
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def _resolve_sample_property(cursor, sample: Dict, measurement_index: str = '') -> Tuple[str, str]:
        """Resolve the requested property value from any of the sample's property slots."""
        property_pairs = []

        for idx in range(1, 11):
            property_name_id = sample.get(f'property_name{idx}')
            property_value = sample.get(f'property_value{idx}')
            if not property_name_id:
                continue

            cursor.execute(
                """
                    SELECT content_name
                    FROM content_dictionary
                    WHERE id = %s
                """,
                (property_name_id,)
            )
            prop_result = cursor.fetchone()
            if not prop_result:
                continue

            property_name = (prop_result.get('content_name') or '').strip()
            property_pairs.append((property_name, '' if property_value is None else str(property_value).strip()))

        if not property_pairs:
            return '', ''

        normalized_measurement = measurement_index.casefold()
        if normalized_measurement:
            for property_name, property_value in property_pairs:
                if property_name.casefold() == normalized_measurement:
                    return property_name, property_value

        for property_name, property_value in property_pairs:
            if property_value and property_value != '0':
                return property_name, property_value

        return property_pairs[0]

    @staticmethod
    def _propagate_group_property_values(samples: List[Dict]) -> None:
        """Ensure replicate scan rows share the same resolved property value."""
        grouped_values = {}

        for sample in samples:
            group_key = (
                str(sample.get('sample_name', '')).strip(),
                str(sample.get('create_time', ''))[:16].strip()
            )
            property_name = str(sample.get('property_name', '')).strip()
            property_value = str(sample.get('property_value', '')).strip()

            if property_value and property_value != '0':
                grouped_values[group_key] = (property_name, property_value)

        for sample in samples:
            group_key = (
                str(sample.get('sample_name', '')).strip(),
                str(sample.get('create_time', ''))[:16].strip()
            )
            existing_value = str(sample.get('property_value', '')).strip()
            if existing_value and existing_value != '0':
                continue

            propagated = grouped_values.get(group_key)
            if propagated:
                sample['property_name'], sample['property_value'] = propagated

    @staticmethod
    def _merge_duplicate_sample_scans(samples: List[Dict]) -> List[Dict]:
        """Return one row per sample name, averaging scan spectra when possible."""
        grouped_samples = {}

        for sample in samples:
            sample_name = str(sample.get('sample_name', '')).strip()
            if not sample_name:
                sample_name = str(sample.get('sample_id', '')).strip()

            grouped_samples.setdefault(sample_name, []).append(sample)

        merged_results = []
        for sample_name, group in grouped_samples.items():
            representative = dict(group[0])

            for sample in group:
                property_value = str(sample.get('property_value', '')).strip()
                if property_value and property_value != '0':
                    representative['property_name'] = sample.get('property_name', representative.get('property_name', ''))
                    representative['property_value'] = property_value
                    break

            if len(group) > 1:
                averaged = DataSelectionService._average_group_spectra(group)
                if averaged is not None:
                    representative['wavelength'] = averaged['wavelength']
                    representative['absorbance'] = averaged['absorbance']
                    representative['wavelength_points'] = averaged['wavelength_points']

            representative['replicate_count'] = len(group)
            merged_results.append(representative)

        merged_results.sort(key=lambda sample: sample.get('sample_name', ''))
        return merged_results

    @staticmethod
    def _average_group_spectra(group: List[Dict]):
        """Average absorbance values for scans that share identical wavelength grids."""
        try:
            wavelength_sets = []
            absorbance_sets = []

            for sample in group:
                wavelength_text = str(sample.get('wavelength', '')).strip()
                absorbance_text = str(sample.get('absorbance', '')).strip()
                if not wavelength_text or not absorbance_text:
                    return None

                wavelengths = [float(value.strip()) for value in wavelength_text.split(',') if value.strip()]
                absorbances = [float(value.strip()) for value in absorbance_text.split(',') if value.strip()]
                if not wavelengths or len(wavelengths) != len(absorbances):
                    return None

                wavelength_sets.append(wavelengths)
                absorbance_sets.append(absorbances)

            reference = wavelength_sets[0]
            if any(current != reference for current in wavelength_sets[1:]):
                return None

            absorbance_array = np.array(absorbance_sets, dtype=float)
            averaged_absorbance = absorbance_array.mean(axis=0).tolist()

            return {
                'wavelength': ','.join(str(value) for value in reference),
                'absorbance': ','.join(str(value) for value in averaged_absorbance),
                'wavelength_points': len(reference)
            }
        except Exception:
            return None
