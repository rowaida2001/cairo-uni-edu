import sqlite3

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# جلب كل المستخدمين
cursor.execute("SELECT id, fullname, email, role FROM users")
rows = cursor.fetchall()

if rows:
    for row in rows:
        print(row)
else:
    print("🚫 لا يوجد مستخدمون في قاعدة البيانات.")

conn.close()

