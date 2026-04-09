from database.db import get_connection

class DataRepository:

    @staticmethod
    def fetch_filtered(filters: dict):
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT
                id,
                sample_name,
                instrument_id,
                project,
                creation_time
            FROM samples
            WHERE 1=1
        """

        params = []

        # --- Creation Time (optional) ---
        if filters.get("date_from") and filters.get("date_to"):
            query += " AND creation_time BETWEEN ? AND ?"
            params.extend([
                filters["date_from"],
                filters["date_to"]
            ])

        # --- Instrument (optional) ---
        if filters.get("instrument") and filters["instrument"] != "all":
            query += " AND instrument_id = ?"
            params.append(filters["instrument"])

        # --- Project (optional) ---
        if filters.get("project") and filters["project"] != "all":
            query += " AND project = ?"
            params.append(filters["project"])

        cur.execute(query, params)
        rows = cur.fetchall()

        conn.close()
        return rows
