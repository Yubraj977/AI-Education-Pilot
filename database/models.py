import os

from dotenv import load_dotenv
from sqlalchemy import Column, ForeignKey, Integer, String, Text, create_engine, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Database connection parameters
server = "acm-brockport-server.database.windows.net"
database = "acm-database"  # Replace with your database name
username = os.getenv("DB_USERNAME")  # Replace with your username
password = os.getenv("DB_PASSWORD")  # Replace with your password
driver = "ODBC Driver 18 for SQL Server"

# Create the SQLAlchemy engine
DATABASE_URL = (
    f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver={driver}"
)
engine = create_engine(DATABASE_URL)

# Create a base class for declarative models
Base = declarative_base()


# Define your models
class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, autoincrement=True)
    banner_id = Column(String(100), nullable=False)  # Add more fields as necessary
    current_attempt = Column(Integer, default=1)


class StudentAnswer(Base):
    __tablename__ = "student_answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    question_id = Column(
        String(50), ForeignKey("questions.question_id"), nullable=False
    )
    answer = Column(Text, nullable=False)
    attempt = Column(Integer, nullable=False, default=1)



class AIFeedback(Base):
    __tablename__ = "ai_feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    feedback = Column(Text, nullable=False)


class Question(Base):
    __tablename__ = "questions"
    question_id = Column(String(50), primary_key=True)
    question = Column(Text, nullable=False)


class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(
        String(50), ForeignKey("questions.question_id"), nullable=False
    )
    answer = Column(Text, nullable=False)


# Create tables in the database
Base.metadata.create_all(engine)

# Create a session
Session = sessionmaker(bind=engine)
