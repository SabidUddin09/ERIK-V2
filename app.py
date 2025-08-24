import streamlit as st
from googlesearch import search
import wikipedia
import fitz  # PyMuPDF
import docx
import os

# ---------------------------
# Page Config & Intro
# ---------------------------
st.set_page_config(page_title="ERIK - Exceptional Resources & Intelligence Kernal", layout="wide")

st.title("🤖 ERIK - Exceptional Resources & Intelligence Kernal")
st.markdown("""
**Developed by: Sabid**  

Welcome to **ERIK**, your all-in-one academic assistant.  
It combines Google Search, Wikipedia, document analysis, quiz generation, flashcards, and Khan Academy references — to make studying smarter and faster.  
""")

# ---------------------------
# Session State Setup
# ---------------------------
if "users" not in st.session_state:
    st.session_state["users"] = {"admin": "1234"}  # default user
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "notes" not in st.session_state:
    st.session_state["notes"] = ""

# ---------------------------
# Authentication Functions
# ---------------------------
def signup(username, password):
    if username in st.session_state["users"]:
        return False
    st.session_state["users"][username] = password
    return True

def login(username, password):
    if username in st.session_state["users"] and st.session_state["users"][username] == password:
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        return True
    return False

# ---------------------------
# Helpers
# ---------------------------
def google_search(query, lang="en"):
    try:
        results = list(search(query, num_results=2, lang=lang))
        return "\n".join(results) if results else "❌ No results found."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def wikipedia_search(query, lang="en"):
    try:
        wikipedia.set_lang("bn" if lang=="bn" else "en")
        return wikipedia.summary(query, sentences=2)
    except:
        return "❌ No results found."

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

# ---------------------------
# Login / Signup
# ---------------------------
if not st.session_state["logged_in"]:
    choice = st.radio("Login / Signup", ["Login", "Signup"])
    if choice == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login(username, password):
                st.success("✅ Login successful!")
            else:
                st.error("❌ Invalid credentials")
    else:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Signup"):
            if signup(new_user, new_pass):
                st.success("🎉 Signup successful! Login now.")
            else:
                st.error("❌ Username already exists!")

# ---------------------------
# Main App Features
# ---------------------------
else:
    st.sidebar.success(f"👋 Welcome, {st.session_state['username']}")
    option = st.sidebar.radio("Choose Feature", [
        "Introduction", "Doubt Solver", "Topic Analyzer",
        "Document Upload", "Quiz Generator", "Flashcards",
        "Wikipedia Search", "Khan Academy Reference"
    ])

    # ---------------------------
    # Introduction
    # ---------------------------
    if option == "Introduction":
        st.subheader("👋 Meet ERIK")
        st.write("""
        ERIK (**Exceptional Resources & Intelligence Kernal**) is designed to help students with:
        - Breaking down complex topics  
        - Solving academic doubts instantly  
        - Creating quizzes & flashcards  
        - Extracting study notes from documents  
        - Searching the web & Wikipedia  
        - Linking to Khan Academy resources  
        """)

    # ---------------------------
    # Doubt Solver
    # ---------------------------
    elif option == "Doubt Solver":
        query = st.text_input("Ask your academic question (Bangla/English):")
        source = st.radio("Answer Source", ["Google", "Wikipedia", "Khan Academy"])
        if st.button("Get Answer"):
            lang = "bn" if any("\u0980" <= ch <= "\u09FF" for ch in query) else "en"
            if source == "Google":
                answer = google_search(query, lang)
            elif source == "Wikipedia":
                answer = wikipedia_search(query, lang)
            else:
                answer = f"🔗 Visit Khan Academy: https://www.khanacademy.org/search?search_again=1&page_search_query={query.replace(' ', '+')}"
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
    # Wikipedia Search
    # ---------------------------
    elif option == "Wikipedia Search":
        query = st.text_input("Search Wikipedia:")
        if st.button("Get Wiki"):
            if query:
                try:
                    summary = wikipedia.summary(query, sentences=3)
                    st.subheader("📖 Wikipedia Summary")
                    st.write(summary)
                except:
                    st.error("No results found.")

    # ---------------------------
    # Khan Academy Reference
    # ---------------------------
    elif option == "Khan Academy Reference":
        topic = st.text_input("Enter subject/topic:")
        if st.button("Find Courses"):
            st.subheader("🎥 Khan Academy Links")
            st.write(f"🔗 [Search {topic} on Khan Academy](https://www.khanacademy.org/search?search_again=1&page_search_query={topic.replace(' ','+')})")

    # ---------------------------
    # Chat History
    # ---------------------------
    st.subheader("💬 Chat History")
    for sender, msg in st.session_state["chat_history"]:
        st.markdown(f"**{sender}:** {msg}")

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["chat_history"] = []
        st.session_state["notes"] = ""
