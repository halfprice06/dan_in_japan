import sqlite3

def setup_database():
    conn = sqlite3.connect('photos.db')
    cursor = conn.cursor()
    
    # Create photo table
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
    
    # Create point_of_interest table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS point_of_interest (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (photo_id) REFERENCES photo (id)
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    setup_database() 