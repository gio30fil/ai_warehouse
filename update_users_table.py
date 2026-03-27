import sqlite3

conn = sqlite3.connect("warehouse.db")
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE users
ADD COLUMN role TEXT
""")

conn.commit()
conn.close()

print("Role column added")