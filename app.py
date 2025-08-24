import os
import re
import requests
import streamlit as st

# Optional imports
def safe_import(modname, obj=None):
    try:
        module = __import__(modname, fromlist=[obj] if obj else [])
        return getattr(module, obj) if obj else module
    except Exception:
        return None

# Libraries
DDGS = safe_import("duckduckgo_search", "DDGS")
bs4 = safe_import("bs4")
BeautifulSoup = getattr(bs4, "BeautifulSoup") if bs4 else None
langdetect = safe_import("langdetect")
detect_lang = getattr(langdetect, "detect") if langdetect else None
ollama = safe_import("ollama")
gpt4all = safe_import("gpt4all")
transformers = safe_import("transformers")
pipeline = getattr(transformers, "pipeline", None) if transformers else None

# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="E.R.I.K.", page_icon="🤖", layout="wide")
st.title("🤖 E.R.I.K. – Local Chatbot")
st.write("Exceptional Resources & Intelligence Kernel — Offline/Local Chatbot (No OpenAI API)")

# Sidebar settings
st.sidebar.header("⚙️ Settings")
model_choice = st.sidebar.selectbox(
    "Local model backend:",
    ["Ollama (Mistral/Llama)", "GPT4All (offline)", "FLAN-T5 (CPU fallback)"]
)
use_web = st.sidebar.checkbox("Use web search", value=True)
enable_bn_translate = st.sidebar.checkbox("Enable Bangla↔English translation", value=False)
max_tokens = st.sidebar.slider("Max new tokens", 64, 1024, 256)
temperature = st.sidebar.slider("Creativity (temperature)", 0.0, 1.5, 0.7)
top_p = st.sidebar.slider("Top-p sampling", 0.1, 1.0, 0.9)

st.sidebar.info("Tip: For best quality, install Ollama and pull a model: `ollama pull mistral`")

# ---------------- Session state ----------------
if "history" not in st.session_state:
    st.session_state.history = []

# ---------------- Helper functions ----------------
def fetch_page_text(url, timeout=7):
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return ""
        html_text = r.text
        if BeautifulSoup:
            soup = BeautifulSoup(html_text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator=" ")
        else:
            text = re.sub("<[^<]+?>", " ", html_text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()[:8000]
    except Exception:
        return ""

def ddg_search(query, max_results=3):
    results = []
    if not DDGS:
        return results
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, safesearch="moderate", max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "source": r.get("source", ""),
                })
    except Exception:
        pass
    return results

def build_prompt(user_query, retrieved_text=""):
    sys = "You are E.R.I.K., a helpful, concise assistant."
    if retrieved_text:
        context = f"Web info:\n{retrieved_text}\nUse [Source: URL] if needed.\n"
    else:
        context = ""
    return f"{sys}\n{context}\nUser question:\n{user_query}\nAnswer:"

def looks_bangla(text):
    if detect_lang:
        try:
            return detect_lang(text) == "bn"
        except:
            return False
    return bool(re.search(r"[\u0980-\u09FF]", text))

def translate(text, direction="bn2en"):
    if not transformers:
        return text
    if direction == "bn2en":
        pipe = pipeline("translation", model="Helsinki-NLP/opus-mt-bn-en")
    else:
        pipe = pipeline("translation", model="Helsinki-NLP/opus-mt-en-bn")
    return pipe(text)[0]["translation_text"]

# ---------------- Model loaders ----------------
@st.cache_resource
def load_ollama_model(name="mistral"):
    if not ollama:
        raise RuntimeError("Install ollama package")
    return {"name": name}

@st.cache_resource
def load_gpt4all_model(path="ggml-gpt4all-j-v1.3-groovy.bin"):
    if not gpt4all:
        raise RuntimeError("Install gpt4all package")
    from gpt4all import GPT4All
    return GPT4All(path)

@st.cache_resource
def load_flan_pipeline():
    if not transformers:
        raise RuntimeError("Install transformers and torch")
    return pipeline("text2text-generation", model="google/flan-t5-base")

# ---------------- Generate responses ----------------
def generate_response(prompt):
    try:
        if model_choice.startswith("Ollama"):
            backend = load_ollama_model()
            resp = ollama.chat(model=backend["name"],
                               messages=[{"role": "user", "content": prompt}])
            return resp["message"]["content"].strip()
        elif model_choice.startswith("GPT4All"):
            model_path = "ggml-gpt4all-j-v1.3-groovy.bin"
            model = load_gpt4all_model(model_path)
            with model.chat_session():
                return model.generate(prompt, max_tokens=max_tokens, temp=temperature, top_p=top_p).strip()
        else:
            pipe = load_flan_pipeline()
            return pipe(prompt, max_new_tokens=max_tokens, do_sample=True,
                        temperature=temperature, top_p=top_p)[0]["generated_text"].strip()
    except Exception as e:
        return f"Error generating response: {e}"

# ---------------- Chat UI ----------------
user_input = st.text_area("💬 Ask anything (Bangla/English supported):", height=120)
col1, col2 = st.columns([1,1])
send = col1.button("Send")
clear = col2.button("Clear Chat")

if clear:
    st.session_state.history = []
    st.experimental_rerun()

if send and user_input.strip():
    st.session_state.history.append({"role": "user", "content": user_input})

    # Optional translation
    text_for_model = user_input
    if enable_bn_translate and looks_bangla(user_input):
        text_for_model = translate(user_input, "bn2en")

    # Optional web search
    retrieval = ""
    if use_web:
        hits = ddg_search(user_input)
        retrieval = "\n".join([f"{h['title']} - {h['href']}" for h in hits])

    prompt = build_prompt(text_for_model, retrieval)
    answer = generate_response(prompt)

    # Translate back to Bangla if needed
    if enable_bn_translate and looks_bangla(user_input):
        answer = translate(answer, "en2bn")

    st.session_state.history.append({"role": "assistant", "content": answer})
    st.experimental_rerun()

# Display chat history
for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(f"**🧑 You:** {msg['content']}")
    else:
        st.markdown(f"**🤖 E.R.I.K.:** {msg['content']}")
