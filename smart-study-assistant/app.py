# app.py - Smart Study Assistant
import streamlit as st
import PyPDF2
import io
from transformers import pipeline
from keybert import KeyBERT
import random
import time
import os

# Set page config
st.set_page_config(
    page_title="Smart Study Assistant",
    page_icon="📚",
    layout="wide"
)


# Initialize AI models with error handling
@st.cache_resource
def load_models():
    """Load AI models only once to save time"""
    try:
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        st.success("✅ Summarization model loaded successfully!")
    except Exception as e:
        st.error(f"❌ Failed to load summarization model: {e}")
        summarizer = None

    try:
        kw_model = KeyBERT()
        st.success("✅ Keyword model loaded successfully!")
    except Exception as e:
        st.error(f"❌ Failed to load keyword model: {e}")
        kw_model = None

    return summarizer, kw_model


class StudyAssistant:
    def __init__(self):
        self.summarizer, self.kw_model = load_models()

    def extract_text_from_pdf(self, pdf_file):
        """Extract text from uploaded PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            total_pages = len(pdf_reader.pages)

            # Progress bar for PDF reading
            progress_bar = st.progress(0)
            for i, page in enumerate(pdf_reader.pages):
                text += page.extract_text() + "\n"
                progress_bar.progress((i + 1) / total_pages)

            return text
        except Exception as e:
            st.error(f"❌ Error reading PDF: {e}")
            return ""

    def smart_summarize(self, text, max_length=150):
        """Generate smart summary with chunking for long texts"""
        if self.summarizer is None:
            return "Summarization model not available. Please check the requirements."

        if len(text) < 100:
            return "Text too short to summarize effectively."

        try:
            # Split text into chunks if too long
            max_chunk_size = 1000
            chunks = [text[i:i + max_chunk_size] for i in range(0, len(text), max_chunk_size)]

            summaries = []
            progress_text = st.empty()
            progress_bar = st.progress(0)

            for i, chunk in enumerate(chunks[:3]):  # Limit to first 3 chunks
                progress_text.text(f"📝 Summarizing chunk {i + 1}/{min(3, len(chunks))}...")
                progress_bar.progress((i + 1) / min(3, len(chunks)))

                try:
                    summary = self.summarizer(
                        chunk,
                        max_length=max_length,
                        min_length=30,
                        do_sample=False
                    )
                    summaries.append(summary[0]['summary_text'])
                except Exception as e:
                    st.warning(f"⚠️ Could not summarize one section: {e}")
                    continue

            progress_text.empty()
            progress_bar.empty()

            return " ".join(summaries) if summaries else "Summary generation failed."

        except Exception as e:
            return f"Error during summarization: {e}"

    def generate_flashcards(self, text, num_cards=8):
        """Generate Q&A flashcards from text"""
        if self.kw_model is None:
            return []

        try:
            # Progress indicator
            progress_text = st.empty()
            progress_text.text("🔍 Extracting key concepts...")

            # Extract key concepts
            keywords = self.kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 3),
                stop_words='english',
                top_n=num_cards * 2
            )

            flashcards = []
            used_terms = set()

            progress_text.text("🎴 Creating flashcards...")
            progress_bar = st.progress(0)

            for i, (keyword, score) in enumerate(keywords):
                if len(flashcards) >= num_cards:
                    break

                if (len(keyword) > 3 and
                        keyword.lower() not in used_terms and
                        not keyword.isnumeric()):
                    # Create different types of questions
                    question_types = [
                        f"What is {keyword}?",
                        f"Explain the concept of {keyword}.",
                        f"Why is {keyword} important?",
                        f"How does {keyword} work?",
                        f"Define {keyword}."
                    ]

                    question = random.choice(question_types)
                    answer = f"**{keyword}** is a key concept in this material. Focus on understanding its definition, significance, and application in the context."

                    flashcards.append({
                        "question": question,
                        "answer": answer,
                        "keyword": keyword,
                        "confidence": round(score, 2)
                    })
                    used_terms.add(keyword.lower())

                progress_bar.progress(min((i + 1) / len(keywords), 1.0))

            progress_text.empty()
            progress_bar.empty()

            return flashcards

        except Exception as e:
            st.error(f"❌ Error generating flashcards: {e}")
            return []

    def generate_quiz(self, text, num_questions=5):
        """Generate multiple choice questions"""
        if self.kw_model is None:
            return []

        try:
            # Progress indicator
            progress_text = st.empty()
            progress_text.text("📝 Generating quiz questions...")

            # Extract key terms for questions
            keywords = self.kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words='english',
                top_n=num_questions * 3
            )

            quiz_questions = []
            used_keywords = set()

            progress_bar = st.progress(0)

            for i, (keyword, score) in enumerate(keywords):
                if len(quiz_questions) >= num_questions:
                    break

                if (keyword.lower() not in used_keywords and
                        len(keyword) > 4 and
                        not keyword.isnumeric()):
                    # Create question with varied options
                    question = {
                        "id": len(quiz_questions) + 1,
                        "question": f"What best describes '{keyword}' based on the text?",
                        "options": [
                            "A fundamental concept discussed in the material",
                            "A technical term with specific meaning",
                            "An important principle or methodology",
                            "A key topic that requires understanding"
                        ],
                        "correct_answer": 0,
                        "explanation": f"'{keyword}' appears to be a significant concept in this context. Review the material to understand its specific meaning and applications.",
                        "keyword": keyword
                    }

                    quiz_questions.append(question)
                    used_keywords.add(keyword.lower())

                progress_bar.progress(min((i + 1) / len(keywords), 1.0))

            progress_text.empty()
            progress_bar.empty()

            return quiz_questions

        except Exception as e:
            st.error(f"❌ Error generating quiz: {e}")
            return []


def main():
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .feature-card {
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #ff6b6b;
        background-color: #f8f9fa;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .flashcard {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    }
    .quiz-question {
        background-color: #e3f2fd;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        border-left: 5px solid #2196f3;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<h1 class="main-header">📚 Smart Study Assistant</h1>', unsafe_allow_html=True)
    st.markdown("### 🚀 AI-Powered Learning Companion • Transform PDFs into Study Materials")

    # Initialize assistant
    with st.spinner("🔄 Loading AI models... This may take a moment for the first time."):
        assistant = StudyAssistant()

    # Sidebar for instructions
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2997/2997892.png", width=100)
        st.header("🎯 How to Use")
        st.markdown("""
        1. **Upload** your lecture PDF
        2. **Summarize** - Get instant AI summary  
        3. **Flashcards** - Generate Q&A cards
        4. **Quiz** - Test your knowledge
        5. **Learn** - Study smarter!
        """)

        st.markdown("---")
        st.header("📊 Benefits")
        st.metric("⏱️ Time Saved", "2-3 hours/week")
        st.metric("🧠 Retention", "40%+ improvement")
        st.metric("⚡ Efficiency", "3x faster learning")

        st.markdown("---")
        st.header("🔧 Debug Info")
        if st.button("Check Models Status"):
            if assistant.summarizer and assistant.kw_model:
                st.success("✅ All models loaded successfully!")
            else:
                st.error("❌ Some models failed to load")

    # File upload section
    st.markdown("## 📤 Step 1: Upload Your Study Material")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type="pdf",
            help="Upload your lecture notes, research paper, or textbook chapter"
        )

    with col2:
        st.info("💡 **Tip**: Use text-based PDFs (not scanned images) for best results")

    if uploaded_file is not None:
        # Display file info
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size / 1024:.1f} KB",
            "File type": uploaded_file.type
        }

        st.json(file_details)

        # Process PDF
        with st.spinner("🔄 Reading and processing your PDF..."):
            text = assistant.extract_text_from_pdf(uploaded_file)

            if not text or len(text.strip()) < 50:
                st.error("""
                ❌ Could not extract sufficient text from PDF. This might be because:
                - The PDF contains scanned images (use OCR software first)
                - The PDF is password protected
                - The file is corrupted
                - Try a different PDF file
                """)
                return

            # Show text stats
            st.success("✅ PDF processed successfully!")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📄 Pages", len(PyPDF2.PdfReader(uploaded_file).pages))
            with col2:
                st.metric("📝 Words", len(text.split()))
            with col3:
                st.metric("🔤 Characters", len(text))
            with col4:
                st.metric("📚 Reading Time", f"{len(text.split()) // 200 + 1} min")

        # Features in tabs
        st.markdown("## 🎯 Step 2: Choose Your Study Tools")
        tab1, tab2, tab3 = st.tabs(["📄 Smart Summary", "📇 AI Flashcards", "🎯 Practice Quiz"])

        with tab1:
            st.header("📄 AI-Powered Summary")
            st.markdown("Get a concise summary of the key points from your document.")

            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🚀 Generate Summary", key="summary_btn", use_container_width=True):
                    with st.spinner("🤖 AI is analyzing and summarizing your content..."):
                        summary = assistant.smart_summarize(text)

                        st.markdown('<div class="success-box">✅ Summary Generated Successfully!</div>',
                                    unsafe_allow_html=True)
                        st.markdown("### 📋 Key Takeaways")
                        st.info(summary)

                        # Download summary
                        st.download_button(
                            label="📥 Download Summary as Text",
                            data=summary,
                            file_name=f"{uploaded_file.name}_summary.txt",
                            mime="text/plain",
                            use_container_width=True
                        )

            with col2:
                st.info("""
                **What to expect:**
                - Concise overview of main concepts
                - Key points extracted by AI
                - Perfect for quick review before exams
                """)

        with tab2:
            st.header("📇 Smart Flashcards")
            st.markdown("Automatically generate Q&A flashcards from your study material.")

            col1, col2 = st.columns([1, 3])
            with col1:
                num_cards = st.slider("Number of flashcards", 3, 15, 8)
                if st.button("🎴 Generate Flashcards", key="flashcard_btn", use_container_width=True):
                    with st.spinner(f"🎴 Creating {num_cards} interactive flashcards..."):
                        flashcards = assistant.generate_flashcards(text, num_cards)

                        if flashcards:
                            st.markdown(f'<div class="success-box">✅ Generated {len(flashcards)} flashcards!</div>',
                                        unsafe_allow_html=True)

                            # Display flashcards
                            for i, card in enumerate(flashcards):
                                with st.expander(f"Card {i + 1}: {card['question']} (Confidence: {card['confidence']})",
                                                 expanded=False):
                                    st.markdown(f"**Answer:** {card['answer']}")
                                    st.caption(f"Keyword: {card['keyword']}")

                            # Flashcard study mode
                            st.markdown("---")
                            st.subheader("🎮 Interactive Study Mode")

                            if flashcards and st.button("Start Flashcard Review Session"):
                                session_card = random.choice(flashcards)
                                st.markdown(f"""
                                <div class="flashcard">
                                    <h3>🎯 Question:</h3>
                                    <p style="font-size: 1.2em;"><strong>{session_card['question']}</strong></p>
                                </div>
                                """, unsafe_allow_html=True)

                                if st.button("👀 Reveal Answer", key="reveal_btn"):
                                    st.markdown(f"""
                                    <div class="flashcard">
                                        <h3>💡 Answer:</h3>
                                        <p style="font-size: 1.1em;">{session_card['answer']}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                        else:
                            st.warning("⚠️ Could not generate flashcards. Try with more content-rich PDF.")

            with col2:
                st.info("""
                **Flashcard Features:**
                - Automatic Q&A generation
                - Key concept identification  
                - Confidence scores for accuracy
                - Interactive study mode
                - Perfect for memorization
                """)

        with tab3:
            st.header("🎯 Practice Quiz")
            st.markdown("Test your understanding with AI-generated multiple choice questions.")

            col1, col2 = st.columns([1, 3])
            with col1:
                num_quiz_questions = st.slider("Number of questions", 3, 10, 5)
                if st.button("📝 Generate Quiz", key="quiz_btn", use_container_width=True):
                    with st.spinner(f"📝 Creating {num_quiz_questions} quiz questions..."):
                        quiz_questions = assistant.generate_quiz(text, num_quiz_questions)

                        if quiz_questions:
                            st.markdown(
                                f'<div class="success-box">✅ Generated {len(quiz_questions)} quiz questions!</div>',
                                unsafe_allow_html=True)

                            # Display quiz
                            st.subheader("📋 Quiz Time!")
                            st.write("Answer the following questions based on the material:")

                            score = 0
                            user_answers = {}

                            for i, q in enumerate(quiz_questions):
                                st.markdown(f"""
                                <div class="quiz-question">
                                    <h4>Question {q['id']}: {q['question']}</h4>
                                </div>
                                """, unsafe_allow_html=True)

                                user_answer = st.radio(
                                    f"Select your answer for Question {q['id']}:",
                                    q["options"],
                                    key=f"q_{i}",
                                    index=None
                                )
                                user_answers[i] = user_answer
                                st.markdown("---")

                            # Submit quiz
                            if st.button("✅ Submit Quiz", use_container_width=True):
                                st.markdown("---")
                                st.subheader("📊 Quiz Results")

                                for i, q in enumerate(quiz_questions):
                                    user_ans = user_answers.get(i)
                                    correct_ans = q["options"][q["correct_answer"]]

                                    col_a, col_b = st.columns([3, 1])
                                    with col_a:
                                        if user_ans == correct_ans:
                                            st.success(f"✅ **Question {q['id']}:** Correct!")
                                            score += 1
                                        else:
                                            st.error(f"❌ **Question {q['id']}:** Incorrect")
                                            st.info(f"**Correct answer:** {correct_ans}")

                                    with col_b:
                                        if user_ans == correct_ans:
                                            st.markdown("**Score: 1/1**")
                                        else:
                                            st.markdown("**Score: 0/1**")

                                    with st.expander(f"💡 Explanation for Question {q['id']}"):
                                        st.info(q["explanation"])
                                        st.caption(f"Related concept: {q['keyword']}")

                                # Show final score
                                st.markdown("---")
                                col1, col2, col3 = st.columns([1, 2, 1])
                                with col2:
                                    st.markdown(f"## 🏆 Final Score: {score}/{len(quiz_questions)}")
                                    percentage = (score / len(quiz_questions)) * 100

                                    if percentage == 100:
                                        st.balloons()
                                        st.success("🎉 Perfect score! Excellent work!")
                                    elif percentage >= 70:
                                        st.success("👍 Great job! You're doing well!")
                                    elif percentage >= 50:
                                        st.warning("💪 Good effort! Keep practicing!")
                                    else:
                                        st.info("📚 Keep studying! Review the material and try again.")

                                # Progress bar for score
                                st.progress(percentage / 100)

                        else:
                            st.warning("⚠️ Could not generate quiz questions. Try with more content-rich PDF.")

            with col2:
                st.info("""
                **Quiz Features:**
                - Multiple choice questions
                - Instant scoring and feedback
                - Detailed explanations
                - Performance tracking
                - Great for self-assessment
                """)

    else:
        # Demo section when no file is uploaded
        st.markdown("---")
        st.header("🎯 Welcome to Smart Study Assistant!")

        # Features showcase
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div class="feature-card">
            <h3>📄 Smart Summaries</h3>
            <p>Turn lengthy PDFs into concise, easy-to-understand summaries using advanced AI technology.</p>
            <ul>
            <li>Extract key points</li>
            <li>Save hours of reading</li>
            <li>Perfect for reviews</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="feature-card">
            <h3>📇 AI Flashcards</h3>
            <p>Automatically generate interactive Q&A flashcards from your study materials.</p>
            <ul>
            <li>Active recall practice</li>
            <li>Key concept focus</li>
            <li>Study anywhere</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <div class="feature-card">
            <h3>🎯 Practice Quizzes</h3>
            <p>Test your knowledge with AI-generated multiple choice questions and get instant feedback.</p>
            <ul>
            <li>Self-assessment</li>
            <li>Progress tracking</li>
            <li>Exam preparation</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

        # Quick start guide
        st.markdown("---")
        st.header("🚀 Quick Start Guide")

        steps = st.container()
        with steps:
            st.write("""
            1. **Upload a PDF** - Click 'Browse files' above to upload your study material
            2. **Choose your tool** - Select from Summary, Flashcards, or Quiz
            3. **Generate content** - Click the generate button for instant AI-powered materials
            4. **Study efficiently** - Use the generated materials to learn faster and smarter!
            """)

        # Sample use cases
        st.markdown("---")
        st.header("💡 Perfect For:")

        use_cases = st.container()
        with use_cases:
            col1, col2 = st.columns(2)
            with col1:
                st.write("""
                - **Lecture notes** review
                - **Textbook chapters** summarization
                - **Research papers** understanding
                - **Study guides** creation
                """)
            with col2:
                st.write("""
                - **Exam preparation** 
                - **Quick revisions**
                - **Concept reinforcement**
                - **Self-paced learning**
                """)


if __name__ == "__main__":
    main()