import sqlite3
import hashlib
import io

def fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    return buf.read()

class DBPlots:
    def __init__(self, db_path="plots.db"):
        self.db = sqlite3.connect(db_path)
        self.cur = self.db.cursor()
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS plots (
                filepath TEXT,
                file_content_hash TEXT,
                image BLOB,
                PRIMARY KEY (filepath, file_content_hash)
            )
        """)
        self.db.commit()

    def add_fig(self, rfdata, fig):
        # Check if an entry for this filepath already exists
        self.cur.execute(
            "SELECT file_content_hash FROM plots WHERE filepath = ?",
            (rfdata.filepath,)
        )
        row = self.cur.fetchone()
        if row:
            existing_hash = row[0]
            # Skip if file content hasn't changed
            #if existing_hash == rfdata.h:
            #    return existing_hash

            # Otherwise, update the existing record
            image_bytes = fig_to_bytes(fig)
            self.cur.execute(
                "UPDATE plots SET file_content_hash = ?, image = ? WHERE filepath = ?",
                (rfdata.h, image_bytes, rfdata.filepath)
            )
        else:
            # Insert new record
            image_bytes = fig_to_bytes(fig)
            self.cur.execute(
                "INSERT INTO plots (filepath, file_content_hash, image) VALUES (?, ?, ?)",
                (rfdata.filepath, rfdata.h, image_bytes)
            )

        self.db.commit()

    def get_fig(self, filepath: str):
        self.cur.execute(
            "SELECT image FROM plots WHERE filepath=?",
            (filepath, )
        )
        row = self.cur.fetchone()
        return row[0] if row else None

    def close(self):
        self.db.close()