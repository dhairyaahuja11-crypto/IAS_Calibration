from backend.database import Database

class InstrumentService:
    def __init__(self):
        self.db = Database()

    def add_instrument(self, data):
        conn = self.db.get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO instruments (
                name, instrument_id, sample_type, workflow,
                instrument_type, initial_wl, terminal_wl,
                points, resolution, avg_num, light_mode,
                turntable, creation_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["name"],
            data["instrument_id"],
            data["sample_type"],
            data["workflow"],
            data["instrument_type"],
            data["initial_wl"],
            data["terminal_wl"],
            data["points"],
            data["resolution"],
            data["avg_num"],
            data["light_mode"],
            int(data["turntable"]),
            data["creation_date"]
        ))

        conn.commit()
        conn.close()
