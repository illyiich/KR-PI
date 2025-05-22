CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    student_name VARCHAR(255) NOT NULL,
    group_name VARCHAR(50) NOT NULL,
    record_book_number VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE debts (
    debt_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    discipline VARCHAR(255) NOT NULL,
    semester INT NOT NULL,
    debt_type VARCHAR(100) NOT NULL,
    teacher_name VARCHAR(255) NOT NULL,
    department VARCHAR(255) NOT NULL,
    head_of_department VARCHAR(255) NOT NULL,
    head_phone VARCHAR(20) NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user') NOT NULL
);

-- Добавляем студентов
INSERT INTO students (student_name, group_name, record_book_number) VALUES
('Иванов Иван Иванович', 'ИС-21', 'ЗК-001'),
('Петров Петр Петрович', 'ИС-21', 'ЗК-002'),
('Сидорова Анна Сергеевна', 'ЭК-22', 'ЗК-003'),
('Юмаев Егор Михайлович', '22-ИЭ-1', 'ЗК-009'),
('Сафаров Артём Игоревич', '22-ИЭ-1', 'ЗК-010'),
('Бундин Дмитрий Евгеньевич', '22-ИЭ-1', 'ЗК-011'),
('Тихонов Илья Алексеевич', '22-ИЭ-2', 'ЗК-012'),
('Кузанюк Тимофей Юрьевич', '22-ИЭ-2', 'ЗК-013');

-- Добавляем задолженности
INSERT INTO debts (student_id, discipline, semester, debt_type, teacher_name, department, head_of_department, head_phone) VALUES
(1, 'Математика', 3, 'Экзамен', 'Кутузова Татьяна Адамовна', 'Кафедра математики', 'Кузнецов Алексей Петрович', '+7(999)123-45-67'),
(2, 'Программирование', 4, 'Зачет', 'Ковалев Сергей Иванович', 'Кафедра информатики', 'Соловей Марина Викторовна', '+7(999)123-45-68'),
(3, 'Бухгалтерский учёт', 2, 'Экзамен', 'Даниленков Валерий Леонидович', 'Кафедра экономики', 'Мнацаканян Альберт Гургенович', '+7(999)123-45-69'),
(4, 'Электроника', 2, 'Зачёт', 'Капустин Владимир Вячеславович', 'Кафедра информатики', 'Соловей Марина Викторовна', '+7(950)-674-53-29'),
(5, 'Дискретная математика', 3, 'Курсовая работа', 'Топоркова Ольга Мстиславовна', 'Кафедра информатики', 'Соловей Марина Викторовна', '+7(981)777-55-44'),
(6, 'Математика', 2, 'Экзамен', 'Кутузова Татьяна Адамовна', 'Кафедра математики', 'Кузнецов Алексей Петрович', '+7(990)258-77-65'),
(7, 'Эконометрика', 2, 'Зачёт', 'Настин Юрий Яковлевич', 'Кафедра экономики', 'Мнацаканян Альберт Гургенович', '+7(911)479-28-66'),
(8, 'Эконометрика', 2, 'Зачёт', 'Настин Юрий Яковлевич', 'Кафедра экономики', 'Мнацаканян Альберт Гургенович', '+7(952)344-57-80');

-- Добавляем пользователей (пароль "password" для всех)
INSERT INTO users (username, password, role) VALUES
('admin', 'password', 'admin'),
('user', 'password', 'user');

CREATE TABLE IF NOT EXISTS debts (
    debt_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    -- остальные поля
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);


-- Удаляем старые данные, если они есть (для чистоты)
DELETE FROM debts;

DELETE FROM students;

-- Проверка содержимого таблиц
SELECT * FROM debts;

SELECT * FROM students;

