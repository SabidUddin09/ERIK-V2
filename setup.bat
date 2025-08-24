@echo off
echo 🔹 Starting E.R.I.K. Chatbot Setup…

:: 1. Create virtual environment
python -m venv venv
call venv\Scripts\activate

:: 2. Update pip
python -m pip install --upgrade pip

:: 3. Install required Python packages
pip install --upgrade pip
pip install streamlit requests ollama gpt4all transformers torch duckduckgo_search beautifulsoup4 langdetect

:: 4. Pull Ollama model (if Ollama is installed)
where ollama >nul 2>nul
if %errorlevel%==0 (
    ollama pull mistral
) else (
    echo ⚠️ Ollama not found. Please install Ollama from https://ollama.com
)

echo ✅ Setup complete!
echo Run your chatbot with: streamlit run app.py
pause
