import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

try:
    cursor.execute("""
        ALTER TABLE notes
        ADD COLUMN lecture_name TEXT
    """)

    print("✅ lecture_name column added successfully!")

except sqlite3.OperationalError:
    print("✅ lecture_name column already exists.")

conn.commit()
conn.close()