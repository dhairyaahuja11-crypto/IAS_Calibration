"""
Project Service - Business logic and database operations for Project Management
"""
import pymysql
from config import DB_CONFIG
from datetime import datetime
import random


class ProjectService:
    @staticmethod
    def _log(message):
        """Keep service-level terminal output quiet."""
        return
    
    @staticmethod
    def _get_db_connection():
        """Get database connection with READ COMMITTED isolation level for data visibility."""
        try:
            conn = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                port=DB_CONFIG['port'],
                charset=DB_CONFIG['charset'],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            # Set transaction isolation to READ COMMITTED to see latest committed data
            cursor = conn.cursor()
            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
            cursor.close()
            return conn
        except Exception:
            return None
    
    @staticmethod
    def get_projects_by_filters(date_from, date_to, status=None, measurement_type=None, 
                                 project_name=None, sample_type=None, user_id=None):
        """
        Fetch projects from database based on filters
        
        Args:
            date_from (str): Start date in 'YYYY-MM-DD' format
            date_to (str): End date in 'YYYY-MM-DD' format
            status (str, optional): Project status filter
            measurement_type (str, optional): Measurement type filter (analysis_type)
            project_name (str, optional): Project name filter (partial match)
            sample_type (str, optional): Sample type filter
            user_id (str, optional): User ID filter (partial match)
            
        Returns:
            list: List of project dictionaries with all fields
        """
        try:
            conn = ProjectService._get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            # Build dynamic query with filters
            query = """
                SELECT 
                    project_id,
                    project_name,
                    sample_type,
                    analysis_type as measurement_type,
                    analysis_object as measurement_index,
                    project_state as status,
                    create_person as user_id,
                    project_remark as remark,
                    create_time as creation_time,
                    modify_time as modification_time,
                    project_state
                FROM project
                WHERE (project_state IS NULL OR project_state != 'Deleted')
            """
            
            params = []

            if date_from and date_to:
                query += " AND DATE(create_time) BETWEEN %s AND %s"
                params.extend([date_from, date_to])
            elif date_from:
                query += " AND DATE(create_time) >= %s"
                params.append(date_from)
            elif date_to:
                query += " AND DATE(create_time) <= %s"
                params.append(date_to)
            
            # Add optional filters
            if status and status.lower() != 'all':
                query += " AND project_state = %s"
                params.append(status)
            
            if measurement_type and measurement_type.lower() != 'all':
                measurement_type_value = measurement_type.strip().lower()
                if measurement_type_value.startswith('qual'):
                    query += " AND analysis_type IN (%s, %s)"
                    params.extend(['Qual', 'Qualitative'])
                elif measurement_type_value.startswith('quan'):
                    query += " AND analysis_type IN (%s, %s)"
                    params.extend(['Quan', 'Quantitative'])
                else:
                    query += " AND analysis_type = %s"
                    params.append(measurement_type)
            
            if project_name and project_name.strip():
                query += " AND project_name LIKE %s"
                params.append(f"%{project_name}%")
            
            if sample_type and sample_type.lower() != 'all':
                query += " AND sample_type = %s"
                params.append(sample_type)
            
            if user_id and user_id.strip():
                query += " AND create_person LIKE %s"
                params.append(f"%{user_id.strip()}%")
            
            query += " ORDER BY create_time DESC"
            
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return results
            
        except Exception:
            import traceback
            traceback.print_exc()
            return []

    @staticmethod
    def project_name_exists(project_name, exclude_project_id=None):
        """Check whether a non-deleted project already uses the given name."""
        try:
            normalized_name = (project_name or '').strip()
            if not normalized_name:
                return False

            conn = ProjectService._get_db_connection()
            if not conn:
                return False

            cursor = conn.cursor()
            query = """
                SELECT project_id
                FROM project
                WHERE LOWER(TRIM(project_name)) = LOWER(%s)
                AND (project_state IS NULL OR project_state != 'Deleted')
            """
            params = [normalized_name]

            if exclude_project_id:
                query += " AND project_id != %s"
                params.append(str(exclude_project_id))

            query += " LIMIT 1"
            cursor.execute(query, tuple(params))
            result = cursor.fetchone()

            cursor.close()
            conn.close()
            return result is not None

        except Exception:
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def delete_project(project_id):
        """
        Delete a project and all associated sample links
        
        Args:
            project_id (str): ID of the project to delete
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if not project_id:
                return False, "Project ID is required"
            
            conn = ProjectService._get_db_connection()
            if not conn:
                return False, "Failed to connect to database"
            
            cursor = conn.cursor()
            
            # Start transaction
            conn.begin()
            
            try:
                # Soft delete: Mark project as deleted
                cursor.execute("""
                    UPDATE project 
                    SET project_state = 'Deleted'
                    WHERE project_id = %s
                """, (project_id,))
                
                if cursor.rowcount == 0:
                    conn.rollback()
                    return False, f"Project '{project_id}' not found"
                
                # Commit transaction
                conn.commit()
                cursor.close()
                conn.close()
                
                return True, f"Project '{project_id}' deleted successfully"
                
            except Exception as e:
                conn.rollback()
                raise e
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Error deleting project: {str(e)}"
    
    @staticmethod
    def get_project_by_id(project_id):
        """
        Get a single project by ID
        
        Args:
            project_id (str): Project ID
            
        Returns:
            dict or None: Project data dictionary or None if not found
        """
        try:
            conn = ProjectService._get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    project_id,
                    project_name,
                    sample_type,
                    analysis_type as measurement_type,
                    analysis_object as measurement_index,
                    project_state as status,
                    create_person as user_id,
                    project_remark as remark,
                    create_time as creation_time,
                    modify_time as modification_time,
                    project_state
                FROM project
                WHERE project_id = %s
            """
            
            cursor.execute(query, (project_id,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return result
            
        except Exception:
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_project_samples(project_id):
        """
        Get all samples associated with a project
        
        Args:
            project_id (str): Project ID
            
        Returns:
            list: List of sample dictionaries
        """
        try:
            conn = ProjectService._get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            # Check if project_sample linking table exists
            cursor.execute("SHOW TABLES LIKE 'project_sample'")
            has_linking_table = cursor.fetchone() is not None
            
            if has_linking_table:
                cursor.execute(
                    """
                        SELECT sample_id
                        FROM project_sample
                        WHERE project_id = %s
                    """,
                    (project_id,)
                )
                linked_rows = cursor.fetchall()
                sample_ids = [str(row['sample_id']).strip() for row in linked_rows if row.get('sample_id')]

                if not sample_ids:
                    cursor.close()
                    conn.close()
                    return []

                placeholders = ','.join(['%s'] * len(sample_ids))
                query = f"""
                    SELECT
                        s.sample_id,
                        s.sample_id as id,
                        s.sample_name,
                        s.model_num as sample_quantity,
                        1 as scanned_number,
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
                        s.model_method as scanning_method,
                        CASE
                            WHEN s.sample_status = '0' THEN 'Not collected'
                            WHEN s.sample_status = '1' THEN 'Collected'
                            WHEN s.sample_status = '2' THEN 'Completed'
                            ELSE COALESCE(s.sample_status, 'Not collected')
                        END as sample_status,
                        s.create_person as user_id,
                        DATE_FORMAT(s.create_time, '%%Y-%%m-%%d %%H:%%i:%%s') as creation_time
                    FROM sample s
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
                    WHERE s.sample_id IN ({placeholders})
                    AND (s.sample_state IS NULL OR s.sample_state != 'Deleted')
                    ORDER BY s.create_time DESC
                """
                params = tuple(sample_ids)
            else:
                # Direct relationship
                query = """
                    SELECT 
                        sample_id,
                        sample_id as id,
                        sample_name,
                        model_num as sample_quantity,
                        1 as scanned_number,
                        CONCAT_WS(', ',
                            CASE 
                                WHEN property_value1 IS NOT NULL AND property_value1 != '0' AND property_value1 != '' 
                                THEN CONCAT(COALESCE(cd1.content_name, 'Substance'), ': ', property_value1)
                                ELSE NULL
                            END,
                            CASE 
                                WHEN property_value2 IS NOT NULL AND property_value2 != '0' AND property_value2 != '' 
                                THEN CONCAT(COALESCE(cd2.content_name, 'Substance'), ': ', property_value2)
                                ELSE NULL
                            END,
                            CASE 
                                WHEN property_value3 IS NOT NULL AND property_value3 != '0' AND property_value3 != '' 
                                THEN CONCAT(COALESCE(cd3.content_name, 'Substance'), ': ', property_value3)
                                ELSE NULL
                            END,
                            CASE 
                                WHEN property_value4 IS NOT NULL AND property_value4 != '0' AND property_value4 != '' 
                                THEN CONCAT(COALESCE(cd4.content_name, 'Substance'), ': ', property_value4)
                                ELSE NULL
                            END,
                            CASE 
                                WHEN property_value5 IS NOT NULL AND property_value5 != '0' AND property_value5 != '' 
                                THEN CONCAT(COALESCE(cd5.content_name, 'Substance'), ': ', property_value5)
                                ELSE NULL
                            END,
                            CASE 
                                WHEN property_value6 IS NOT NULL AND property_value6 != '0' AND property_value6 != '' 
                                THEN CONCAT(COALESCE(cd6.content_name, 'Substance'), ': ', property_value6)
                                ELSE NULL
                            END,
                            CASE 
                                WHEN property_value7 IS NOT NULL AND property_value7 != '0' AND property_value7 != '' 
                                THEN CONCAT(COALESCE(cd7.content_name, 'Substance'), ': ', property_value7)
                                ELSE NULL
                            END,
                            CASE 
                                WHEN property_value8 IS NOT NULL AND property_value8 != '0' AND property_value8 != '' 
                                THEN CONCAT(COALESCE(cd8.content_name, 'Substance'), ': ', property_value8)
                                ELSE NULL
                            END,
                            CASE 
                                WHEN property_value9 IS NOT NULL AND property_value9 != '0' AND property_value9 != '' 
                                THEN CONCAT(COALESCE(cd9.content_name, 'Substance'), ': ', property_value9)
                                ELSE NULL
                            END,
                            CASE 
                                WHEN property_value10 IS NOT NULL AND property_value10 != '0' AND property_value10 != '' 
                                THEN CONCAT(COALESCE(cd10.content_name, 'Substance'), ': ', property_value10)
                                ELSE NULL
                            END
                        ) as substance_content,
                        model_method as scanning_method,
                        CASE 
                            WHEN sample_status = '0' THEN 'Not collected'
                            WHEN sample_status = '1' THEN 'Collected'
                            WHEN sample_status = '2' THEN 'Completed'
                            ELSE COALESCE(sample_status, 'Not collected')
                        END as sample_status,
                        create_person as user_id,
                        create_time as creation_time
                    FROM sample
                    LEFT JOIN content_dictionary cd1 ON CAST(property_name1 AS UNSIGNED) = cd1.id
                    LEFT JOIN content_dictionary cd2 ON CAST(property_name2 AS UNSIGNED) = cd2.id
                    LEFT JOIN content_dictionary cd3 ON CAST(property_name3 AS UNSIGNED) = cd3.id
                    LEFT JOIN content_dictionary cd4 ON CAST(property_name4 AS UNSIGNED) = cd4.id
                    LEFT JOIN content_dictionary cd5 ON CAST(property_name5 AS UNSIGNED) = cd5.id
                    LEFT JOIN content_dictionary cd6 ON CAST(property_name6 AS UNSIGNED) = cd6.id
                    LEFT JOIN content_dictionary cd7 ON CAST(property_name7 AS UNSIGNED) = cd7.id
                    LEFT JOIN content_dictionary cd8 ON CAST(property_name8 AS UNSIGNED) = cd8.id
                    LEFT JOIN content_dictionary cd9 ON CAST(property_name9 AS UNSIGNED) = cd9.id
                    LEFT JOIN content_dictionary cd10 ON CAST(property_name10 AS UNSIGNED) = cd10.id
                    WHERE project_id = %s
                    ORDER BY create_time DESC
                """
                params = (project_id,)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return results
            
        except Exception:
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def update_project(project_id, project_data, selected_samples=None):
        """
        Update an existing project
        
        Args:
            project_id (str): ID of the project to update
            project_data (dict): Updated project information
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if not project_id:
                return False, "Project ID is required"
            
            conn = ProjectService._get_db_connection()
            if not conn:
                return False, "Failed to connect to database"
            
            cursor = conn.cursor()
            
            # Prepare data
            project_name = project_data.get('project_name', '').strip()[:500]
            sample_type = project_data.get('sample_type', '')[:10]

            if ProjectService.project_name_exists(project_name, exclude_project_id=project_id):
                return False, f"Project name '{project_name}' already exists. Please use a different name."
            
            # Map measurement_type to analysis_type
            measurement_type = project_data.get('measurement_type', '')
            if measurement_type.lower().startswith('qual'):
                analysis_type = 'Qual'
            elif measurement_type.lower().startswith('quan'):
                analysis_type = 'Quan'
            else:
                analysis_type = measurement_type[:10]
            
            # Convert measurement_index list to comma-separated string
            measurement_indexes = project_data.get('measurement_index', [])
            analysis_object = ','.join(measurement_indexes)[:200]
            
            project_remark = project_data.get('remark', '').strip()[:1000]
            
            # Update timestamp
            modify_time = datetime.now()
            
            # Update project in database
            update_query = """
                UPDATE project SET
                    project_name = %s,
                    sample_type = %s,
                    analysis_type = %s,
                    analysis_object = %s,
                    project_remark = %s,
                    modify_time = %s,
                    project_state = %s
                WHERE project_id = %s
            """
            
            cursor.execute(update_query, (
                project_name,
                sample_type,
                analysis_type,
                analysis_object,
                project_remark,
                modify_time,
                'Modified',
                project_id
            ))
            
            if cursor.rowcount == 0:
                return False, f"Project '{project_id}' not found"

            # Keep the project/sample links in sync with the modified selection.
            if selected_samples is not None:
                cursor.execute("SHOW TABLES LIKE 'project_sample'")
                has_linking_table = cursor.fetchone() is not None

                normalized_sample_ids = []
                for sample in selected_samples:
                    sample_id = sample.get('sample_id') if isinstance(sample, dict) else getattr(sample, 'sample_id', None)
                    if sample_id is not None and str(sample_id).strip():
                        normalized_sample_ids.append(str(sample_id).strip())

                if has_linking_table:
                    cursor.execute("DELETE FROM project_sample WHERE project_id = %s", (project_id,))
                    unique_sample_ids = list(dict.fromkeys(normalized_sample_ids))
                    if unique_sample_ids:
                        values = [
                            (f"{project_id}_{sample_id}", project_id, sample_id)
                            for sample_id in unique_sample_ids
                        ]
                        cursor.executemany(
                            "INSERT INTO project_sample (id, project_id, sample_id) VALUES (%s, %s, %s)",
                            values
                        )
                else:
                    cursor.execute("UPDATE sample SET project_id = NULL WHERE project_id = %s", (project_id,))
                    unique_sample_ids = list(dict.fromkeys(normalized_sample_ids))
                    if unique_sample_ids:
                        cursor.executemany(
                            "UPDATE sample SET project_id = %s WHERE sample_id = %s",
                            [(project_id, sample_id) for sample_id in unique_sample_ids]
                        )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True, f"Project '{project_name}' updated successfully!"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Error updating project: {str(e)}"
    
    @staticmethod
    def create_project(project_data, selected_samples):
        """
        Create a new project and associate samples with it
        
        Args:
            project_data (dict): Project information containing:
                - project_name (str): Name of the project
                - sample_type (str): Type of samples (Granules/Powder/Liquid)
                - measurement_type (str): Type of measurement (Qualitative/Quantitative)
                - measurement_index (list): List of selected measurement parameters
                - remark (str): Project remarks/notes
                - user_id (str): User who created the project
            selected_samples (list): List of sample dictionaries with sample IDs
            
        Returns:
            tuple: (success: bool, message: str, project_id: int or None)
        """
        try:
            # Validate required fields
            if not project_data.get('project_name'):
                return False, "Project name is required", None
            
            if not selected_samples:
                return False, "Please select at least one sample", None
            
            if not project_data.get('measurement_index'):
                return False, "Please select at least one measurement index", None
            
            conn = ProjectService._get_db_connection()
            if not conn:
                return False, "Failed to connect to database", None
            
            cursor = conn.cursor()
            
            # Start transaction to ensure atomic auto-increment
            conn.begin()
            
            try:
                # Lock the table and get the next project_id
                cursor.execute("SELECT MAX(CAST(project_id AS UNSIGNED)) as max_id FROM project FOR UPDATE")
                result = cursor.fetchone()
                
                if result and result['max_id'] is not None:
                    project_id = str(result['max_id'] + 1)
                else:
                    project_id = "1"
                
                
                # Prepare data for database insertion
                project_name = project_data.get('project_name', '').strip()[:500]
                sample_type = project_data.get('sample_type', '')[:10]

                if ProjectService.project_name_exists(project_name):
                    conn.rollback()
                    cursor.close()
                    conn.close()
                    return False, f"Project name '{project_name}' already exists. Please use a different name.", None
                
                # Map measurement_type to analysis_type
                measurement_type = project_data.get('measurement_type', '')
                if measurement_type.lower().startswith('qual'):
                    analysis_type = 'Qual'
                elif measurement_type.lower().startswith('quan'):
                    analysis_type = 'Quan'
                else:
                    analysis_type = measurement_type[:10]
                
                # Convert measurement_index list to comma-separated string for analysis_object
                measurement_indexes = project_data.get('measurement_index', [])
                analysis_object = ','.join(measurement_indexes)[:200]  # varchar(200) limit
                
                # Get remark and user_id
                project_remark = project_data.get('remark', '').strip()[:1000]
                create_person = project_data.get('user_id', '').strip()[:20]
                
                # Set initial state and progress
                project_state = 'Created'[:10]
                project_progress = 'New'[:10]  # Initial progress status
                
                # Get current timestamp
                current_time = datetime.now()
                
                # Insert project into database
                insert_query = """
                    INSERT INTO project (
                        project_id,
                        project_name,
                        sample_type,
                        analysis_type,
                        analysis_object,
                        project_progress,
                        project_remark,
                        create_person,
                        create_time,
                        modify_time,
                        project_state
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(insert_query, (
                    project_id,
                    project_name,
                    sample_type,
                    analysis_type,
                    analysis_object,
                    project_progress,
                    project_remark,
                    create_person,
                    current_time,
                    current_time,
                    project_state
                ))
                
                print(f"✓ Project inserted successfully with ID: {project_id}")
                
                # Associate samples with the project
                # Check if project_sample linking table exists
                cursor.execute("SHOW TABLES LIKE 'project_sample'")
                has_linking_table = cursor.fetchone() is not None
                
                if has_linking_table:
                    # Store ALL numeric sample IDs including replicates
                    all_sample_ids = []
                    for sample in selected_samples:
                        sample_id = sample.get('sample_id')
                        if sample_id and str(sample_id).strip():
                            all_sample_ids.append(str(sample_id).strip())
                    # Bulk insert all samples
                    if all_sample_ids:
                        values = [(f"{project_id}_{sample_id}", project_id, sample_id) for sample_id in all_sample_ids]
                        sql = "INSERT INTO project_sample (id, project_id, sample_id) VALUES (%s, %s, %s)"
                        cursor.executemany(sql, values)
                else:
                    # Update samples directly to reference the project
                    for sample in selected_samples:
                        sample_id = sample.get('sample_id')
                        if sample_id:
                            cursor.execute("""
                                UPDATE sample SET project_id = %s WHERE sample_id = %s
                            """, (project_id, sample_id))
                
                # Commit transaction
                conn.commit()
                cursor.close()
                conn.close()
                
                sample_count = len(selected_samples)
                success_msg = f"Project '{project_name}' created successfully with {sample_count} sample(s)!"
                return True, success_msg, project_id
                
            except Exception as e:
                # Rollback on error
                conn.rollback()
                raise e
            
        except Exception as e:
            print(f"Error creating project: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error creating project: {str(e)}", None
