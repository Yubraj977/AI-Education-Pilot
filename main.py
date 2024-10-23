import streamlit as st
from database.database import (get_ai_feedback, get_student_answers,
                               insert_ai_feedback, insert_student_answer, 
                               get_current_attempt, get_or_create_student, 
                               update_student_attempt)
from utils import (get_feedback, get_or_create_chroma_collection,
                   get_relevant_content, load_questions_and_answers, group_question)
import time

@st.cache_resource
def initialize_resources(_questions_fp):
    questions, answers = load_questions_and_answers(_questions_fp)
    return questions, answers


def first_attempt_flow(collection, questions, answers, ai_client):
    # Filter questions for first attempt
    first_attempt_questions = {k: v for k, v in questions.items() if k not in ['6', '7']}
    grouped_questions = group_question(first_attempt_questions)
    
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = {q_id: "" for q_id in first_attempt_questions}
    if "feedbacks" not in st.session_state:
        st.session_state.feedbacks = {q_id: "" for q_id in first_attempt_questions}
    if "current_question_group" not in st.session_state:
        st.session_state.current_question_group = list(grouped_questions.keys())[0]
    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    # Sidebar for question navigation
    with st.sidebar:
        st.title("Question Navigation")
        for group_id in grouped_questions:
            if st.button(f"Question {group_id}", key=f"nav_{group_id}"):
                st.session_state.current_question_group = group_id

    if not st.session_state.submitted:
        # Display current question group
        current_group = st.session_state.current_question_group
        st.markdown(f"<p class='big-font'>Question {current_group}</p>", unsafe_allow_html=True)
        
        with st.form(key=f"form_{current_group}"):
            for q_id, question in grouped_questions[current_group]:
                st.write(question)
                user_answer = st.text_area(
                    f"Your answer for {q_id}:",
                    value=st.session_state.user_answers[q_id],
                    key=f"answer_{q_id}",
                )
                if st.form_submit_button(f"Save Answer for {q_id}"):
                    st.session_state.user_answers[q_id] = user_answer
                    insert_student_answer(st.session_state.student_id, q_id, user_answer, attempt=1)
                    st.success(f"Answer for {q_id} saved!")

        # Navigation buttons (outside the form)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Previous Question"):
                current_index = list(grouped_questions.keys()).index(current_group)
                if current_index > 0:
                    st.session_state.current_question_group = list(grouped_questions.keys())[current_index - 1]
                    st.rerun()
        with col2:
            if st.button("Next Question"):
                current_index = list(grouped_questions.keys()).index(current_group)
                if current_index < len(grouped_questions) - 1:
                    st.session_state.current_question_group = list(grouped_questions.keys())[current_index + 1]
                    st.rerun()

        # Submit all button
        if st.button("Submit All Answers"):
            st.session_state.submitted = True
            st.session_state.current_attempt = 2
            update_student_attempt(st.session_state.student_id, 2)
            st.success("All answers submitted. Generating AI feedback...")
            st.rerun()

    else:
        # Display all questions, answers, and generate feedback
        st.markdown("<h2 style='color: #215732;'>Submission Summary</h2>", unsafe_allow_html=True)

        for group_id, group_questions in grouped_questions.items():
            for q_id, question in group_questions:
                st.markdown(f"<p class='big-font'>Question {q_id}</p>", unsafe_allow_html=True)
                st.write(question)
                st.write("Your Answer:")
                st.write(st.session_state.user_answers[q_id])

                if st.session_state.user_answers[q_id].strip():

                    if not st.session_state.feedbacks[q_id]:
                        with st.spinner("Generating AI feedback..."):
                            relevant_content = get_relevant_content(
                                collection,
                                st.session_state.user_answers[q_id],
                                answers[q_id],
                                question,
                            )
                            feedback = get_feedback(
                                ai_client,
                                st.session_state.user_answers[q_id],
                                question,
                                relevant_content,
                                answers[q_id],
                            )
                            st.session_state.feedbacks[q_id] = feedback
                            insert_ai_feedback(st.session_state.student_id, feedback)

            
                    st.markdown("**AI Feedback:**")
                    st.write(st.session_state.feedbacks[q_id])

                else:
                    st.markdown("**AI Feedback:** No feedback generated for blank answer.")

                st.markdown("---")

        st.write("You have completed the first attempt. You can now close the window and return later for your second attempt, or start your second attempt now.")
        if st.button("Start Second Attempt"):
            for key in ["user_answers", "feedbacks", "current_question_group", "submitted"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

def second_attempt_flow(questions):
    # Include all questions for second attempt
    grouped_questions = group_question(questions)
    
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = {q_id: "" for q_id in questions}
    if "current_question_group" not in st.session_state:
        st.session_state.current_question_group = list(grouped_questions.keys())[0]
    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    st.write("This is your second assessment attempt, your submitted answers will be final.")

    # Sidebar for question navigation
    with st.sidebar:
        st.title("Question Navigation")
        for group_id in grouped_questions:
            if st.button(f"Question {group_id}", key=f"nav_second_{group_id}"):
                st.session_state.current_question_group = group_id

    if not st.session_state.submitted:
        current_group = st.session_state.current_question_group
        st.markdown(f"<p class='big-font'>Question {current_group}</p>", unsafe_allow_html=True)
        
        with st.form(key=f"form_second_{current_group}"):
            for q_id, question in grouped_questions[current_group]:
                st.write(question)
                user_answer = st.text_area(
                    f"Your answer for {q_id}:",
                    value=st.session_state.user_answers[q_id],
                    key=f"second_attempt_{q_id}",
                )
                if st.form_submit_button(f"Save Answer for {q_id}"):
                    st.session_state.user_answers[q_id] = user_answer
                    insert_student_answer(st.session_state.student_id, q_id, user_answer, attempt=2)
                    st.success(f"Answer for {q_id} saved!")

        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Previous Question"):
                current_index = list(grouped_questions.keys()).index(current_group)
                if current_index > 0:
                    st.session_state.current_question_group = list(grouped_questions.keys())[current_index - 1]
                    st.rerun()
        with col2:
            if st.button("Next Question"):
                current_index = list(grouped_questions.keys()).index(current_group)
                if current_index < len(grouped_questions) - 1:
                    st.session_state.current_question_group = list(grouped_questions.keys())[current_index + 1]
                    st.rerun()

        if st.button("Submit All Answers"):
            st.session_state.submitted = True
            st.session_state.current_attempt = 3
            update_student_attempt(st.session_state.student_id, 3)
            st.success("All answers for the second attempt have been submitted. You have completed the assessment.")
            st.rerun()
    else:
        st.write("You have completed both attempts of the assessment.")

def main(collection, questions_fp, ai_client):
    questions, answers = initialize_resources(questions_fp)    
    # Brockport green color scheme
    st.markdown(
        """
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
    """,
        unsafe_allow_html=True,
    )

    st.title("Autism Spectrum Disorder (Part 1): An Overview for Educators")

    if "student_id" not in st.session_state:
        st.session_state.student_id = None
    if "current_attempt" not in st.session_state:
        st.session_state.current_attempt = None

    # Input for Banner ID
    if st.session_state.student_id is None:
        banner_id = st.text_input("Enter the last four digits of your Banner ID:")
        if st.button("Submit"):
            if banner_id and banner_id.isdigit() and len(banner_id) == 4:
                student_id, current_attempt, is_new_student = get_or_create_student(banner_id)
                st.session_state.student_id = student_id
                st.session_state.current_attempt = current_attempt
                if is_new_student:
                    st.success(f"New student record created. You are starting attempt 1.")
                    st.button("Start Test")
                    return
                else:
                    st.success(f"Returning student found. You are on attempt {current_attempt}.")
                    st.button("Start Test")
                    return
            else:   
                st.error("Please enter a valid 4-digit Banner ID.")
        return
    
    # Handle different attempts
    if st.session_state.current_attempt == 1:
        st.write("Current attempt: 1")
        first_attempt_flow(collection, questions, answers, ai_client)
    elif st.session_state.current_attempt == 2:
        if "submitted" in st.session_state and st.session_state.submitted:
            # If the first attempt was just submitted, show the feedback
            st.write("First attempt feedback:")
            first_attempt_flow(collection, questions, answers, ai_client)
        else:
            # Otherwise, start the second attempt
            st.write("Current attempt: 2")
            second_attempt_flow(questions)
    else:
        st.write("You have completed both attempts of the assessment.")
        # Display a summary or final message here
        st.write("Thank you for completing the assessment. Your responses have been recorded.")