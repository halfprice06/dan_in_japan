import sqlite3

def setup_database():
    conn = sqlite3.connect('photos.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            caption TEXT,
            date_taken TEXT,
            latitude REAL,
            longitude REAL,
            location_name TEXT,
            exif_data TEXT,
            photographer TEXT
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    setup_database() 