import sqlite3

conn = sqlite3.connect("warehouse.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT UNIQUE,
password TEXT,
role TEXT
)
""")

# admin user
cursor.execute("""
INSERT OR IGNORE INTO users (username,password,role)
VALUES ('admin','admin123','admin')
""")

# sales users
for i in range(1,11):

    username = f"sales{i}"

    cursor.execute("""
    INSERT OR IGNORE INTO users (username,password,role)
    VALUES (?,?,?)
    """,(username,"1234","sales"))

conn.commit()
conn.close()

print("Users created successfully")