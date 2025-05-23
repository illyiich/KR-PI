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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    role = request.args.get('role')  # Получаем роль из параметров URL
    if not role or role not in ['user', 'admin']:
        flash('Не указана или неверная роль.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Проверяем логин и пароль
        if password == 'password' and username in ['admin', 'user']:
            # Проверяем соответствие имени пользователя и выбранной роли
            if (role == 'admin' and username == 'admin') or (role == 'user' and username == 'user'):
                session['role'] = role
                return redirect(url_for('dashboard'))
            else:
                flash('Выбранная роль не соответствует имени пользователя.', 'error')
        else:
            flash('Неверное имя пользователя или пароль.', 'error')

    return render_template('login.html', role=role)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'role' not in session:
        return redirect(url_for('index'))

    # Всегда загружаем свежие данные из базы
    conn = get_db_connection()
    if not conn:
        return render_template('dashboard.html', debts=[], role=session.get('role'))

    cursor = conn.cursor(dictionary=True)
    try:
        query = '''
        SELECT s.student_id, s.record_book_number, s.student_name, s.group_name, 
               d.debt_id, d.debt_type, d.discipline, d.semester,
               d.teacher_name, d.department, d.head_of_department, d.head_phone
        FROM students s
        INNER JOIN debts d ON s.student_id = d.student_id
        '''
        cursor.execute(query)
        debts = cursor.fetchall()

        # Обработка NULL значений
        for debt in debts:
            for key in debt:
                if debt[key] is None:
                    debt[key] = ''
            if not debt.get('debt_id'):
                debt['debt_id'] = 0

        # Если есть данные в сессии, фильтруем их
        if 'filtered_debts' in session and session['filtered_debts']:
            session_debts = session['filtered_debts']
            # Фильтруем только те записи, которые всё ещё существуют в базе
            valid_debt_ids = {debt['debt_id'] for debt in debts}
            debts = [debt for debt in session_debts if debt['debt_id'] in valid_debt_ids]
        else:
            debts = debts  # Используем свежие данные из базы

    except mysql.connector.Error as err:
        flash(f'Ошибка базы данных: {err}', 'error')
        debts = []
    finally:
        cursor.close()
        conn.close()

    # Параметры поиска
    student_query = request.form.get('student_query', '').strip()
    group_query = request.form.get('group_query', '').strip()
    discipline_query = request.form.get('discipline_query', '').strip()

    # Фильтрация данных
    filtered_debts = debts

    if student_query:
        filtered_debts = [
            debt for debt in filtered_debts
            if debt['record_book_number'].lower() == student_query.lower()
        ]

    if group_query:
        filtered_debts = [
            debt for debt in filtered_debts
            if debt['group_name'].lower() == group_query.lower()
        ]

    if discipline_query:
        filtered_debts = [
            debt for debt in filtered_debts
            if discipline_query.lower() in debt['discipline'].lower()
        ]

    # Сохраняем отфильтрованные данные в сессии
    session['filtered_debts'] = filtered_debts

    return render_template('dashboard.html', debts=filtered_debts, role=session['role'])

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

    # Проверка формата номера зачётной книжки
    if not re.match(r'^[ЗК]{2}-\d{3}$', form_data['record_book']):
        flash('Номер зачётной книжки должен быть в формате ЗК-123 (ЗК, дефис, три цифры)', 'error')
        return redirect(url_for('dashboard'))

    # Проверка формата телефона
    if not re.match(r'^\+7\(\d{3}\)\d{3}-\d{2}-\d{2}$', form_data['head_phone']):
        flash('Телефон должен быть в формате +7(код региона)XXX-XX-XX, например, +7(495)123-45-67', 'error')
        return redirect(url_for('dashboard'))

    # Проверка семестра
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

    cursor = conn.cursor(dictionary=True)
    
    try:
        # Проверка, существует ли студент с таким номером зачётной книжки
        cursor.execute(
            'SELECT student_id, student_name FROM students WHERE record_book_number = %s',
            (form_data['record_book'],)
        )
        existing_student = cursor.fetchone()

        if existing_student:
            # Если студент с таким номером уже существует, сравниваем имена
            existing_name = existing_student['student_name']
            if existing_name != form_data['student_name']:
                flash('Данная зачётка присвоена другому студенту.', 'error')
                return redirect(url_for('dashboard'))

        if not existing_student:
            # Добавление нового студента
            cursor.execute(
                'INSERT INTO students (record_book_number, student_name, group_name) VALUES (%s, %s, %s)',
                (form_data['record_book'], form_data['student_name'], form_data['group_name'])
            )
            student_id = cursor.lastrowid
        else:
            student_id = existing_student['student_id']

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

        # Сбрасываем фильтры в сессии после добавления
        session.pop('filtered_debts', None)
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

    cursor = conn.cursor(dictionary=True)
    
    try:
        # Получаем student_id перед удалением задолженности
        cursor.execute('SELECT student_id FROM debts WHERE debt_id = %s', (debt_id,))
        debt = cursor.fetchone()
        if not debt:
            flash('Задолженность не найдена.', 'error')
            return redirect(url_for('dashboard'))

        student_id = debt['student_id']

        # Удаляем задолженность
        cursor.execute('DELETE FROM debts WHERE debt_id = %s', (debt_id,))

        # Проверяем, остались ли у студента другие задолженности
        cursor.execute('SELECT COUNT(*) as debt_count FROM debts WHERE student_id = %s', (student_id,))
        result = cursor.fetchone()
        debt_count = result['debt_count']

        # Если задолженностей больше нет, удаляем студента
        if debt_count == 0:
            cursor.execute('DELETE FROM students WHERE student_id = %s', (student_id,))
            flash('Задолженность и студент удалены, так как у студента больше нет задолженностей.', 'success')
        else:
            flash('Задолженность успешно удалена.', 'success')

        # Сбрасываем фильтры в сессии после удаления
        session.pop('filtered_debts', None)
        conn.commit()
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
        # Удаление студента (debts удалятся автоматически благодаря ON DELETE CASCADE)
        cursor.execute('DELETE FROM students WHERE record_book_number = %s', (record_book,))
        conn.commit()
        flash('Студент и все его задолженности успешно удалены.', 'success')
        # Сбрасываем фильтры в сессии после удаления
        session.pop('filtered_debts', None)
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Ошибка при удалении студента: {err}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('dashboard'))

@app.route('/reset_filters')
def reset_filters():
    # Сбрасываем фильтры, удаляя данные из сессии
    session.pop('filtered_debts', None)
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('role', None)
    session.pop('filtered_debts', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)