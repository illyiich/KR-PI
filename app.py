from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Конфигурация базы данных
db_config = {
    'host': 'localhost',
    'user': 'ilya',
    'password': 'password',
    'database': 'spravochnik4'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        flash(f'Ошибка подключения к базе данных: {err}', 'error')
        return None

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if password == 'password':
            session['role'] = 'admin' if username == 'admin' else 'user'
            return redirect(url_for('dashboard'))
        
        flash('Неверное имя пользователя или пароль', 'error')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'role' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        return render_template('dashboard.html', debts=[], role=session.get('role'))

    cursor = conn.cursor(dictionary=True)

    try:
        # Параметры поиска
        student_query = request.form.get('student_query', '').strip()
        group_query = request.form.get('group_query', '').strip()
        discipline_query = request.form.get('discipline_query', '').strip()

        query = '''
        SELECT s.student_id, s.record_book_number, s.student_name, s.group_name, 
               d.debt_id, d.debt_type, d.discipline, d.semester,
               d.teacher_name, d.department, d.head_of_department, d.head_phone
        FROM students s
        LEFT JOIN debts d ON s.student_id = d.student_id
        WHERE 1=1
        '''
        params = []

        if student_query:
            query += ' AND s.record_book_number = %s'
            params.append(student_query)
        if group_query:
            query += ' AND s.group_name = %s'
            params.append(group_query)
        if discipline_query:
            query += ' AND d.discipline LIKE %s'
            params.append(f'%{discipline_query}%')

        cursor.execute(query, params)
        debts = cursor.fetchall()

        # Обработка NULL значений
        for debt in debts:
            for key in debt:
                if debt[key] is None:
                    debt[key] = ''
            if not debt.get('debt_id'):
                debt['debt_id'] = 0

    except mysql.connector.Error as err:
        flash(f'Ошибка базы данных: {err}', 'error')
        debts = []
    finally:
        cursor.close()
        conn.close()

    return render_template('dashboard.html', debts=debts, role=session['role'])

@app.route('/add', methods=['POST'])
def add():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('dashboard'))

    # Получение данных из формы
    form_data = {
        'record_book': request.form.get('record_book', '').strip(),
        'student_name': request.form.get('student_name', '').strip(),
        'group_name': request.form.get('group_name', '').strip(),
        'discipline': request.form.get('discipline', '').strip(),
        'semester': request.form.get('semester', '').strip(),
        'debt_type': request.form.get('debt_type', '').strip(),
        'teacher_name': request.form.get('teacher_name', '').strip(),
        'department': request.form.get('department', '').strip(),
        'head_of_department': request.form.get('head_of_department', '').strip(),
        'head_phone': request.form.get('head_phone', '').strip()
    }

    # Проверка заполнения всех полей
    if not all(form_data.values()):
        flash('Все поля обязательны для заполнения', 'error')
        return redirect(url_for('dashboard'))

    # Проверка формата номера зачётной книжки (например, АБ-1234 или AB-1234)
    if not re.match(r'^[ЗК]{2}-\d{3}$', form_data['record_book']):
        flash('Номер зачётной книжки должен быть в формате ЗК-123 (ЗК, дефис, три цифры)', 'error')
        return redirect(url_for('dashboard'))

    # Проверка формата телефона (например, +7(495)123-45-67)
    if not re.match(r'^\+7\(\d{3}\)\d{3}-\d{2}-\d{2}$', form_data['head_phone']):
        flash('Телефон должен быть в формате +7(код региона)XXX-XX-XX, например, +7(495)123-45-67', 'error')
        return redirect(url_for('dashboard'))

    try:
        semester = int(form_data['semester'])
        if semester < 1 or semester > 10:
            flash('Семестр должен быть числом от 1 до 10', 'error')
            return redirect(url_for('dashboard'))
    except ValueError:
        flash('Семестр должен быть числом', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    if not conn:
        return redirect(url_for('dashboard'))

    cursor = conn.cursor()
    
    try:
        # Проверка, существует ли студент
        cursor.execute(
            'SELECT student_id FROM students WHERE record_book_number = %s',
            (form_data['record_book'],)
        )
        student = cursor.fetchone()

        if not student:
            # Добавление нового студента
            cursor.execute(
                'INSERT INTO students (record_book_number, student_name, group_name) VALUES (%s, %s, %s)',
                (form_data['record_book'], form_data['student_name'], form_data['group_name'])
            )
            student_id = cursor.lastrowid
        else:
            student_id = student[0]

        # Проверка на существующую идентичную задолженность
        cursor.execute(
            '''SELECT debt_id 
               FROM debts 
               WHERE student_id = %s 
               AND discipline = %s 
               AND semester = %s 
               AND debt_type = %s 
               AND teacher_name = %s 
               AND department = %s 
               AND head_of_department = %s 
               AND head_phone = %s''',
            (student_id, form_data['discipline'], semester, form_data['debt_type'],
             form_data['teacher_name'], form_data['department'],
             form_data['head_of_department'], form_data['head_phone'])
        )
        existing_debt = cursor.fetchone()

        if existing_debt:
            flash('Такая задолженность уже существует для этого студента.', 'error')
        else:
            # Добавление записи о задолженности
            cursor.execute(
                '''INSERT INTO debts 
                (student_id, discipline, semester, debt_type, teacher_name, 
                 department, head_of_department, head_phone) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                (student_id, form_data['discipline'], semester, form_data['debt_type'],
                 form_data['teacher_name'], form_data['department'],
                 form_data['head_of_department'], form_data['head_phone'])
            )
            flash('Запись успешно добавлена.', 'success')

        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Ошибка при добавлении записи: {err}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('dashboard'))

@app.route('/delete/<int:debt_id>')
def delete(debt_id):
    if 'role' not in session or session['role'] != 'admin' or debt_id == 0:
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    if not conn:
        return redirect(url_for('dashboard'))

    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM debts WHERE debt_id = %s', (debt_id,))
        conn.commit()
        flash('Задолженность успешно удалена.', 'success')
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Ошибка при удалении записи: {err}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('dashboard'))

@app.route('/delete_student', methods=['POST'])
def delete_student():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('dashboard'))

    record_book = request.form.get('record_book')
    if not record_book:
        flash('Не указан номер зачётной книжки.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    if not conn:
        return redirect(url_for('dashboard'))

    cursor = conn.cursor()
    
    try:
        # Удаление всех задолженностей студента
        cursor.execute('''
            DELETE FROM debts 
            WHERE student_id IN (
                SELECT student_id FROM students WHERE record_book_number = %s
            )
        ''', (record_book,))
        
        # Удаление студента
        cursor.execute('DELETE FROM students WHERE record_book_number = %s', (record_book,))
        
        conn.commit()
        flash('Студент и все его задолженности успешно удалены.', 'success')
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Ошибка при удалении студента: {err}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('role', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)