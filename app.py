import os

import chromadb
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from database.database import get_table_names, insert_answer, insert_question
from utils import get_or_create_chroma_collection, load_questions_and_answers

# Set page configuration
st.set_page_config(layout="wide")

load_dotenv()

# Initialize OpenAI client
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize ChromaDB persistent client
persistent_path = "Vector_Storage"
db_client = chromadb.PersistentClient(path=persistent_path)

# Define file paths
module_content_fp = "Test_Data/IRIS Autism Overview.pdf"
questions_fp = "questions_and_answers.json"


# Check if the database has already been initialized
if "db_initialized" not in st.session_state:
    # Initialize the database
    os.system("python database/init_db.py")  # Run the initialization script
    print("Database initialized")

    # Check if SQL database tables are created
    print("Tables:")
    print(get_table_names())

    # Load questions and answers into the database
    questions, answers = load_questions_and_answers(questions_fp)
    for question_id, question in questions.items():
        insert_question(question_id, question)
    for question_id, answer in answers.items():
        insert_answer(question_id, answer)

    # Mark the database as initialized
    st.session_state.db_initialized = True

# Get or create Chroma collection
collection = get_or_create_chroma_collection(db_client, module_content_fp, ai_client)

# Import and run the main function from main.py
from main import main

main(collection, questions_fp, ai_client)
