import streamlit as st
from googlesearch import search
import requests
from bs4 import BeautifulSoup

# -------------------------------
# Authentication (local storage)
# -------------------------------
if "users" not in st.session_state:
    st.session_state["users"] = {"admin": "1234"}  # default user
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

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

# -------------------------------
# Google Search Answer Finder
# -------------------------------
def get_answer_from_google(query, lang="en"):
    try:
        results = list(search(query, num_results=3, lang=lang))
        if not results:
            return "❌ No results found."

        url = results[0]
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract first paragraph
        paragraphs = soup.find_all("p")
        if paragraphs:
            return paragraphs[0].text.strip() + f"\n\n🔗 Source: {url}"
        else:
            return f"Couldn't extract details. Check here: {url}"
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# -------------------------------
# Streamlit UI
# -------------------------------
st.title("🤖 ERIK – AI Chatbot (Google Powered)")

if not st.session_state["logged_in"]:
    choice = st.radio("Login / Signup", ["Login", "Signup"])

    if choice == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login(username, password):
                st.success("✅ Login successful!")
            else:
                st.error("❌ Invalid username or password")
    else:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Signup"):
            if signup(new_user, new_pass):
                st.success("🎉 Signup successful! Please login now.")
            else:
                st.error("❌ Username already exists!")

else:
    st.write(f"👋 Welcome, **{st.session_state['username']}**")
    user_input = st.text_input("Ask me anything (English or Bangla)...")

    if st.button("Send") and user_input:
        lang = "bn" if any("\u0980" <= ch <= "\u09FF" for ch in user_input) else "en"
        answer = get_answer_from_google(user_input, lang=lang)
        st.session_state["chat_history"].append(("You", user_input))
        st.session_state["chat_history"].append(("ERIK", answer))

    # Chat history
    for sender, msg in st.session_state["chat_history"]:
        if sender == "You":
            st.markdown(f"**🧑 You:** {msg}")
        else:
            st.markdown(f"**🤖 ERIK:** {msg}")

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["chat_history"] = []
