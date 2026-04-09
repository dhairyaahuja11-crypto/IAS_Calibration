"""
Shared service for spectral data import operations.
Provides common functionality for CSV parsing, metadata extraction, and database operations.
"""
import pandas as pd
from datetime import datetime


class SpectralImportService:
    """Service class for handling spectral data import operations."""

    @staticmethod
    def _extract_wave_range(data_df):
        """Return min/max wavelengths from a parsed CSV dataframe."""
        model_wavemin = "900"
        model_wavemax = "1700"

        if 'Wavelength' in data_df.columns and len(data_df) > 0:
            wavelengths = data_df['Wavelength'].values
            model_wavemin = str(int(wavelengths[0]))
            model_wavemax = str(int(wavelengths[-1]))

        return model_wavemin, model_wavemax

    @staticmethod
    def create_sample_record(conn, sample_name, creation_time=None, scan_quantity=0):
        """Insert a sample row and return its generated sample_id."""
        cursor = None
        try:
            cursor = conn.cursor()

            if creation_time is None:
                creation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            sample_id = SpectralImportService.generate_sample_id(cursor)
            sample_name_truncated = sample_name[:50] if len(sample_name) > 50 else sample_name

            try:
                import getpass
                create_person = getpass.getuser()[:20]
            except Exception:
                create_person = 'import_user'

            cursor.execute(
                """
                INSERT INTO sample (
                    sample_id, sample_name, model_num, model_wavemin, model_wavemax,
                    model_wavepath, model_method, sample_status,
                    create_person, create_time, sample_state
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    sample_id,
                    sample_name_truncated,
                    scan_quantity,
                    '900',
                    '1700',
                    '1',
                    '0',
                    '0',
                    create_person,
                    creation_time,
                    '1'
                )
            )
            return sample_id
        finally:
            if cursor:
                cursor.close()

    @staticmethod
    def insert_scan_for_sample(
        conn,
        sample_id,
        instrument,
        scan_name,
        data_df,
        absorb_points,
        creation_time=None,
        system_temp='0',
        model_order=1,
        update_sample_range=False
    ):
        """Insert one scan row into model_data for an existing sample."""
        cursor = None
        try:
            cursor = conn.cursor()

            if creation_time is None:
                creation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            model_sno = (scan_name or str(model_order))[:50]

            if 'Wavelength' in data_df.columns and 'Absorbance' in data_df.columns:
                wave = ",".join(data_df['Wavelength'].astype(str).tolist())
                absorb = ",".join(data_df['Absorbance'].astype(str).tolist())
                cursor.execute(
                    """
                    INSERT INTO model_data (
                        sample_id, model_sno, model_order, device_id,
                        model_length, wave, absorb, system_temp, create_time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        sample_id,
                        model_sno,
                        str(model_order),
                        instrument,
                        str(absorb_points),
                        wave,
                        absorb,
                        system_temp,
                        creation_time
                    )
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO model_data (
                        sample_id, model_sno, model_order, device_id,
                        model_length, system_temp, create_time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        sample_id,
                        model_sno,
                        str(model_order),
                        instrument,
                        str(absorb_points),
                        system_temp,
                        creation_time
                    )
                )

            if update_sample_range:
                model_wavemin, model_wavemax = SpectralImportService._extract_wave_range(data_df)
                cursor.execute(
                    """
                    UPDATE sample
                    SET model_num = GREATEST(COALESCE(model_num, 0), %s),
                        model_wavemin = %s,
                        model_wavemax = %s
                    WHERE sample_id = %s
                    """,
                    (int(model_order), model_wavemin, model_wavemax, sample_id)
                )
        finally:
            if cursor:
                cursor.close()
    
    @staticmethod
    def extract_csv_header_metadata(file_path):
        """
        Extract metadata from CSV header rows (rows 1-18).
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            dict: Header metadata containing detector_temp, humidity, serial_number, creation_time
        """
        header_data = {
            'detector_temp': '0.0',
            'humidity': '0.0',
            'serial_number': '',
            'creation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            # Read CSV file
            df = pd.read_csv(file_path, header=None, skiprows=0, on_bad_lines='skip', encoding='utf-8')
            
            # Extract from specific rows (0-indexed)
            # Row 4: Detector Temp hundredths
            if len(df) > 3:
                try:
                    detector_val = df.iloc[3, 1]  # Column B (index 1)
                    if pd.notna(detector_val):
                        detector_val = float(detector_val) / 100.0
                        header_data['detector_temp'] = f"{detector_val:.2f}"
                except (ValueError, IndexError):
                    pass
            
            # Row 5: Humidity hundredths
            if len(df) > 4:
                try:
                    humidity_val = df.iloc[4, 1]  # Column B (index 1)
                    if pd.notna(humidity_val):
                        humidity_val = float(humidity_val) / 100.0
                        header_data['humidity'] = f"{humidity_val:.2f}"
                except (ValueError, IndexError):
                    pass
            
            # Row 8: Serial Number
            if len(df) > 7:
                try:
                    serial_val = df.iloc[7, 1]  # Column B (index 1)
                    if pd.notna(serial_val):
                        header_data['serial_number'] = str(serial_val).strip()
                except (ValueError, IndexError):
                    pass
            
            print(f"Extracted header metadata: {header_data}")
            return header_data
            
        except Exception as e:
            print(f"Error extracting CSV header metadata: {e}")
            import traceback
            traceback.print_exc()
            return header_data
    
    @staticmethod
    def generate_sample_id(cursor):
        """
        Generate unique sample_id by finding max existing ID and incrementing.
        
        Args:
            cursor: Database cursor
            
        Returns:
            str: New unique sample_id
        """
        try:
            query = "SELECT MAX(CAST(sample_id AS UNSIGNED)) as max_id FROM sample"
            cursor.execute(query)
            result = cursor.fetchone()
            max_id = result['max_id'] if result['max_id'] else 0
            return str(max_id + 1)
        except:
            return str(int(datetime.now().timestamp()))
    
    @staticmethod
    def insert_sample_to_db(conn, sample_name, instrument, lot_number, absorb_points, 
                           wavelength_str, absorbance_str, data_df, 
                           detector_temp='0', humidity='0', creation_time=None):
        """
        Insert sample data into database tables (sample and model_data).
        
        Args:
            conn: Database connection
            sample_name: Name of the sample
            instrument: Instrument/device ID
            lot_number: Lot number
            absorb_points: Number of wavelength points
            wavelength_str: Comma-separated wavelength values
            absorbance_str: Comma-separated absorbance values
            data_df: DataFrame containing spectral data
            detector_temp: Detector temperature (default: '0')
            humidity: Humidity value (default: '0')
            creation_time: Creation timestamp (default: current time)
            
        Returns:
            str: sample_id if successful, None otherwise
        """
        cursor = None
        try:
            cursor = conn.cursor()
            
            if creation_time is None:
                creation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Generate unique sample_id
            sample_id = SpectralImportService.generate_sample_id(cursor)
            print(f"Generated sample_id: {sample_id}")
            
            # Extract wavelength range from actual data
            model_wavemin, model_wavemax = SpectralImportService._extract_wave_range(data_df)
            
            print(f"Wave range: {model_wavemin} - {model_wavemax}")
            
            # Truncate sample_name to 50 chars and set create_person to Windows username (max 20 chars)
            sample_name_truncated = sample_name[:50] if len(sample_name) > 50 else sample_name
            try:
                import getpass
                create_person = getpass.getuser()[:20]
            except Exception:
                create_person = 'import_user'
            
            # ===== INSERT INTO sample TABLE =====
            insert_sample = """
            INSERT INTO sample (
                sample_id, sample_name, model_num, model_wavemin, model_wavemax,
                model_wavepath, model_method, sample_status,
                create_person, create_time, sample_state
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            print(f"Inserting into sample table:")
            print(f"  - sample_id: {sample_id}")
            print(f"  - sample_name: {sample_name_truncated}")
            print(f"  - instrument: {instrument}")
            print(f"  - lot_number: {lot_number}")
            print(f"  - creation_time: {creation_time} (batch timestamp)")
            
            cursor.execute(insert_sample, (
                sample_id, 
                sample_name_truncated, 
                0, 
                model_wavemin, 
                model_wavemax,
                '1', 
                '0', 
                '0',
                create_person,
                creation_time,
                '1'
            ))
            print(f"Successfully inserted into sample table")
            
            # ===== INSERT INTO model_data TABLE =====
            if 'Wavelength' in data_df.columns and 'Absorbance' in data_df.columns:
                wave = ",".join(data_df['Wavelength'].astype(str).tolist())
                absorb = ",".join(data_df['Absorbance'].astype(str).tolist())
                
                insert_model = """
                INSERT INTO model_data (
                    sample_id, model_sno, model_order, device_id,
                    model_length, wave, absorb, system_temp, create_time
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                print(f"Inserting into model_data table with device_id: {instrument}")
                cursor.execute(insert_model, (
                    sample_id,
                    lot_number,
                    "1",
                    instrument,
                    str(absorb_points),
                    wave,
                    absorb,
                    "0",
                    creation_time
                ))
                print(f"Successfully inserted into model_data table")
            else:
                print(f"Warning: Wavelength/Absorbance not found in data_df")
                # Still insert even without spectral data
                insert_model = """
                INSERT INTO model_data (
                    sample_id, model_sno, model_order, device_id,
                    model_length, system_temp, create_time
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(insert_model, (
                    sample_id,
                    lot_number,
                    "1",
                    instrument,
                    str(absorb_points),
                    "0"
                ))
            
            # Commit all changes
            conn.commit()
            print(f"✓ Successfully inserted sample: {sample_id} - {sample_name}")
            print(f"  Instrument: {instrument}, Lot: {lot_number}")
            return sample_id
            
        except Exception as e:
            print(f"✗ Error inserting sample: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
            except:
                pass
            return None
        finally:
            if cursor:
                cursor.close()
