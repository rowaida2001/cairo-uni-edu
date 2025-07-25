import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(results)")
columns = cursor.fetchall()

print("أعمدة جدول results:")
for column in columns:
    print(column)

conn.close()
