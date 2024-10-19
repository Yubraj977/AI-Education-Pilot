import streamlit as st

from database.database import (get_ai_feedback, get_student_answers,
                               insert_ai_feedback, insert_student,
                               insert_student_answer)
from utils import (get_feedback, get_or_create_chroma_collection,
                   get_relevant_content, load_questions_and_answers)


def main(collection, questions_fp, ai_client):
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

    st.title("SUNY Brockport Student Assessment Feedback System")

    if "student_id" not in st.session_state:
        st.session_state.student_id = None
    # Load questions and answers only if not already loaded
    if "questions" not in st.session_state:
        st.session_state.questions, st.session_state.answers = (
            load_questions_and_answers(questions_fp)
        )

    questions = st.session_state.questions
    answers = st.session_state.answers

    # Initialize session state
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = {q_id: "" for q_id in questions}
    if "feedbacks" not in st.session_state:
        st.session_state.feedbacks = {q_id: "" for q_id in questions}
    if "current_question" not in st.session_state:
        st.session_state.current_question = list(questions.keys())[0]
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "last_question" not in st.session_state:
        st.session_state.last_question = None

    # Input for Banner ID
    if st.session_state.student_id is None:  # If student_id is not yet set
        banner_id = st.text_input("Enter the last four of your Banner ID:")
        if st.button("Submit Banner ID"):
            if banner_id:  # Ensure that the banner ID is provided
                st.session_state.student_id = insert_student(
                    banner_id
                )  # Insert the student
                st.success(
                    "Student record created with ID: {}".format(
                        st.session_state.student_id
                    )
                )
            else:
                st.error("Please enter a valid Banner ID.")
        return  # Exit the function to prevent executing further code

    # Sidebar for question navigation
    with st.sidebar:
        st.title("Question Navigation")
        for q_id in questions:
            if st.button(f"Question {q_id}", key=f"nav_{q_id}"):
                st.session_state.current_question = q_id

    if not st.session_state.submitted:
        # Display current question
        current_q_id = st.session_state.current_question
        st.markdown(
            f"<p class='big-font'>Question {current_q_id}</p>", unsafe_allow_html=True
        )
        st.write(questions[current_q_id])

        # Text area for user answer
        user_answer = st.text_area(
            "Your answer:",
            value=st.session_state.user_answers[current_q_id],
            key=f"answer_{current_q_id}",
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
                    st.session_state.current_question = list(questions.keys())[
                        current_index - 1
                    ]
                    st.rerun()

        with col2:
            if st.button("Next Question"):
                current_index = list(questions.keys()).index(current_q_id)
                if current_index < len(questions) - 1:
                    st.session_state.last_question = current_q_id
                    st.session_state.current_question = list(questions.keys())[
                        current_index + 1
                    ]
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
        st.markdown(
            "<h2 style='color: #215732;'>Submission Summary</h2>",
            unsafe_allow_html=True,
        )

        for q_id, question in questions.items():
            st.markdown(
                f"<p class='big-font'>Question {q_id}</p>", unsafe_allow_html=True
            )
            st.write(question)
            st.write("Your Answer:")
            st.write(st.session_state.user_answers[q_id])

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

            # Insert student answer and AI feedback into the database
            insert_student_answer(
                st.session_state.student_id, q_id, st.session_state.user_answers[q_id]
            )
            insert_ai_feedback(
                st.session_state.student_id, st.session_state.feedbacks[q_id]
            )

            st.markdown("**AI Feedback:**")
            st.write(st.session_state.feedbacks[q_id])
            st.markdown("---")

        if st.button("Start Over"):
            for key in [
                "user_answers",
                "feedbacks",
                "current_question",
                "submitted",
                "last_question",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
