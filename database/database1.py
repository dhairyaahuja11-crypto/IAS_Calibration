import pymysql
import pandas as pd
import os
import re
import sys

# Import config from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG

def process_samples(
    sampleid_folder_path,
    reference_file_path,
    project_name,
    target,
    db_host=None,
    db_user=None,
    db_password=None,
    db_name=None,
    db_port=None
):
    # Use config values if not provided
    db_host = db_host or DB_CONFIG["host"]
    db_user = db_user or DB_CONFIG["user"]
    db_password = db_password or DB_CONFIG["password"]
    db_name = db_name or DB_CONFIG["database"]
    db_port = db_port or DB_CONFIG["port"]

    # ---------------------------------------------
    # CONNECT TO DATABASE
    # ---------------------------------------------
    try:
        connection = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            port=db_port,
            charset="utf8",
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = connection.cursor()
        cursor.execute("SET time_zone = '+05:30';")
        print("Connected to database.")
    except Exception as e:
        print("Connection failed:", e)
        return

    # ---------------------------------------------
    # DB HELPER FUNCTIONS
    '''
    def get_latest_sample_id():
        cursor.execute("SELECT sample_id FROM sample ORDER BY CAST(sample_id AS UNSIGNED) DESC LIMIT 1;")
        row = cursor.fetchone()
        if not row or not row["sample_id"]:
            return "1"  
        return str(int(row["sample_id"]) + 1)

    # def get_latest_model_id():
    #     cursor.execute("SELECT model_id FROM model_data ORDER BY model_id DESC LIMIT 1;")
    #     row = cursor.fetchone()
    #     return str(int(row["model_id"]) + 1)

    def get_project_sample_id():
        cursor.execute("SELECT id FROM project_sample ORDER BY CAST(id AS UNSIGNED) DESC LIMIT 1;")
        row = cursor.fetchone()
        if not row or not row["id"]:
            return "1"
        return str(int(row["id"]) + 1)

    def get_latest_project_id():
        cursor.execute("SELECT project_id FROM project ORDER BY CAST(project_id AS UNSIGNED) DESC LIMIT 1;")
        row = cursor.fetchone()
        if not row or not row["project_id"]:
            return "1"
        return str(int(row["project_id"]) + 1)



    def get_id_target_name(target):
        cursor.execute("SELECT * FROM content_dictionary;")
        df = pd.DataFrame(cursor.fetchall())
        df["content_name"] = df["content_name"].str.lower()
        target_lower = target.lower()

        # Check if target exists
        if target_lower not in df["content_name"].values:
            # Target not found → insert it into DB
            cursor.execute("INSERT INTO content_dictionary (content_name) VALUES (%s);",(target,))
            connection.commit()

            # Fetch updated table
            cursor.execute("SELECT * FROM content_dictionary;")
            df = pd.DataFrame(cursor.fetchall())
            df["content_name"] = df["content_name"].str.lower()

        # Now fetch the ID safely
        target_id = int(df.loc[df.content_name == target_lower, "id"].values[0])
        return target_id



    def extract_sample_id_and_samplename(filename):
        """
        Extracts the sample ID and batch based on pattern occurrence.
        """
        filename=filename.replace(".csv","")

        # Find the pattern
        pattern = r"_0_(5|3|1)-(1|2|3|4|5)"

        match = re.search(pattern, filename)
        if not match:
            raise ValueError(f"Filename does not match expected pattern: {filename}")

        # Identify the batch (5 characters before the pattern)
        start_index = match.start()
        current_batch = filename[start_index - 5:start_index]

        # Check how many times this batch appears
        occurrence_count = filename.count(current_batch)

        # --- Single Occurrence (Device Format) ---
        if occurrence_count == 1:

            # Find position of the batch
            sample_number= filename[-1]
            pos = filename.find(current_batch)
            if current_batch not in filename:
                raise ValueError(f"Batch '{current_batch}' not found in filename: {filename}")

            # Take everything up to the end of the batch
            prefix_end = pos + len(current_batch)
            extracted = filename[:prefix_end]

            # Split by underscore.
            parts = extracted.split('_')

            # Safety check: Ensure split actually created enough parts
            if len(parts) < 2:
                raise ValueError(f"Expected at least 2 parts, got {len(parts)}: {parts}")

            # take second element and remove last 14 chars
            final_sample_id = parts[1][:-14]

            return final_sample_id,sample_number

        # --- Multiple Occurrences (Qualix Format) ---
        else:
            # Find the FIRST occurrence
            sample_number=filename.split('_')[-2].split('-')[-1]
            pos = filename.find(current_batch)
            if current_batch not in filename:
                raise ValueError(f"Batch '{current_batch}' not found in filename: {filename}")

            prefix_end = pos + len(current_batch)
            extracted = filename[:prefix_end]

            if len(extracted) < 14:
                raise ValueError(f"Expected at least 14 extracted values, got {len(extracted)}: {extracted}")

            # remove last 14 characters
            final_sample_id = extracted[:-14]
            # print(final_sample_id)

            return final_sample_id,sample_number


    # ---------------------------------------------
    # READ REFERENCE FILE
    # ---------------------------------------------
    file_ext = os.path.splitext(reference_file_path)[1].lower()

    if file_ext in ['.csv']:
        refdf = pd.read_csv(reference_file_path)
    elif file_ext in ['.xls', '.xlsx']:
        refdf = pd.read_excel(reference_file_path)
    else:
        raise ValueError(f"Unsupported reference file format: {file_ext}")

    # ---------------------------------------------
    # SCAN SAMPLE FOLDER
    # ---------------------------------------------
    result = {}

    for file in os.listdir(sampleid_folder_path):
        full_path = os.path.join(sampleid_folder_path, file)

        # ---------- CSV directly inside main folder ----------
        if os.path.isfile(full_path) and file.endswith(".csv"):
            try:
                sample_name, sample_number = extract_sample_id_and_samplename(file)
            except ValueError as e:
                raise RuntimeError(f"Sample extraction failed for {file}: {e}")

            if sample_name not in result:
                result[sample_name] = {}

            result[sample_name][sample_number] = [
                pd.read_csv(full_path, skiprows=1, nrows=16),
                pd.read_csv(full_path, skiprows=18),
            ]

        # ---------- CSVs inside subfolders ----------
        elif os.path.isdir(full_path):
            for f in os.listdir(full_path):
                print(f)
                if f.endswith(".csv"):
                    fp = os.path.join(full_path, f)

                    try:
                        sample_name, sample_number = extract_sample_id_and_samplename(f)
                        # print("************************_______________________")
                        # print("************************_______________________")
                        # print(sample_number)
                        # print("************************_______________________")
                        # print("************************_______________________")
                    except ValueError as e:
                        raise RuntimeError(f"Sample extraction failed for {f}: {e}")

                    if sample_name not in result:
                        result[sample_name] = {}

                    result[sample_name][sample_number] = [
                        pd.read_csv(fp, skiprows=1, nrows=16),
                        pd.read_csv(fp, skiprows=18),
                    ]


    # ---------------------------------------------
    # PROCESS EACH SAMPLE
    # ---------------------------------------------
    all_samples=[]
    for sample_name in result:
        sample_id = get_latest_sample_id()
        print(sample_id, "sample ID")
        all_samples.append(sample_id)

        model_wavemin = result[sample_name]["1"][0].loc[
            result[sample_name]["1"][0]["Head:"].str.contains("Start wavelength"),
            "Reference"
        ].values[0]

        model_wavemax = result[sample_name]["1"][0].loc[
            result[sample_name]["1"][0]["Head:"].str.contains("End wavelength"),
            "Reference"
        ].values[0]

        property_name = get_id_target_name(target)
        property_value = refdf.loc[refdf["Sample ID"] == sample_name, target].values[0]

        # ---------------------------------------------
        # INSERT INTO sample TABLE
        # ---------------------------------------------
        insert_sample = """
        INSERT INTO sample (
            sample_id, sample_name, model_num, model_wavemin, model_wavemax,
            model_wavepath, model_method, sample_status,
            property_name1, property_value1,
            create_person, create_time, sample_state
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s)
        """

        cursor.execute(insert_sample, (
            sample_id, sample_name, 0, str(model_wavemin), str(model_wavemax),
            '1', '0', '0',
            str(property_name), str(property_value),
            'automation_script', '1'
            
        ))

        # ---------------------------------------------
        # INSERT INTO model_data TABLE
        # ---------------------------------------------
        insert_model = """
        INSERT INTO model_data (
            sample_id, model_sno, model_order, device_id,
            model_length, wave, absorb, system_temp,create_time
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW())
        """

        for sample_number in result[sample_name]:

            df_meas = result[sample_name][sample_number][1]
            wave = ",".join(df_meas["Wavelength"].astype(str))
            absorb = ",".join(df_meas["Absorbance"].astype(str))

            model_order = sample_number

            cursor.execute(insert_model, (
                sample_id, "", model_order, "30001",
                "801", wave, absorb, "0"
            ))

        print(f"Inserted sample: {sample_name}")

    # ---------------------------------------------
    # INSERT PROJECT ENTRY
    # ---------------------------------------------
    project_id = get_latest_project_id()

    insert_project = """
    INSERT INTO project (
        project_id, project_name, sample_type, analysis_type,
        analysis_object, project_progress, project_remark,
        create_person, create_time, modify_time, project_state
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NULL,%s)
    """

    cursor.execute(insert_project, (
        project_id, project_name, "0", "1",
        str(property_name), "0", "",
        "by_automation_script", "1"
    ))

    for sid in all_samples:
        insert_project_sample = """
        INSERT INTO project_sample (id,project_id,sample_id,new_id,new_name)
        VALUES (%s, %s, %s, %s, %s)"""
        id_var=get_project_sample_id()

        cursor.execute(insert_project_sample,(id_var, project_id, sid, "", ""))



    # Commit all DB changes
    connection.commit()
    print("\nALL DONE — Data inserted successfully!\n")


process_samples(
    sampleid_folder_path=r'C:\Users\Agnext\Desktop\ias_sw\converted\converted',
    reference_file_path=r'C:\Users\Agnext\Desktop\ias_sw\converted\Ref.xlsx',
    project_name="Automation IAS Project1",
    target="Moisture")
'''