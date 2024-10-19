from sqlalchemy import text

from database.models import (AIFeedback, Answer, Question, Session, Student,
                             StudentAnswer)


def insert_question(question_id, question):
    # Check if the question already exists
    session = Session()
    existing_question = (
        session.query(Question).filter_by(question_id=question_id).first()
    )
    if existing_question is None:
        new_question = Question(question_id=question_id, question=question)
        session.add(new_question)
        session.commit()
    else:
        print(f"Question with ID {question_id} already exists. Skipping insertion.")


def insert_answer(question_id, answer):
    session = Session()
    existing_answer = (
        session.query(Answer).filter_by(question_id=question_id, answer=answer).first()
    )
    if existing_answer is None:
        new_answer = Answer(question_id=question_id, answer=answer)
        session.add(new_answer)
        session.commit()
        print(f"Inserted answer: for question ID: {question_id}")
    else:
        print(
            f"Answer for question ID {question_id} already exists. Skipping insertion."
        )


def insert_student(banner_id):
    session = Session()
    new_student = Student(banner_id=banner_id)
    session.add(new_student)
    session.commit()
    student_id = new_student.id  # Get the generated student ID
    session.close()  # Close the session
    return student_id


def insert_student_answer(student_id, question_id, answer):
    session = Session()
    try:
        new_student_answer = StudentAnswer(
            student_id=student_id, question_id=question_id, answer=answer
        )
        session.add(new_student_answer)
        session.commit()
    except Exception as e:
        print(f"Error inserting student answer: {e}")
    finally:
        session.close()


def get_student_answers(student_id):
    session = Session()
    answers = session.query(StudentAnswer).filter_by(student_id=student_id).all()
    session.close()
    return answers


def insert_ai_feedback(student_id, feedback):
    session = Session()
    try:
        new_feedback = AIFeedback(student_id=student_id, feedback=feedback)
        session.add(new_feedback)
        session.commit()
    except Exception as e:
        print(f"Error inserting AI feedback: {e}")
    finally:
        session.close()


def get_ai_feedback(student_id):
    session = Session()
    feedback = session.query(AIFeedback).filter_by(student_id=student_id).all()
    session.close()
    return feedback


def get_table_names():
    session = Session()
    # Use text() for the main query
    tables = session.execute(
        text(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE';"
        )
    ).fetchall()

    table_columns = {}
    for table in tables:
        table_name = table[0]
        # Use text() for the column names query
        columns = session.execute(
            text(
                f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'"
            )
        ).fetchall()
        column_names = [column[0] for column in columns]
        table_columns[table_name] = column_names

    session.close()
    return table_columns
