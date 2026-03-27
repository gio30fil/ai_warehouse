import sqlite3

conn = sqlite3.connect("warehouse.db")
cursor = conn.cursor()

cursor.execute("SELECT username, role FROM users")

print(cursor.fetchall())

conn.close()