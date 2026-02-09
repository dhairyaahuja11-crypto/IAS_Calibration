"""
Data Selection Service - for calibration data selection tab
"""
from database.db import get_connection
from typing import List, Dict, Tuple
import numpy as np


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
            print(f"Error fetching projects: {e}")
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
            print(f"Error fetching instruments: {e}")
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
            
            query = """
                SELECT project_id, project_name, analysis_object, analysis_type, sample_type
                FROM project 
                WHERE project_id = %s
            """
            cursor.execute(query, (project_id,))
            project = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return project if project else {}
            
        except Exception as e:
            print(f"Error fetching project info: {e}")
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
            
            # First check if project has samples
            check_query = """
                SELECT COUNT(*) as count 
                FROM project_sample 
                WHERE project_id = %s
            """
            cursor.execute(check_query, (project_id,))
            result = cursor.fetchone()
            print(f"Debug - Project {project_id} has {result['count']} unique samples in project_sample table")
            
            # Get ONLY the samples that were actually associated with this project
            # No self-join - only fetch samples explicitly stored in project_sample
            query = """
                SELECT 
                    s.sample_id,
                    s.sample_name,
                    s.create_time,
                    s.create_person as user_id,
                    s.property_name1,
                    s.property_value1,
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
            print(f"Debug - Found {len(samples)} samples associated with project")
            
            # Debug: Show sample breakdown
            sample_count = {}
            for sample in samples:
                name = sample.get('sample_name', 'Unknown')
                sample_count[name] = sample_count.get(name, 0) + 1
            print(f"Debug - Sample breakdown:")
            for name, count in sample_count.items():
                print(f"  {name}: {count} replicate(s)")
            
            # Process each record
            for sample in samples:
                # Calculate wavelength points from comma-separated values
                if sample.get('wavelength'):
                    sample['wavelength_points'] = len(sample['wavelength'].split(','))
                else:
                    sample['wavelength_points'] = 0
                
                # Get property name from content_dictionary
                if sample.get('property_name1'):
                    prop_query = """
                        SELECT content_name 
                        FROM content_dictionary 
                        WHERE id = %s
                    """
                    cursor.execute(prop_query, (sample['property_name1'],))
                    prop_result = cursor.fetchone()
                    if prop_result:
                        sample['property_name'] = prop_result['content_name']
                        sample['property_value'] = sample.get('property_value1', '')
                    else:
                        sample['property_name'] = ''
                        sample['property_value'] = ''
                else:
                    sample['property_name'] = ''
                    sample['property_value'] = ''
            
            cursor.close()
            conn.close()
            
            print(f"Debug - Returning {len(samples)} samples from project_sample table")
            return samples
            
        except Exception as e:
            print(f"Error fetching project samples: {e}")
            import traceback
            traceback.print_exc()
            return []
