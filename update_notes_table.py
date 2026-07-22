import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE notes
ADD COLUMN favorite INTEGER DEFAULT 0
""")

conn.commit()
conn.close()

print("✅ Favorite column added!")