import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# الكود ده بيضيف العمود role لو مش موجود
try:
    c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'student'")
    print("✅ تم إضافة العمود role بنجاح.")
except Exception as e:
    print("⚠️ حصل خطأ:", e)

conn.commit()
conn.close()
