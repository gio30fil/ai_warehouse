import sqlite3

conn = sqlite3.connect("warehouse.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS search_logs (
id INTEGER PRIMARY KEY AUTOINCREMENT,
user TEXT,
query TEXT,
created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("Logs table created")