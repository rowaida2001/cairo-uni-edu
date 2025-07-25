import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# جيب اسماء الأعمدة في جدول courses
cursor.execute("PRAGMA table_info(courses);")
columns = cursor.fetchall()

print("أعمدة جدول courses:")
for col in columns:
    print(col)

conn.close()
