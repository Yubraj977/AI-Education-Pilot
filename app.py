import streamlit as st
from openai import OpenAI
import chromadb
import os
from dotenv import load_dotenv
from database.database import init_db, insert_question, get_table_names, insert_answer
from utils import get_or_create_chroma_collection, load_questions_and_answers

# Set page configuration
st.set_page_config(layout="wide")

load_dotenv()

# Initialize OpenAI client
ai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Initialize ChromaDB persistent client
persistent_path = 'Vector_Storage'
db_client = chromadb.PersistentClient(path=persistent_path)

# Define file paths
module_content_fp = 'Test_Data/IRIS Autism Overview.pdf'
questions_fp = 'questions_and_answers.json'

# Initialize the database
init_db()
print("Database initialized")

#check if sqldatabase tables are created
print("Tables:")
print(get_table_names())


# load questions and answers into database
questions, answers = load_questions_and_answers(questions_fp)
for question_id, question in questions.items():
    insert_question(question_id, question)
for question_id, answer in answers.items():
    insert_answer(question_id, answer)


# Get or create Chroma collection
collection = get_or_create_chroma_collection(db_client, module_content_fp, ai_client)

# Import and run the main function from main.py
from main import main

if __name__ == "__main__":
    main(collection, questions_fp, ai_client)