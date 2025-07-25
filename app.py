from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

# مجلدات رفع الصور والامتحانات
USER_PHOTO_FOLDER = "static/user_photos"
EXAM_UPLOAD_FOLDER = "uploads"
os.makedirs(USER_PHOTO_FOLDER, exist_ok=True)
os.makedirs(EXAM_UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT,
            course_code TEXT,
            doctor_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_name TEXT,
            course_id INTEGER,
            duration_minutes INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER,
            question_text TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_answer TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            exam_id INTEGER,
            question_id INTEGER,
            answer TEXT,
            is_correct BOOLEAN
        )
    """)

    # ✅ إضافة عمود user_id لجدول student_answers لو مش موجود
    try:
        cursor.execute("ALTER TABLE student_answers ADD COLUMN user_id INTEGER")
    except sqlite3.OperationalError:
        pass  # العمود موجود بالفعل

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            exam_id INTEGER,
            score INTEGER
        )
    """)

    conn.commit()
    conn.close()

# ============ دوال مساعدة ===============
def get_user_by_email(email):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    return user

# ============ الراوتات ===============
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, fullname, password, role FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['fullname'] = user[1]
            session['role'] = user[3]
            session['email'] = email  # ✅ لازم يكون هنا علشان نحتفظ بالإيميل في السيشن

            if user[3] == 'teacher':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            error = "البريد الإلكتروني أو كلمة المرور غير صحيحة"
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, name, description FROM courses WHERE user_id = ?", (user_id,))
    courses = c.fetchall()
    conn.close()
    return render_template('dashboard.html', courses=courses)

@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if 'email' not in session:
        return redirect(url_for('login'))

    user = get_user_by_email(session['email'])
    if not user:
        return redirect(url_for('logout'))

    user_id = user[0]

    if request.method == 'POST':
        name = request.form['course_name']
        description = request.form['course_description']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO courses (user_id, name, description) VALUES (?, ?, ?)", (user_id, name, description))
        conn.commit()
        conn.close()

        flash("✅ تم إنشاء الكورس بنجاح", "success")
        return redirect(url_for('dashboard'))

    return render_template('create_course.html')

@app.route('/submit_exam/<int:exam_id>', methods=['POST'])
def submit_exam(exam_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    student_id = session['user_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    total_score = 0
    user_answers = {}

    # Get exam questions
    c.execute("SELECT id, correct_answer FROM questions WHERE exam_id = ?", (exam_id,))
    questions = c.fetchall()

    for q_id, correct_answer in questions:
        student_answer = request.form.get(f'question_{q_id}', '')
        user_answers[q_id] = student_answer
        if student_answer.strip().lower() == correct_answer.strip().lower():
            total_score += 1

        # Save individual student answer
        c.execute("INSERT INTO student_answers (student_id, exam_id, question_id, student_answer) VALUES (?, ?, ?, ?)",
                  (student_id, exam_id, q_id, student_answer))

    # 🟢 دلوقتي نستخدم المتغيرات بشكل سليم:
    score = total_score
    c.execute("INSERT INTO results (student_id, exam_id, score) VALUES (?, ?, ?)", 
          (student_id, exam_id, score))
    conn.commit()
    conn.close()

    return render_template("exam_result.html", score=score, total=len(questions))

@app.route('/create_exam', methods=['GET', 'POST'])
def create_exam():
    if 'email' not in session:
        return redirect(url_for('login'))

    user = get_user_by_email(session['email'])
    if not user:
        return redirect(url_for('logout'))

    user_id = user[0]

    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id, name FROM courses WHERE user_id = ?", (user_id,))
        courses = c.fetchall()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        title = request.form.get('title')
        duration = int(request.form.get('duration'))

        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            c.execute("INSERT INTO exams (course_id, title, duration) VALUES (?, ?, ?)", (course_id, title, duration))
            exam_id = c.lastrowid

            for i in range(5):
                question = f"MCQ Question {i+1}?"
                c.execute('''INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option, question_type)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                          (exam_id, question, 'A', 'B', 'C', 'D', 'A', 'mcq'))

            c.execute('''INSERT INTO questions (exam_id, question_text, question_type)
                         VALUES (?, ?, ?)''', (exam_id, 'Essay Question: Explain...', 'essay'))

            for i in range(5):
                question = f"True or False Question {i+1}?"
                c.execute('''INSERT INTO questions (exam_id, question_text, option_a, option_b, correct_option, question_type)
                             VALUES (?, ?, ?, ?, ?, ?)''',
                          (exam_id, question, 'True', 'False', 'True', 'true_false'))

            conn.commit()

        flash("✅ تم إنشاء الامتحان بنجاح", "success")
        return redirect(url_for('create_exam'))

    return render_template('create_exam.html', courses=courses)

@app.route('/upload_exam_file', methods=['POST'])
def upload_exam_file():
    file = request.files['exam_file']
    if file:
        filename = secure_filename(file.filename)
        upload_path = os.path.join(EXAM_UPLOAD_FOLDER, filename)
        file.save(upload_path)
        flash("✅ تم رفع الامتحان بنجاح", "success")
    else:
        flash("⚠️ يرجى اختيار ملف صالح", "danger")
    return redirect(url_for('create_exam'))

@app.route('/manual_exam', methods=['POST'])
def manual_exam():
    q1 = request.form.get('q1')
    q2 = request.form.get('q2')
    flash("✅ تم إنشاء الامتحان اليدوي بنجاح", "success")
    return redirect(url_for('create_exam'))

# Route: Teacher Dashboard
@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    return render_template('teacher_dashboard.html', fullname=session.get('fullname'))

# Route: Student Dashboard
@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Get all courses
    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    # Get available exams
    cursor.execute("SELECT * FROM exams")
    exams = cursor.fetchall()

    # Get student results with exam titles
    cursor.execute('''
        SELECT exams.title, results.score
        FROM results
        JOIN exams ON results.exam_id = exams.id
        WHERE results.user_id = ?
    ''', (session['user_id'],))
    results = cursor.fetchall()

    conn.close()

    return render_template('student_dashboard.html',
                           fullname=session['fullname'],
                           courses=courses,
                           exams=exams,
                           results=results)

@app.route('/results')
def my_results():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    query = '''
        SELECT exams.title, exam_results.score
        FROM exam_results
        JOIN exams ON exam_results.exam_id = exams.id
        WHERE exam_results.user_id = ?
    '''
    cursor.execute(query, (user_id,))
    results = cursor.fetchall()
    conn.close()

    return render_template('results.html', results=results)

@app.route('/take_exam/<int:exam_id>', methods=['GET', 'POST'])
def take_exam(exam_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # احضار بيانات الامتحان
    c.execute('SELECT title, duration FROM exams WHERE id = ?', (exam_id,))
    exam = c.fetchone()
    if not exam:
        return "Exam not found."

    exam_title, exam_duration = exam

    # احضار الأسئلة
    c.execute('SELECT * FROM questions WHERE exam_id = ?', (exam_id,))
    questions = c.fetchall()
    conn.close()

    if request.method == 'POST':
        score = 0
        total = 0
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        for q in questions:
            q_id, _, q_text, opt1, opt2, opt3, opt4, correct, q_type = q
            user_answer = request.form.get(f"question_{q_id}")

            if q_type == 'essay':
                c.execute('''INSERT INTO student_answers (user_id, exam_id, question_id, answer) 
                             VALUES (?, ?, ?, ?)''', 
                          (session['user_id'], exam_id, q_id, user_answer))
            else:
                if user_answer and user_answer.lower() == correct.lower():
                    score += 1
                total += 1

        # حفظ النتيجة
        c.execute('INSERT INTO results (user_id, exam_id, score, total) VALUES (?, ?, ?, ?)', 
                  (session['user_id'], exam_id, score, total))
        conn.commit()
        conn.close()
        return redirect(url_for('student_results'))

    return render_template('take_exam.html', exam_title=exam_title, exam_duration=exam_duration, questions=questions)

@app.route('/my_exams')
def my_exams():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT exams.id, exams.title
        FROM exams
        JOIN courses ON exams.course_id = courses.id
        WHERE courses.user_id = ?
    """, (user_id,))
    exams = cursor.fetchall()
    conn.close()
    return render_template('my_exams.html', exams=exams)

@app.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    user = get_user_by_email(session['email'])
    if not user:
        return redirect(url_for('logout'))

    user_id = user[0]

    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        # نتأكد إن الكورس يخص المستخدم الحالي
        c.execute("DELETE FROM courses WHERE id = ? AND user_id = ?", (course_id, user_id))
        conn.commit()

    flash("✅ تم حذف الكورس بنجاح", "success")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (?, ?, ?, ?)",
                       (fullname, email, hashed_password, role))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')



if __name__ == "__main__":
    init_db()
    app.run(debug=True)
