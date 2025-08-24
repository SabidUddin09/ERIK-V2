import streamlit as st
from googlesearch import search
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import docx
import re

# ---------------------------
# Page Config & Welcome
# ---------------------------
st.set_page_config(page_title="ERIK - Exceptional Resources & Intelligence Kernal", layout="wide")
st.title("🤖 ERIK - Exceptional Resources & Intelligence Kernal")
st.markdown("""
**Developed by: Sabid**

Welcome to **ERIK**, your all-in-one academic assistant!  
It helps you study smarter by automatically generating answers, analyzing topics, creating quizzes, flashcards, and extracting notes from documents.
""")

# ---------------------------
# Session State Setup
# ---------------------------
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "notes" not in st.session_state:
    st.session_state["notes"] = ""

# ---------------------------
# Helpers
# ---------------------------
def extract_text_from_file(uploaded_file):
    text = ""
    if uploaded_file.type == "application/pdf":
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page in doc:
            text += page.get_text()
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(uploaded_file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    else:
        text = uploaded_file.read().decode("utf-8")
    return text

def detect_language(text):
    """Return 'bn' if Bangla characters found, else 'en'"""
    if re.search("[\u0980-\u09FF]", text):
        return 'bn'
    return 'en'

def google_auto_answer(query):
    """Search Google and return a concise paragraph as answer"""
    lang = detect_language(query)
    try:
        results = list(search(query, num_results=3))
        if not results:
            return "❌ No results found."

        for url in results:
            try:
                response = requests.get(url, timeout=5)
                soup = BeautifulSoup(response.text, "html.parser")
                paragraphs = soup.find_all("p")
                for p in paragraphs:
                    text = p.get_text().strip()
                    if len(text.split()) > 10:
                        return text + f"\n\n🔗 Source: {url}"
            except:
                continue
        return f"Couldn't extract details. Check here: {results[0]}"
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ---------------------------
# Sidebar - Features
# ---------------------------
option = st.sidebar.radio("Choose Feature", [
    "Introduction", "Doubt Solver", "Topic Analyzer",
    "Document Upload", "Quiz Generator", "Flashcards"
])

# ---------------------------
# Introduction
# ---------------------------
if option == "Introduction":
    st.subheader("👋 Meet ERIK")
    st.write("""
    ERIK (**Exceptional Resources & Intelligence Kernal**) is designed to help students with:
    - Automatically answering academic questions (Bangla + English)
    - Breaking down complex topics
    - Creating quizzes & flashcards
    - Extracting study notes from documents
    """)

# ---------------------------
# Doubt Solver
# ---------------------------
elif option == "Doubt Solver":
    query = st.text_input("Ask your academic question (Bangla/English):")
    if st.button("Get Answer"):
        if query:
            answer = google_auto_answer(query)
            st.session_state["chat_history"].append(("You", query))
            st.session_state["chat_history"].append(("ERIK", answer))

# ---------------------------
# Topic Analyzer
# ---------------------------
elif option == "Topic Analyzer":
    topic = st.text_input("Enter topic:")
    if st.button("Analyze"):
        st.subheader(f"🔎 Topic Breakdown: {topic}")
        st.markdown(f"""
        **Key Concepts:**  
        - Definition of {topic}  
        - Importance in academics  
        - Applications  

        **Example Questions:**  
        1. Define {topic}.  
        2. What are its applications?  
        3. Why is it important?  
        """)

# ---------------------------
# Document Upload
# ---------------------------
elif option == "Document Upload":
    uploaded_file = st.file_uploader("Upload PDF, DOCX, or TXT")
    if uploaded_file:
        text = extract_text_from_file(uploaded_file)
        st.session_state["notes"] = text
        st.subheader("📄 Extracted Notes:")
        st.text_area("Preview", text[:1000])

# ---------------------------
# Quiz Generator
# ---------------------------
elif option == "Quiz Generator":
    if st.session_state["notes"]:
        st.subheader("📝 Sample Quiz")
        st.write("**MCQ:** What is the main concept?")
        st.write("**Short Q:** Explain in 2 lines.")
        st.write("**Creative Q:** Relate it to real life.")
    else:
        st.warning("⚠️ Upload notes first!")

# ---------------------------
# Flashcards
# ---------------------------
elif option == "Flashcards":
    if st.session_state["notes"]:
        st.subheader("📌 Flashcards")
        sentences = st.session_state["notes"].split(".")
        for i, s in enumerate(sentences[:5]):
            if len(s.strip())>5:
                st.write(f"**Q{i+1}:** About '{s.strip()[:20]}…'?")
                st.write(f"**A{i+1}:** {s.strip()}")
    else:
        st.warning("⚠️ Upload notes first!")

# ---------------------------
# Chat History
# ---------------------------
st.subheader("💬 Chat History")
for sender, msg in st.session_state["chat_history"]:
    st.markdown(f"**{sender}:** {msg}")
