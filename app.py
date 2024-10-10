import streamlit as st
from openai import OpenAI
import chromadb
import os
from dotenv import load_dotenv
import PyPDF2
import json
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
        st.success("Using existing ChromaDB collection.")
    except chromadb.errors.InvalidCollectionException:
        st.info("No existing ChromaDB collection found. Creating a new one...")
        pdf_text = extract_text_from_pdf(module_content_fp)
        chunks, embeddings = embed_content_in_chunks(pdf_text)
        collection = db_client.create_collection(name=collection_name, embedding_function=embedding_function)
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=[f"embedding_{i}" for i in range(len(embeddings))]
        )
        st.success("New collection created and embeddings added to ChromaDB.")
    
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
    prompt = f"""
    Question: {question}
    User Answer: {user_answer}
    Actual Answer: {actual_answer}
    Relevant Content: {relevant_content}

    You are an administrator for this course and are a tutor for this assessment. You
    are to only answer based on knowledge I'm providing you. The student is asked
    "{question}" and you are to provide feedback on the student's answer. If the student's answer "{user_answer}" is not
    inline with the actual answer "{actual_answer}", you are to provide feedback on the student's answer on how they can improve and where in the relevant content
    they can review. If the student's answer is
    inline with the actual answer, you are to provide feedback on the student's answer.
    """
    response = ai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def main():
    """
    Main function to run the Student Assessment Feedback System.

    This function sets up the Streamlit interface, loads questions and answers,
    collects user responses, and generates feedback using AI.

    The function performs the following steps:
    1. Sets up the Streamlit title and initializes the ChromaDB collection.
    2. Loads questions and answers from a file.
    3. Displays questions and collects user answers using Streamlit widgets.
    4. Generates feedback for each question when the user submits their answer.
    5. Displays the feedback for each question after submission.

    Note:
    - This function relies on several helper functions like get_or_create_chroma_collection,
      load_questions_and_answers, get_relevant_content, and get_feedback.
    - It uses Streamlit for the user interface and ChromaDB for content storage and retrieval.
    """
    # Set page configuration
    st.set_page_config(
        page_title="SUNY Brockport Student Assessment",
        page_icon="🦅",  # Eagle emoji for Brockport
        layout="wide"
    )

    # Custom CSS to style the app
    st.markdown("""
    <style>
    .stApp {
        background-color: #00533E;
    }
    .stButton>button {
        background-color: #00533E;
        color: white;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-color: #00533E;
    }
    h1 {
        color: #FFA400;
    }
    h2, h3 {
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("SUNY Brockport Student Assessment Feedback System")

    with st.spinner("System is starting up, please wait..."):
        collection = get_or_create_chroma_collection() # Get or create ChromaDB collection
    
    questions, answers = load_questions_and_answers(questions_fp) # Load questions and answers from JSON file

    # Initialize session state for user answers and feedbacks if not already present
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {q_id: "" for q_id in questions}
    if 'feedbacks' not in st.session_state:
        st.session_state.feedbacks = {q_id: "" for q_id in questions}

    # Display questions, collect user answers, and show feedback
    for question_id, question in questions.items():
        st.markdown(f"<h3 style='color: white;'>{question}</h3>", unsafe_allow_html=True)
        user_answer = st.text_area(
            f"Your answer for {question_id}:",
            value=st.session_state.user_answers[question_id],
            key=f"answer_{question_id}"
        )
        
        # Create a submit button for each question
        if st.button(f"Submit Answer for {question_id}"):
            st.session_state.user_answers[question_id] = user_answer
            actual_answer = answers[question_id]
            
            # Add loading bar while generating feedback
            with st.spinner("AI generating feedback..."):
                relevant_content = get_relevant_content(collection, user_answer, actual_answer, question)
                feedback = get_feedback(user_answer, question, relevant_content, actual_answer)
            st.session_state.feedbacks[question_id] = feedback

        # Display feedback if available and submitted
        if st.session_state.feedbacks[question_id]:
            st.markdown(f"**AI Feedback:** {st.session_state.feedbacks[question_id]}")

if __name__ == "__main__":
    main()