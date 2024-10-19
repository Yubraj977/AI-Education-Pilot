import sqlite3



def init_db():
    conn = sqlite3.connect('pilot.db')
    cursor = conn.cursor()
    
    # Create student_answers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer TEXT NOT NULL,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    ''')
    
    # Create ai_feedback table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            feedback TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')

    # Drop existing questions table if it exists
    cursor.execute('DROP TABLE IF EXISTS questions')

    # Create questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT NOT NULL,
            question TEXT NOT NULL
        )
    ''')

    cursor.execute('DROP TABLE IF EXISTS answers')

    # Create answers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT NOT NULL,
            answer TEXT NOT NULL,
            FOREIGN KEY (question_id) REFERENCES questions(question_id) 
        )
    ''')
    conn.commit()
    conn.close()

def insert_question(question_id, question):
    conn = sqlite3.connect('pilot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO questions (question_id, question)
        VALUES (?, ?)
    ''', (question_id, question))
    conn.commit()
    conn.close()

def insert_answer(question_id, answer):
    conn = sqlite3.connect('pilot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO answers (question_id, answer)
        VALUES (?, ?)
    ''', (question_id, answer))
    conn.commit()
    conn.close()

def insert_student_answer(student_id, question_id, answer):
    conn = sqlite3.connect('pilot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO student_answers (student_id, question_id, answer)
        VALUES (?, ?, ?)
    ''', (student_id, question_id, answer))
    conn.commit()
    conn.close()

def get_student_answers(student_id):
    conn = sqlite3.connect('pilot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM student_answers WHERE student_id = ?', (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def insert_ai_feedback(student_id, feedback):
    conn = sqlite3.connect('pilot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ai_feedback (student_id, feedback)
        VALUES (?, ?)
    ''', (student_id, feedback))
    conn.commit()
    conn.close()

def get_ai_feedback(student_id):
    conn = sqlite3.connect('pilot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ai_feedback WHERE student_id = ?', (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_table_names():
    conn = sqlite3.connect('pilot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    table_columns = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        table_columns[table_name] = column_names
    
    conn.close()
    return table_columns