import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# بنجيب أسماء الأعمدة في جدول users
c.execute("PRAGMA table_info(users)")
columns = c.fetchall()

print("📋 أعمدة جدول users:")
for col in columns:
    print(f"- {col[1]}")

conn.close()
