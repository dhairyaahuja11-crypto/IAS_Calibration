"""
Sample Management Service
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG
from database.db import get_connection


class SampleService:
    """Service class for sample management operations"""
    
    @staticmethod
    def get_samples_by_date(date_from, date_to, sample_name=None, user_id=None, sample_status=None):
        """
        INQUIRY BUTTON
        Fetch samples based on creation date range and optional filters
        Each model_data entry (import) is shown as a separate row
        
        Args:
            date_from (str): Start date in 'YYYY-MM-DD' format
            date_to (str): End date in 'YYYY-MM-DD' format
            sample_name (str, optional): Filter by sample name (partial match)
            user_id (str, optional): Filter by user ID (partial match)
            sample_status (str, optional): Filter by sample status ('Not Collected', 'Collected', 'Completed')
            
        Returns:
            list: List of sample dictionaries with all fields
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    md.model_id as id,
                    s.sample_name as sample_name,
                    s.model_num as sample_quantity,
                    s.model_wavemin as initial_wavelength,
                    s.model_wavemax as terminal_wavelength,
                    s.model_wavepath as wavelength_step,
                    s.model_method as scanning_method,
                    CONCAT_WS(', ',
                        CASE 
                            WHEN s.property_value1 IS NOT NULL AND s.property_value1 != '0' AND s.property_value1 != '' 
                            THEN CONCAT(COALESCE(cd1.content_name, 'Substance'), ': ', s.property_value1)
                            ELSE NULL
                        END,
                        CASE 
                            WHEN s.property_value2 IS NOT NULL AND s.property_value2 != '0' AND s.property_value2 != '' 
                            THEN CONCAT(COALESCE(cd2.content_name, 'Substance'), ': ', s.property_value2)
                            ELSE NULL
                        END,
                        CASE 
                            WHEN s.property_value3 IS NOT NULL AND s.property_value3 != '0' AND s.property_value3 != '' 
                            THEN CONCAT(COALESCE(cd3.content_name, 'Substance'), ': ', s.property_value3)
                            ELSE NULL
                        END,
                        CASE 
                            WHEN s.property_value4 IS NOT NULL AND s.property_value4 != '0' AND s.property_value4 != '' 
                            THEN CONCAT(COALESCE(cd4.content_name, 'Substance'), ': ', s.property_value4)
                            ELSE NULL
                        END,
                        CASE 
                            WHEN s.property_value5 IS NOT NULL AND s.property_value5 != '0' AND s.property_value5 != '' 
                            THEN CONCAT(COALESCE(cd5.content_name, 'Substance'), ': ', s.property_value5)
                            ELSE NULL
                        END,
                        CASE 
                            WHEN s.property_value6 IS NOT NULL AND s.property_value6 != '0' AND s.property_value6 != '' 
                            THEN CONCAT(COALESCE(cd6.content_name, 'Substance'), ': ', s.property_value6)
                            ELSE NULL
                        END,
                        CASE 
                            WHEN s.property_value7 IS NOT NULL AND s.property_value7 != '0' AND s.property_value7 != '' 
                            THEN CONCAT(COALESCE(cd7.content_name, 'Substance'), ': ', s.property_value7)
                            ELSE NULL
                        END,
                        CASE 
                            WHEN s.property_value8 IS NOT NULL AND s.property_value8 != '0' AND s.property_value8 != '' 
                            THEN CONCAT(COALESCE(cd8.content_name, 'Substance'), ': ', s.property_value8)
                            ELSE NULL
                        END,
                        CASE 
                            WHEN s.property_value9 IS NOT NULL AND s.property_value9 != '0' AND s.property_value9 != '' 
                            THEN CONCAT(COALESCE(cd9.content_name, 'Substance'), ': ', s.property_value9)
                            ELSE NULL
                        END,
                        CASE 
                            WHEN s.property_value10 IS NOT NULL AND s.property_value10 != '0' AND s.property_value10 != '' 
                            THEN CONCAT(COALESCE(cd10.content_name, 'Substance'), ': ', s.property_value10)
                            ELSE NULL
                        END
                    ) as substance_content,
                    1 as scanned_number,
                    CASE 
                        WHEN s.sample_status = '0' THEN 'Not collected'
                        WHEN s.sample_status = '1' THEN 'Collected'
                        ELSE 'Not collected'
                    END as sample_status,
                    s.create_person as user_id,
                    DATE_FORMAT(md.create_time, '%%Y-%%m-%%d %%H:%%i:%%s') as creation_time,
                    s.sample_id as sample_id
                FROM model_data md
                INNER JOIN sample s ON md.sample_id = s.sample_id
                LEFT JOIN content_dictionary cd1 ON CAST(s.property_name1 AS UNSIGNED) = cd1.id
                LEFT JOIN content_dictionary cd2 ON CAST(s.property_name2 AS UNSIGNED) = cd2.id
                LEFT JOIN content_dictionary cd3 ON CAST(s.property_name3 AS UNSIGNED) = cd3.id
                LEFT JOIN content_dictionary cd4 ON CAST(s.property_name4 AS UNSIGNED) = cd4.id
                LEFT JOIN content_dictionary cd5 ON CAST(s.property_name5 AS UNSIGNED) = cd5.id
                LEFT JOIN content_dictionary cd6 ON CAST(s.property_name6 AS UNSIGNED) = cd6.id
                LEFT JOIN content_dictionary cd7 ON CAST(s.property_name7 AS UNSIGNED) = cd7.id
                LEFT JOIN content_dictionary cd8 ON CAST(s.property_name8 AS UNSIGNED) = cd8.id
                LEFT JOIN content_dictionary cd9 ON CAST(s.property_name9 AS UNSIGNED) = cd9.id
                LEFT JOIN content_dictionary cd10 ON CAST(s.property_name10 AS UNSIGNED) = cd10.id
                WHERE DATE(md.create_time) BETWEEN %s AND %s
                AND (s.sample_state IS NULL OR s.sample_state != 'Deleted')
            """
            
            # Build dynamic WHERE conditions
            params = [date_from, date_to]
            
            if sample_name and sample_name.strip():
                query += " AND s.sample_name LIKE %s"
                params.append(f"%{sample_name.strip()}%")
            
            if user_id and user_id.strip():
                query += " AND s.create_person LIKE %s"
                params.append(f"%{user_id.strip()}%")
            
            if sample_status and sample_status.strip() and sample_status.lower() != 'all':
                # Map UI strings to database values
                status_map = {
                    'not collected': '0',
                    'collected': '1',
                    'completed': '2'
                }
                db_status = status_map.get(sample_status.lower())
                if db_status:
                    query += " AND s.sample_status = %s"
                    params.append(db_status)
            
            query += " ORDER BY md.create_time DESC"
            
            print(f"Executing query with dates: {date_from} to {date_to}, sample_name: {sample_name}, user_id: {user_id}, sample_status: {sample_status}")
            cursor.execute(query, tuple(params))
            samples = cursor.fetchall()
            
            print(f"Found {len(samples)} sample imports (each model_data entry shown separately)")
            
            cursor.close()
            conn.close()
            
            return samples
            
        except Exception as e:
            print(f"Error fetching samples by date: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    @staticmethod
    def get_samples_for_template(sample_ids):
        """
        Fetch sample data with all properties for template export
        
        Args:
            sample_ids (list): List of sample IDs to fetch
            
        Returns:
            list: List of dictionaries with sample data and all property values
        """
        if not sample_ids:
            return []
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Build dynamic query to get all 10 property values
            placeholders = ','.join(['%s'] * len(sample_ids))
            
            # Build SELECT and JOIN clauses dynamically for all 10 properties
            select_parts = ['s.sample_id', 's.sample_name']
            join_parts = []
            
            for i in range(1, 11):
                select_parts.append(f'cd{i}.content_name as property{i}_name')
                select_parts.append(f's.property_value{i}')
                join_parts.append(f'LEFT JOIN content_dictionary cd{i} ON s.property_name{i} = cd{i}.id')
            
            query = f"""
                SELECT 
                    {', '.join(select_parts)}
                FROM sample s
                {' '.join(join_parts)}
                WHERE s.sample_id IN ({placeholders})
                ORDER BY s.sample_id
            """
            
            cursor.execute(query, tuple(sample_ids))
            results = cursor.fetchall()
            
            # Process results into template format
            template_data = []
            for row in results:
                # Build properties dictionary dynamically
                properties = {}
                
                for i in range(1, 11):
                    prop_name_key = f'property{i}_name'
                    prop_value_key = f'property_value{i}'
                    
                    if row[prop_name_key] and row[prop_value_key] and row[prop_value_key] != '0':
                        prop_name = row[prop_name_key].lower()
                        properties[prop_name] = row[prop_value_key]
                
                # Create template row with all found properties
                template_row = {
                    'sample_id': row['sample_id'],
                    'sample_name': row['sample_name']
                }
                
                # Add all properties found (not just protein/oil/moisture)
                template_row.update(properties)
                
                template_data.append(template_row)
            
            cursor.close()
            conn.close()
            
            return template_data
            
        except Exception as e:
            print(f"Error fetching samples for template: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    @staticmethod
    def export_template_to_excel(sample_data, file_path):
        """
        Export sample data to CSV template with dynamic property columns
        
        Args:
            sample_data (list): List of sample dictionaries
            file_path (str): Path where CSV file should be saved
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            import pandas as pd
            
            if not sample_data:
                return False, "No data to export"
            
            # Collect all unique property names across all samples
            all_properties = set()
            for sample in sample_data:
                for key in sample.keys():
                    if key not in ['sample_id', 'sample_name']:
                        all_properties.add(key)
            
            # Sort properties alphabetically for consistent column order
            sorted_properties = sorted(all_properties)
            
            # Prepare data in required format
            export_data = []
            for sample in sample_data:
                row = {
                    "sample ID": sample['sample_id'],
                    "sample name": sample['sample_name']
                }
                
                # Add all properties dynamically (capitalize first letter)
                for prop in sorted_properties:
                    row[prop.capitalize()] = sample.get(prop, '')
                
                export_data.append(row)
            
            # Create DataFrame and export to CSV
            df = pd.DataFrame(export_data)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            return True, f"Successfully exported {len(export_data)} sample(s)"
            
        except Exception as e:
            return False, f"Failed to export template: {str(e)}"
    
    @staticmethod
    def add_sample(sample_data):
        """
        Add a new sample to the database with auto-generated sample_id
        
        Args:
            sample_data (dict): Dictionary containing sample information
            
        Returns:
            tuple: (success: bool, message: str, sample_id: int or None)
        """
        try:
            import uuid
            conn = get_connection()
            cursor = conn.cursor()
            
            # Generate unique sample_id using timestamp + random component
            # Format: YYYYMMDD-HHMMSS-XXXX (e.g., 20260129-153045-A3F2)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            random_suffix = str(uuid.uuid4())[:4].upper()
            new_sample_id = f"{timestamp}-{random_suffix}"
            
            # Get content_dictionary mapping (property name -> id)
            cursor.execute("SELECT id, content_name FROM content_dictionary")
            content_dict = {row['content_name'].lower(): row['id'] for row in cursor.fetchall()}
            
            # Map substance content to property fields (up to 10)
            substance_content = sample_data.get('substance_content', {})
            properties = {}
            
            prop_index = 1
            for name, value in substance_content.items():
                if value and value.strip() and prop_index <= 10:
                    prop_id = content_dict.get(name.lower())
                    if prop_id:
                        properties[f'property_name{prop_index}'] = prop_id
                        properties[f'property_value{prop_index}'] = value
                        prop_index += 1
            
            # Build dynamic INSERT query
            base_fields = ['sample_id', 'sample_name', 'model_num', 'model_wavemin', 'model_wavemax',
                          'model_wavepath', 'model_method', 'sample_status', 'create_person', 'create_time']
            property_fields = []
            
            for i in range(1, 11):
                property_fields.append(f'property_name{i}')
                property_fields.append(f'property_value{i}')
            
            all_fields = base_fields + property_fields
            placeholders = ', '.join(['%s'] * len(all_fields))
            
            query = f"""
                INSERT INTO sample ({', '.join(all_fields)})
                VALUES ({placeholders})
            """
            
            # Build values tuple
            base_values = [
                new_sample_id,
                sample_data.get('sample_name', ''),
                sample_data.get('scanning_quantity', 0),
                sample_data.get('initial_wavelength', 900),
                sample_data.get('terminal_wavelength', 1700),
                sample_data.get('wavelength_step', 1),
                0,  # model_method (scanning method) - default 0
                '0',  # sample_status: 0 = Not collected
                sample_data.get('user_id', ''),
                datetime.now()
            ]
            
            # Add property values (None if not set)
            property_values = []
            for i in range(1, 11):
                property_values.append(properties.get(f'property_name{i}'))
                property_values.append(properties.get(f'property_value{i}'))
            
            values = tuple(base_values + property_values)
            
            cursor.execute(query, values)
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return True, "Sample added successfully", new_sample_id
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error adding sample: {e}")
            import traceback
            traceback.print_exc()
            
            # Check for duplicate entry error
            if "Duplicate entry" in error_msg:
                if sample_data.get('sample_name'):
                    return False, f"Sample name '{sample_data.get('sample_name')}' already exists. Please use a different name.", None
                else:
                    return False, "Duplicate entry error. Sample name may be required or already exists.", None
            
            return False, f"Failed to add sample: {error_msg}", None
    
    @staticmethod
    def update_sample(sample_id, sample_data):
        """
        Update an existing sample in the database
        Merges new properties with existing ones (additive update)
        
        Args:
            sample_id (str): ID of the sample to update
            sample_data (dict): Dictionary containing updated sample information
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get content_dictionary mapping (property name -> id)
            cursor.execute("SELECT id, content_name FROM content_dictionary")
            content_dict = {row['content_name'].lower(): row['id'] for row in cursor.fetchall()}
            reverse_dict = {row['id']: row['content_name'].lower() for row in cursor.fetchall()}
            
            # Fetch existing properties from database
            cursor.execute("""
                SELECT property_name1, property_value1, property_name2, property_value2,
                       property_name3, property_value3, property_name4, property_value4,
                       property_name5, property_value5, property_name6, property_value6,
                       property_name7, property_value7, property_name8, property_value8,
                       property_name9, property_value9, property_name10, property_value10
                FROM sample WHERE sample_id = %s
            """, (sample_id,))
            existing = cursor.fetchone()
            
            # Build existing properties map (name -> value)
            existing_props = {}
            if existing:
                for i in range(1, 11):
                    prop_id = existing.get(f'property_name{i}')
                    prop_value = existing.get(f'property_value{i}')
                    if prop_id and prop_value:
                        if isinstance(prop_id, str):
                            prop_id = int(prop_id)
                        prop_name = reverse_dict.get(prop_id, "").lower()
                        if prop_name:
                            existing_props[prop_name] = prop_value
            
            # Merge with new substance content
            substance_content = sample_data.get('substance_content', {})
            merged_props = existing_props.copy()
            
            # Update/add new properties
            for name, value in substance_content.items():
                if value and value.strip():
                    merged_props[name.lower()] = value
            
            # Convert merged properties back to property slots
            properties = {}
            prop_index = 1
            for name, value in merged_props.items():
                if prop_index <= 10:
                    prop_id = content_dict.get(name.lower())
                    if prop_id:
                        properties[f'property_name{prop_index}'] = prop_id
                        properties[f'property_value{prop_index}'] = value
                        prop_index += 1
            
            # Build dynamic UPDATE query
            set_clauses = [
                'sample_name = %s',
                'model_num = %s',
                'model_wavemin = %s',
                'model_wavemax = %s',
                'model_wavepath = %s',
                'model_method = %s'
            ]
            
            # Add property fields to SET clause
            for i in range(1, 11):
                set_clauses.append(f'property_name{i} = %s')
                set_clauses.append(f'property_value{i} = %s')
            
            query = f"""
                UPDATE sample SET
                    {', '.join(set_clauses)}
                WHERE sample_id = %s
            """
            
            # Build values tuple
            base_values = [
                sample_data.get('sample_name', ''),
                sample_data.get('scan_quantity', 0),
                sample_data.get('initial_wavelength', 900),
                sample_data.get('terminal_wavelength', 1700),
                sample_data.get('wavelength_step', 1),
                0  # model_method (scanning method) - default 0
            ]
            
            # Add property values (None if not set)
            property_values = []
            for i in range(1, 11):
                property_values.append(properties.get(f'property_name{i}'))
                property_values.append(properties.get(f'property_value{i}'))
            
            values = tuple(base_values + property_values + [sample_id])
            
            cursor.execute(query, values)
            conn.commit()
            
            rows_affected = cursor.rowcount
            
            cursor.close()
            conn.close()
            
            if rows_affected > 0:
                return True, "Sample updated successfully"
            else:
                return False, "No sample found with the given ID"
            
        except Exception as e:
            print(f"Error updating sample: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Failed to update sample: {str(e)}"
    
    @staticmethod
    def check_spectral_data(sample_ids):
        """
        Check if samples have spectrogram data in model_data table
        
        Args:
            sample_ids (list): List of sample IDs to check
            
        Returns:
            tuple: (has_data: bool, message: str)
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check if any of the samples have model_data entries
            placeholders = ','.join(['%s'] * len(sample_ids))
            query = f"SELECT COUNT(*) as count FROM model_data WHERE sample_id IN ({placeholders})"
            cursor.execute(query, tuple(sample_ids))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            count = result['count'] if result else 0
            
            if count > 0:
                return True, f"{count} sample(s) have spectrogram data"
            else:
                return False, "No spectrogram data found"
            
        except Exception as e:
            print(f"Error checking spectral data: {e}")
            import traceback
            traceback.print_exc()
            return False, "Error checking spectral data"
    
    @staticmethod
    def delete_samples(sample_ids):
        """
        Delete multiple samples from the database
        
        Args:
            sample_ids (list): List of sample IDs to delete
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not sample_ids:
            return False, "No samples selected for deletion"
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Delete samples (no model_data since it was checked before)
            placeholders = ','.join(['%s'] * len(sample_ids))
            delete_sample_query = f"DELETE FROM sample WHERE sample_id IN ({placeholders})"
            cursor.execute(delete_sample_query, tuple(sample_ids))
            
            conn.commit()
            
            rows_deleted = cursor.rowcount
            
            cursor.close()
            conn.close()
            
            return True, f"Successfully deleted {rows_deleted} sample(s)"
            
        except Exception as e:
            print(f"Error deleting samples: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Failed to delete samples: {str(e)}"
    
    @staticmethod
    def get_sample_by_id(sample_id):
        """
        Fetch a single sample by ID for editing
        
        Args:
            sample_id (int): Sample ID to fetch
            
        Returns:
            dict or None: Sample data dictionary or None if not found
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    sample_id,
                    sample_name,
                    model_num as scan_quantity,
                    model_wavemin as initial_wavelength,
                    model_wavemax as terminal_wavelength,
                    model_wavepath as wavelength_step,
                    model_method as scanning_method,
                    property_name1, property_value1,
                    property_name2, property_value2,
                    property_name3, property_value3,
                    property_name4, property_value4,
                    property_name5, property_value5,
                    property_name6, property_value6,
                    property_name7, property_value7,
                    property_name8, property_value8,
                    property_name9, property_value9,
                    property_name10, property_value10,
                    create_person as user_id
                FROM sample
                WHERE sample_id = %s
            """
            
            cursor.execute(query, (sample_id,))
            sample = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return sample
            
        except Exception as e:
            print(f"Error fetching sample by ID: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def batch_import_substance_content(file_path, selected_sample_ids=None):
        """
        Batch import substance content values from CSV file
        Matches samples by ID or Name and updates property values
        
        Args:
            file_path (str): Path to CSV file with substance content data
            selected_sample_ids (list): List of sample_ids that are selected/checked in UI.
                                       If provided, only these samples will be updated.
            
        Returns:
            tuple: (success: bool, message: str, updated_count: int)
        """
        try:
            import pandas as pd
            
            # Read CSV file
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # Normalize column names (case-insensitive)
            df.columns = df.columns.str.strip().str.lower()
            
            # Check for required columns
            if 'sample id' not in df.columns and 'sample name' not in df.columns:
                return False, "CSV file must contain either 'Sample ID' or 'Sample Name' column", 0
            
            # Get connection
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get content_dictionary mapping (property name -> id)
            cursor.execute("SELECT id, content_name FROM content_dictionary")
            content_dict = {row['content_name'].lower(): row['id'] for row in cursor.fetchall()}
            
            # Auto-detect new parameters from CSV columns and add to content_dictionary
            csv_columns = [col for col in df.columns if col not in ['sample id', 'sample name']]
            new_parameters_added = []
            
            for col_name in csv_columns:
                col_lower = col_name.lower()
                if col_lower not in content_dict:
                    # Add new parameter to content_dictionary
                    try:
                        cursor.execute(
                            "INSERT INTO content_dictionary (content_name) VALUES (%s)",
                            (col_name.title(),)  # Title case: 'ash' -> 'Ash'
                        )
                        new_id = cursor.lastrowid
                        content_dict[col_lower] = new_id
                        new_parameters_added.append(col_name.title())
                        print(f"Added new parameter to content_dictionary: {col_name.title()}")
                    except Exception as e:
                        print(f"Error adding parameter {col_name}: {e}")
            
            if new_parameters_added:
                conn.commit()
                print(f"New parameters added: {', '.join(new_parameters_added)}")
            
            updated_count = 0
            errors = []
            
            # Process each row in CSV
            for idx, row in df.iterrows():
                try:
                    # Get sample ID (model_id from UI) and sample name for matching
                    model_id = None
                    sample_name = None
                    
                    if 'sample id' in df.columns and pd.notna(row['sample id']):
                        value = row['sample id']
                        if isinstance(value, (int, float)):
                            model_id = str(int(value))
                        else:
                            model_id = str(value).strip()
                    
                    if 'sample name' in df.columns and pd.notna(row['sample name']):
                        value = row['sample name']
                        if isinstance(value, (int, float)):
                            sample_name = str(value)
                        else:
                            sample_name = str(value).strip()
                    
                    # Need both ID and name for precise matching
                    if not model_id or not sample_name:
                        errors.append(f"Row {idx+2}: Missing sample ID or sample name")
                        continue
                    
                    # Find sample_ids for this specific model_id (specific import)
                    # This ensures we only update the exact import, not all samples with same name
                    cursor.execute("""
                        SELECT s.sample_id, s.sample_name
                        FROM sample s
                        INNER JOIN model_data md ON s.sample_id = md.sample_id
                        WHERE md.model_id = %s 
                          AND s.sample_name = %s
                          AND (s.sample_state IS NULL OR s.sample_state != 'Deleted')
                    """, (model_id, sample_name))
                    
                    results = cursor.fetchall()
                    if not results:
                        errors.append(f"Row {idx+2}: Sample ID '{model_id}' with name '{sample_name}' not found")
                        continue
                    
                    # Get sample IDs for this specific model_id
                    db_sample_ids = [result['sample_id'] for result in results]
                    
                    # 🔴 FILTER: Only update samples that were selected/checked in UI
                    if selected_sample_ids:
                        db_sample_ids = [
                            sid for sid in db_sample_ids 
                            if str(sid) in [str(s) for s in selected_sample_ids]
                        ]
                        
                        if not db_sample_ids:
                            errors.append(f"Row {idx+2}: Sample ID '{model_id}' not in selected samples")
                            continue
                        
                        if not db_sample_ids:
                            errors.append(f"Row {idx+2}: Sample '{sample_name}' not in selected samples")
                            continue
                    
                    # Extract property values from CSV columns
                    properties = []
                    for col in df.columns:
                        if col not in ['sample id', 'sample name', 'whether the new']:
                            col_clean = col.strip().lower()
                            if col_clean in content_dict and pd.notna(row[col]):
                                property_id = content_dict[col_clean]
                                # Handle numeric values properly
                                value = row[col]
                                if isinstance(value, (int, float)):
                                    property_value = str(value)
                                else:
                                    property_value = str(value).strip()
                                if property_value and property_value != '0' and property_value.lower() != 'nan':
                                    properties.append((property_id, property_value))
                    
                    # Update ALL samples with the same sample_name (all replicates)
                    if properties:
                        update_fields = []
                        update_values = []
                        
                        for i, (prop_id, prop_val) in enumerate(properties[:10], start=1):
                            update_fields.append(f"property_name{i} = %s")
                            update_fields.append(f"property_value{i} = %s")
                            update_values.extend([prop_id, prop_val])
                        
                        # Clear remaining property slots if less than 10 properties
                        for i in range(len(properties) + 1, 11):
                            update_fields.append(f"property_name{i} = NULL")
                            update_fields.append(f"property_value{i} = NULL")
                        
                        update_query = f"UPDATE sample SET {', '.join(update_fields)} WHERE sample_id = %s"
                        
                        # Execute update for EACH sample_id (all replicates get the same properties)
                        for db_sample_id in db_sample_ids:
                            update_values_copy = update_values.copy()
                            update_values_copy.append(db_sample_id)
                            cursor.execute(update_query, tuple(update_values_copy))
                        
                        updated_count += len(db_sample_ids)
                
                except Exception as e:
                    errors.append(f"Row {idx+2}: {str(e)}")
                    continue
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if errors:
                error_msg = "\n".join(errors[:5])  # Show first 5 errors
                if len(errors) > 5:
                    error_msg += f"\n... and {len(errors) - 5} more errors"
                return True, f"Updated {updated_count} sample(s) with warnings:\n{error_msg}", updated_count
            else:
                return True, f"Successfully updated {updated_count} sample(s)", updated_count
            
        except Exception as e:
            print(f"Error in batch import: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Failed to import: {str(e)}", 0
