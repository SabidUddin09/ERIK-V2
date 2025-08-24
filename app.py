import os
import re
import time
import html
import requests
import streamlit as st

# Optional libs (loaded lazily)
# - transformers (FLAN-T5 fallback + optional MarianMT translation)
# - gpt4all (fully offline local models)
# - ollama (local Mistral/Llama via Ollama runtime)
# - duckduckgo_search (search without API key)
# - bs4 (simple page text extraction)
# - langdetect (detect Bangla vs English)

# ------------------------------
# Helpers: safe optional imports
# ------------------------------
def safe_import(modname, obj=None):
    try:
        module = __import__(modname, fromlist=[obj] if obj else [])
        return getattr(module, obj) if obj else module
    except Exception:
        return None

DDGS = safe_import("duckduckgo_search", "DDGS")
bs4 = safe_import("bs4")
BeautifulSoup = getattr(bs4, "BeautifulSoup") if bs4 else None
langdetect = safe_import("langdetect")
detect_lang = getattr(langdetect, "detect") if langdetect else None

ollama = safe_import("ollama")
gpt4all = safe_import("gpt4all")
transformers = safe_import("transformers")
AutoTokenizer = getattr(transformers, "AutoTokenizer", None) if transformers else None
AutoModelForSeq2SeqLM = getattr(transformers, "AutoModelForSeq2SeqLM", None) if transformers else None
pipeline = getattr(transformers, "pipeline", None) if transformers else None

# ------------------------------
# Streamlit Page Config
# ------------------------------
st.set_page_config(page_title="E.R.I.K. – Local Chatbot", page_icon="🤖", layout="wide")

st.markdown(
    """
    <div style="background-color:#1f2937;padding:16px;border-radius:12px;margin-bottom:12px">
      <h1 style="color:white;text-align:center;margin:0">🤖 E.R.I.K.</h1>
      <p style="color:#e5e7eb;text-align:center;margin:0">Exceptional Resources & Intelligence Kernel — Offline/Local Chatbot (No OpenAI API)</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------------------
# Sidebar: Model & Settings
# ------------------------------
st.sidebar.header("⚙️ Settings")

model_choice = st.sidebar.selectbox(
    "Local model backend (no external API):",
    [
        "Ollama (Mistral/Llama)",
        "GPT4All (offline)",
        "Transformers: FLAN-T5 (CPU fallback)"
    ],
    help="Pick the best available on your machine. Ollama usually gives the best quality; FLAN-T5 is the lightest."
)

use_web = st.sidebar.checkbox(
    "🔎 Use web search for factual/current questions",
    value=True,
    help="Uses DuckDuckGo (no API key) + simple page fetch to ground answers."
)

max_search_results = st.sidebar.slider("Search results to use", 1, 8, 3)
web_timeout = st.sidebar.slider("Per page fetch timeout (sec)", 3, 15, 7)

enable_bn_translate = st.sidebar.checkbox(
    "🌐 Enable offline Bangla↔English translation (MarianMT)",
    value=False,
    help="Improves Bangla with English-focused models. Downloads models on first run."
)

gen_tokens = st.sidebar.slider("Max new tokens", 64, 1024, 256)
temperature = st.sidebar.slider("Creativity (temperature)", 0.0, 1.5, 0.7)
top_p = st.sidebar.slider("Top-p nucleus sampling", 0.1, 1.0, 0.9)

st.sidebar.info("Tip: For **best local quality**, install **Ollama** and pull a model: `ollama pull mistral`")

# ------------------------------
# Lazy model loaders
# ------------------------------
@st.cache_resource(show_spinner=False)
def load_ollama_model(name="mistral"):
    if not ollama:
        raise RuntimeError("ollama python package not installed. `pip install ollama` and install the Ollama app.")
    # Ensure the model is available in Ollama (user must `ollama pull mistral`).
    return {"name": name}  # we just store the name; ollama runtime handles it

@st.cache_resource(show_spinner=False)
def load_gpt4all_model(path_or_name="ggml-gpt4all-j-v1.3-groovy.bin"):
    if not gpt4all:
        raise RuntimeError("gpt4all package not installed. `pip install gpt4all` and download a model.")
    from gpt4all import GPT4All
    return GPT4All(path_or_name)

@st.cache_resource(show_spinner=False)
def load_flan_t5_pipeline():
    if not transformers:
        raise RuntimeError("transformers not installed. `pip install transformers torch`")
    # Smallest decent model for CPU: flan-t5-base (multitask, decent English; partial Bangla)
    pipe = pipeline("text2text-generation", model="google/flan-t5-base")
    return pipe

@st.cache_resource(show_spinner=False)
def load_marian_bn_en():
    if not transformers:
        raise RuntimeError("transformers not installed. `pip install transformers torch`")
    bn_en = pipeline("translation", model="Helsinki-NLP/opus-mt-bn-en")
    en_bn = pipeline("translation", model="Helsinki-NLP/opus-mt-en-bn")
    return bn_en, en_bn

# ------------------------------
# Web search & retrieval
# ------------------------------
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
        return text.strip()[:8000]  # limit
    except Exception:
        return ""

def build_retrieval_context(query, k=max_search_results, timeout=web_timeout):
    hits = ddg_search(query, max_results=k)
    chunks = []
    for h in hits:
        url = h.get("href")
        if not url:
            continue
        page_text = fetch_page_text(url, timeout=timeout)
        if not page_text:
            continue
        snippet = h.get("snippet") or ""
        title = h.get("title") or url
        # keep short portion of page
        page_excerpt = page_text[:1200]
        chunks.append(f"Title: {title}\nURL: {url}\nSnippet: {snippet}\nPage excerpt: {page_excerpt}")
    if not chunks and hits:
        # fallback to just SERP snippets
        for h in hits:
            chunks.append(f"Title: {h.get('title')}\nURL: {h.get('href')}\nSnippet: {h.get('snippet')}")
    return "\n\n".join(chunks)

# ------------------------------
# Prompt builder
# ------------------------------
def build_prompt(user_query, retrieved_text=""):
    sys = (
        "You are E.R.I.K., a helpful, concise assistant. "
        "Answer accurately. If you used web results, cite them inline as [Source: URL]. "
        "If question is in Bangla, answer in Bangla; otherwise answer in the user's language. "
        "For math or steps, be clear and structured."
    )
    if retrieved_text:
        context = (
            f"Relevant web information (may be partial; verify consistency):\n"
            f"{retrieved_text}\n"
            "When you use any line from above, add [Source: URL] after the sentence.\n"
        )
    else:
        context = "No external web info was fetched for this question.\n"
    return f"{sys}\n\n{context}\nUser question:\n{user_query}\n\nAssistant answer:"

# ------------------------------
# Generators per backend
# ------------------------------
def generate_with_ollama(prompt, model_name="mistral", max_tokens=256, temperature=0.7, top_p=0.9):
    if not ollama:
        raise RuntimeError("ollama not available.")
    resp = ollama.chat(
        model=model_name,
        messages=[{"role": "system", "content": "You are E.R.I.K., a helpful assistant."},
                  {"role": "user", "content": prompt}],
        options={"temperature": float(temperature), "top_p": float(top_p), "num_predict": int(max_tokens)}
    )
    return resp["message"]["content"].strip()

def generate_with_gpt4all(model, prompt, max_tokens=256, temperature=0.7, top_p=0.9):
    # GPT4All simple generate
    with model.chat_session():
        out = model.generate(
            prompt,
            max_tokens=max_tokens,
            temp=temperature,
            top_p=top_p
        )
    return out.strip()

def generate_with_flan(pipe, prompt, max_tokens=256, temperature=0.7, top_p=0.9):
    out = pipe(
        prompt,
        max_new_tokens=max_tokens,
        do_sample=True,
        temperature=float(temperature),
        top_p=float(top_p)
    )
    return out[0]["generated_text"].strip()

# ------------------------------
# Language utilities
# ------------------------------
def looks_bangla(text):
    if detect_lang:
        try:
            return detect_lang(text) == "bn"
        except Exception:
            pass
    # Heuristic fallback: presence of Bengali unicode block
    return bool(re.search(r"[\u0980-\u09FF]", text))

def translate_bn_en_en_bn(text, direction, bn_en_pipe, en_bn_pipe):
    if direction == "bn2en":
        return bn_en_pipe(text)[0]["translation_text"]
    else:
        return en_bn_pipe(text)[0]["translation_text"]

# ------------------------------
# Session state
# ------------------------------
if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: {role, content}

# ------------------------------
# UI: Chat
# ------------------------------
with st.container():
    for msg in st.session_state.history:
        if msg["role"] == "user":
            st.markdown(f"**🧑 You:** {msg['content']}")
        else:
            st.markdown(f"**🤖 E.R.I.K.:** {msg['content']}")

st.divider()
user_text = st.text_area("💬 Ask anything (supports বাংলা too):", height=120, placeholder="e.g., Explain Fourier series | বাংলাদেশের স্বাধীনতা যুদ্ধ সম্পর্কে বলো | Who won the last ICC match and where?")
col1, col2 = st.columns([1, 1])
send = col1.button("Send")
clear = col2.button("Clear Chat")

if clear:
    st.session_state.history = []
    st.experimental_rerun()

# ------------------------------
# Handle send
# ------------------------------
if send and user_text.strip():
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.spinner("Thinking locally…"):
        # Optional translation setup
        bn_en_pipe = en_bn_pipe = None
        user_is_bn = looks_bangla(user_text)
        if enable_bn_translate and user_is_bn:
            try:
                bn_en_pipe, en_bn_pipe = load_marian_bn_en()
            except Exception as e:
                st.warning(f"Bangla translation pipelines unavailable: {e}")

        # Build retrieval context if enabled
        retrieval = ""
        if use_web:
            retrieval = build_retrieval_context(user_text, k=max_search_results, timeout=web_timeout)

        prompt = build_prompt(user_text if not (enable_bn_translate and user_is_bn and bn_en_pipe) else translate_bn_en_en_bn(user_text, "bn2en", bn_en_pipe, en_bn_pipe), retrieved_text=retrieval)

        # Generate via selected backend
        try:
            if model_choice.startswith("Ollama"):
                # Load
                backend = load_ollama_model("mistral")
                raw_answer = generate_with_ollama(prompt, model_name=backend["name"], max_tokens=gen_tokens, temperature=temperature, top_p=top_p)

            elif model_choice.startswith("GPT4All"):
                # The user should provide their local model filename if different
                model_path = st.sidebar.text_input("GPT4All model file (once downloaded):", "ggml-gpt4all-j-v1.3-groovy.bin")
                model = load_gpt4all_model(model_path)
                raw_answer = generate_with_gpt4all(model, prompt, max_tokens=gen_tokens, temperature=temperature, top_p=top_p)

            else:  # FLAN-T5 fallback
                pipe = load_flan_t5_pipeline()
                raw_answer = generate_with_flan(pipe, prompt, max_tokens=gen_tokens, temperature=temperature, top_p=top_p)

            # Translate back to Bangla if needed
            if enable_bn_translate and user_is_bn and en_bn_pipe:
                final_answer = translate_bn_en_en_bn(raw_answer, "en2bn", bn_en_pipe, en_bn_pipe)
            else:
                final_answer = raw_answer

        except Exception as e:
            final_answer = f"Sorry, the local model backend failed: {e}\n\nTry another backend in the sidebar, or install the missing package/model."

    st.session_state.history.append({"role": "assistant", "content": final_answer})
    st.experimental_rerun()
