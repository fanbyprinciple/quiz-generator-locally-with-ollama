import streamlit as st
import json
import ollama
from PyPDF2 import PdfReader

@st.cache_data
def fetch_questions(text_content, quiz_level):
    RESPONSE_JSON = {
      "mcqs" : [
        {
            "mcq": "multiple choice question1",
            "options": {
                "a": "choice here1",
                "b": "choice here2",
                "c": "choice here3",
                "d": "choice here4",
            },
            "correct": "correct choice option in the form of a, b, c or d",
        }
      ]
    }

    PROMPT_TEMPLATE = f"""
    Text: {text_content}
    You are an expert in generating MCQ type quiz on the basis of provided content. 
    Create a quiz of 2 multiple choice questions with difficulty level: {quiz_level}. 
    Ensure questions are unique and relevant to the text.
    Format your response exactly like this JSON structure:
    {json.dumps(RESPONSE_JSON, indent=2)}
    """

    response = ollama.chat(
        model='llama3.2:3b',
        messages=[{
            'role': 'user',
            'content': PROMPT_TEMPLATE
        }],
        format='json',
        options={
            'temperature': 0.3,
            'num_ctx': 1024
        }
    )

    try:
        return json.loads(response['message']['content']).get("mcqs", [])
    except json.JSONDecodeError:
        st.error("Failed to parse response from Ollama. Please try again.")
        return []

def extract_text_from_file(uploaded_file, progress_callback=None):
    if uploaded_file.name.endswith('.pdf'):
        pdf_reader = PdfReader(uploaded_file)
        total_pages = len(pdf_reader.pages)
        text = ""
        for i, page in enumerate(pdf_reader.pages):
            text += page.extract_text() or ""  # Handle pages with no text
            if progress_callback:
                progress = (i + 1) / total_pages
                progress_callback(progress)
        return text.strip()
    elif uploaded_file.name.endswith(('.txt', '.md')):
        if progress_callback:
            progress_callback(1.0)  # Instant completion for text files
        return uploaded_file.getvalue().decode("utf-8")
    else:
        st.error("Unsupported file format")
        return None

# ... (keep previous imports and functions unchanged)

# ... (keep previous imports and functions unchanged)

def main():
    st.title("Quiz generator")

    # Initialize session state variables
    if 'processed_text' not in st.session_state:
        st.session_state.processed_text = None
    if 'quiz_generated' not in st.session_state:
        st.session_state.quiz_generated = False
    if 'processing_progress' not in st.session_state:
        st.session_state.processing_progress = 0.0

    # File upload
    uploaded_file = st.file_uploader("Upload a document (PDF or TXT)", type=['pdf', 'txt', 'md'])
    
    if uploaded_file:
        # Create two columns for status and button
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("Generate Quiz"):
                st.session_state.quiz_generated = False
                st.session_state.processing_progress = 0.0
                
                with st.spinner("Processing document..."):
                    progress_bar = st.progress(0.0)
                    
                    def update_progress(progress):
                        st.session_state.processing_progress = progress
                        progress_bar.progress(progress)
                    
                    # Process document with progress updates
                    processed_text = extract_text_from_file(uploaded_file, update_progress)
                    st.session_state.processed_text = processed_text
                    
                    # Generate quiz if text processing succeeded
                    if processed_text:
                        quiz_level = st.session_state.get('quiz_level', 'easy')
                        questions = fetch_questions(processed_text, quiz_level)
                        st.session_state.questions = questions
                        st.session_state.quiz_generated = True
                        st.session_state.selected_options = [None] * len(questions)
                        st.session_state.correct_answers = []
                    
                    progress_bar.empty()

        with col1:
            # Show processing status
            if st.session_state.processing_progress > 0:
                file_type = "PDF" if uploaded_file.name.endswith('.pdf') else "Text"
                st.caption(f"Processing {file_type} document: {int(st.session_state.processing_progress * 100)}% complete")

        # Quiz level selection
        quiz_level = st.selectbox("Select quiz level:", ["Easy", "Medium", "Hard"]).lower()
        st.session_state.quiz_level = quiz_level

        # Display quiz only after generation
        if st.session_state.quiz_generated and 'questions' in st.session_state:
            questions = st.session_state.questions
            if questions:
                # Initialize answer tracking
                if not st.session_state.correct_answers:
                    st.session_state.correct_answers = [
                        q["options"][q["correct"]] for q in questions
                    ]

                # Display questions with proper index handling
                for i, question in enumerate(questions):
                    options = list(question["options"].values())
                    
                    # Get current selection index
                    current_value = st.session_state.selected_options[i]
                    try:
                        default_index = options.index(current_value) if current_value else None
                    except ValueError:
                        default_index = None
                    
                    # Display radio with proper index
                    selected_option = st.radio(
                        question["mcq"],
                        options,
                        index=default_index,
                        key=f"question_{i}"
                    )
                    st.session_state.selected_options[i] = selected_option

                # Submit button
                if st.button("Submit"):
                    marks = sum(1 for sel, cor in zip(st.session_state.selected_options, st.session_state.correct_answers) if sel == cor)
                    st.header("Quiz Result:")
                    for i, question in enumerate(questions):
                        st.subheader(f"{question['mcq']}")
                        st.write(f"You selected: {st.session_state.selected_options[i]}")
                        st.write(f"Correct answer: {st.session_state.correct_answers[i]}")
                    st.subheader(f"You scored {marks} out of {len(questions)}")
                    
                    # Reset session state
                    st.session_state.quiz_generated = False
                    st.session_state.processed_text = None
                    st.session_state.questions = None

if __name__ == "__main__":
    main()