import streamlit as st
from openai import OpenAI
import chromadb
import os
from dotenv import load_dotenv
import PyPDF2
import json
import yaml
from chromadb.utils import embedding_functions

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

def extract_text_from_pdf(pdf_path):
    """
    Extracts text content from a PDF file.

    This function opens a PDF file, reads its content, and extracts the text
    from each page, concatenating it into a single string.

    Args:
        pdf_path (str): The file path to the PDF document.

    Returns:
        str: A string containing all the extracted text from the PDF.

    Raises:
        FileNotFoundError: If the specified PDF file does not exist.
        PyPDF2.errors.PdfReadError: If there's an error reading the PDF file.
    """
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

def embed_content_in_chunks(content):
    """
    Embeds content in chunks using OpenAI's text embedding model.

    This function takes a large piece of text content, splits it into overlapping chunks,
    and then generates embeddings for each chunk using OpenAI's text-embedding-ada-002 model.

    Args:
        content (str): The text content to be embedded.

    Returns:
        tuple: A tuple containing two lists:
            - chunks (list of str): The text content split into overlapping chunks.
            - embeddings (list of list of float): The embeddings for each chunk.

    Note:
        - The function uses a chunk size of 800 characters with a 200 character overlap.
        - It requires an initialized OpenAI client (ai_client) with a valid API key.
        - The embedding model used is "text-embedding-ada-002".
    """
    chunk_size = 800
    chunk_overlap = 200
    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size - chunk_overlap)]
    
    embeddings = []
    for chunk in chunks:
        response = ai_client.embeddings.create(
            input=chunk,
            model="text-embedding-ada-002"
        )
        embeddings.append(response.data[0].embedding)
    return chunks, embeddings

@st.cache_resource
def get_or_create_chroma_collection():
    """
    Retrieves an existing ChromaDB collection or creates a new one if it doesn't exist.

    This function attempts to get a ChromaDB collection with the name "module_content".
    If the collection exists, it's returned. If not, a new collection is created,
    populated with embeddings from the PDF content, and then returned.

    The function uses Streamlit's caching mechanism to avoid unnecessary recomputation.

    Returns:
        chromadb.Collection: The retrieved or newly created ChromaDB collection.

    Raises:
        chromadb.errors.InvalidCollectionException: If there's an error accessing the collection.
        FileNotFoundError: If the PDF file specified by module_content_fp is not found.
        PyPDF2.errors.PdfReadError: If there's an error reading the PDF file.

    Note:
        - This function relies on global variables: db_client, module_content_fp
        - It uses the OpenAI API for creating embeddings, so a valid API key must be set.
        - The function displays Streamlit status messages during its execution.
    """
    collection_name = "module_content"
    
    embedding_function = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-ada-002"
    )
    
    try:
        collection = db_client.get_collection(name=collection_name, embedding_function=embedding_function)
        print("Using existing ChromaDB collection.")
    except chromadb.errors.InvalidCollectionException:
        print("No existing ChromaDB collection found. Creating a new one...")
        pdf_text = extract_text_from_pdf(module_content_fp)
        chunks, embeddings = embed_content_in_chunks(pdf_text)
        collection = db_client.create_collection(name=collection_name, embedding_function=embedding_function)
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=[f"embedding_{i}" for i in range(len(embeddings))]
        )
        print("New collection created and embeddings added to ChromaDB.")
    
    return collection

def load_questions_and_answers(json_path):
    """
    Load questions and answers from a JSON file.

    This function reads a JSON file from the specified path and extracts
    the 'questions' and 'answers' data from it.

    Args:
        json_path (str): The file path to the JSON file containing questions and answers.

    Returns:
        tuple: A tuple containing two dictionaries:
            - The first dictionary contains the questions, where keys are question IDs
              and values are the question texts.
            - The second dictionary contains the answers, where keys are question IDs
              and values are the corresponding answers.

    Raises:
        FileNotFoundError: If the specified JSON file is not found.
        json.JSONDecodeError: If the JSON file is not properly formatted.
        KeyError: If the 'questions' or 'answers' keys are not present in the JSON data.

    Example:
        questions, answers = load_questions_and_answers('path/to/qa_data.json')
    """
    with open(json_path, 'r') as file:
        data = json.load(file)
    questions = {k: f"{k}: {v}" for k, v in data['questions'].items()}
    return questions, data['answers']

def get_relevant_content(collection, user_answer, actual_answer, question):
    """
    Retrieve relevant content from a collection based on the question, user answer, and actual answer.

    This function combines the question, user answer, and actual answer into a single query,
    then uses this query to search the provided collection for relevant content.

    Args:
        collection (chromadb.Collection): The ChromaDB collection to query.
        user_answer (str): The answer provided by the user.
        actual_answer (str): The correct answer to the question.
        question (str): The question being asked.

    Returns:
        str: A string containing the relevant content found in the collection.
             If no relevant content is found, an empty string is returned.

    The function performs the following steps:
    1. Combines the question, user answer, and actual answer into a single query string.
    2. Queries the collection using this combined query, requesting the top 3 most relevant results.
    3. Joins the documents from the first result (if any) into a single string, separated by newlines.
    4. Returns the joined string if content was found, otherwise returns an empty string.
    """
    combined_query = f"{question} {user_answer} {actual_answer}"
    results = collection.query(
        query_texts=[combined_query],
        n_results=3
    )
    relevant_content = "\n\n".join(results['documents'][0])
    return relevant_content if relevant_content else ""

def load_prompts():
    with open('prompts.yaml', 'r') as file:
        return yaml.safe_load(file)


def get_feedback(user_answer, question, relevant_content, actual_answer):
    """
    Generate feedback for a student's answer using AI.

    This function creates a prompt based on the question, user's answer, actual answer,
    and relevant content, then uses an AI model to generate feedback.

    Args:
        user_answer (str): The answer provided by the student.
        question (str): The question being asked.
        relevant_content (str): Additional context or information related to the question.
        actual_answer (str): The correct answer to the question.

    Returns:
        str: The AI-generated feedback on the student's answer.

    The function performs the following steps:
    1. Constructs a prompt containing the question, user's answer, actual answer, and relevant content.
    2. Sends this prompt to an AI model (GPT-3.5-turbo) using the OpenAI API.
    3. Retrieves and returns the AI-generated feedback.

    Note:
    - The AI is instructed to act as a course administrator and tutor.
    - Feedback is tailored based on whether the student's answer aligns with the actual answer.
    - The AI uses only the provided information to generate feedback.
    """
    prompts = load_prompts()
    feedback_prompt = prompts['feedback_prompt']
    response = ai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": feedback_prompt}
        ]
    )
    return response.choices[0].message.content

def main():
    st.set_page_config(layout="wide")
    
    # Brockport green color scheme
    st.markdown("""
    <style>
    .big-font {
        font-size: 20px !important;
        font-weight: bold;
        color: #00533E;
    }
    .stButton>button {
        background-color: #00533E;
        color: white;
    }
    .stTextInput>div>div>input {
        border-color: #00533E;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("SUNY Brockport Student Assessment Feedback System")

    with st.spinner("System is starting up, please wait..."):
        collection = get_or_create_chroma_collection()
    
    questions, answers = load_questions_and_answers(questions_fp)

    # Initialize session state
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {q_id: "" for q_id in questions}
    if 'feedbacks' not in st.session_state:
        st.session_state.feedbacks = {q_id: "" for q_id in questions}
    if 'current_question' not in st.session_state:
        st.session_state.current_question = list(questions.keys())[0]
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    if 'last_question' not in st.session_state:
        st.session_state.last_question = None

    # Sidebar for question navigation
    with st.sidebar:
        st.title("Question Navigation")
        for q_id in questions:
            if st.button(f"Question {q_id}", key=f"nav_{q_id}"):
                st.session_state.current_question = q_id

    if not st.session_state.submitted:
        # Display current question
        current_q_id = st.session_state.current_question
        st.markdown(f"<p class='big-font'>Question {current_q_id}</p>", unsafe_allow_html=True)
        st.write(questions[current_q_id])

        # Text area for user answer
        user_answer = st.text_area(
            "Your answer:",
            value=st.session_state.user_answers[current_q_id],
            key=f"answer_{current_q_id}"
        )
        
        # Submit button for current question
        if st.button("Save Answer"):
            st.session_state.user_answers[current_q_id] = user_answer
            st.success("Answer saved!")

        # Next button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Previous Question"):
                current_index = list(questions.keys()).index(current_q_id)
                if current_index > 0:
                    st.session_state.last_question = current_q_id
                    st.session_state.current_question = list(questions.keys())[current_index - 1]
                    st.rerun()
        with col2:
            if st.button("Next Question"):
                current_index = list(questions.keys()).index(current_q_id)
                if current_index < len(questions) - 1:
                    st.session_state.last_question = current_q_id
                    st.session_state.current_question = list(questions.keys())[current_index + 1]
                    st.rerun()

        # Submit all button
        if st.button("Submit All Questions"):
            st.session_state.submitted = True
            st.rerun()

        # Clear the text area if moving to a new question
        if st.session_state.last_question != st.session_state.current_question:
            st.session_state.last_question = st.session_state.current_question
            st.rerun()

    else:
        # Display all questions, answers, and generate feedback
        st.markdown("<h2 style='color: #215732;'>Submission Summary</h2>", unsafe_allow_html=True)
        
        for q_id, question in questions.items():
            st.markdown(f"<p class='big-font'>Question {q_id}</p>", unsafe_allow_html=True)
            st.write(question)
            st.write("Your Answer:")
            st.write(st.session_state.user_answers[q_id])
            
            if not st.session_state.feedbacks[q_id]:
                with st.spinner("Generating AI feedback..."):
                    relevant_content = get_relevant_content(collection, st.session_state.user_answers[q_id], answers[q_id], question)
                    feedback = get_feedback(st.session_state.user_answers[q_id], question, relevant_content, answers[q_id])
                    st.session_state.feedbacks[q_id] = feedback
            
            st.markdown("**AI Feedback:**")
            st.write(st.session_state.feedbacks[q_id])
            st.markdown("---")

        if st.button("Start Over"):
            for key in ['user_answers', 'feedbacks', 'current_question', 'submitted', 'last_question']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()