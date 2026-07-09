================================================================================
                    NEXUS — Offline AI Agent  V3.0
================================================================================

1. WHAT IS NEXUS
--------------------------------------------------------------------------------
NEXUS is a fully offline AI assistant that runs entirely on your local machine.
It can summarise documents (TXT, PDF, Excel), answer general knowledge questions,
search the web, check your battery status, list running processes, search your
documents using RAG, and be trained on custom datasets with LoRA fine-tuning.

NEXUS runs through a compact Quick Menu overlay that floats on your desktop.
Press Ctrl+Alt+N at any time to show or hide it.


2. SYSTEM REQUIREMENTS
--------------------------------------------------------------------------------
  - Operating System : Windows 10 / 11 (64-bit)
  - RAM              : 8 GB minimum, 16 GB recommended
  - Disk Space       : ~3 GB (model + libraries)
  - Python           : 3.11.x (64-bit)
  - GPU              : Not required (runs on CPU)


3. INSTALLATION
--------------------------------------------------------------------------------
Follow these steps in order:

  Step 1 — Install Python 3.11 (64-bit) from https://python.org/downloads
           IMPORTANT: Check "Add Python to PATH" during installation.

  Step 2 — Open a command prompt (CMD) inside the nexus-agent folder.
           (Tip: Type "cmd" in the File Explorer address bar.)

  Step 3 — Create a virtual environment and install dependencies:
               python -m venv venv
               venv\Scripts\activate
               pip install -r requirements.txt

           If llama-cpp-python fails to install, you may need the Visual Studio
           C++ Build Tools.

  Step 4 — Download the AI model:
           Go to: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF
           Download: qwen2.5-3b-instruct-q4_k_m.gguf  (~2 GB)
           Place the file in: nexus-agent/model/

  Step 5 — You're ready! See "How to Start" below.


4. HOW TO START NEXUS
--------------------------------------------------------------------------------
  Double-click  quickopen.bat  in the nexus-agent folder.

  NEXUS launches as a compact, always-on-top Quick Menu overlay on the right
  side of your screen. It works like a floating calculator or chat widget.

  Features of the Quick Menu:
    - Always on top — stays visible over other windows
    - Drag the title bar to move it anywhere
    - Minimize button — hides to taskbar
    - Maximize button — toggles to fullscreen and back to compact mode
    - Close button — exits NEXUS
    - Three-dot menu — access Settings, Theme switching, Training, About
    - Slash command pills — quick access to /task, /web, /open, /remember, /help
    - Press Ctrl+Alt+N at any time to toggle the window on/off

  The model takes 30-60 seconds to load. The status bar shows loading progress.
  Once ready, type your request and press Enter.


5. WHAT YOU CAN ASK NEXUS
--------------------------------------------------------------------------------

  Summarise a file:
      "summarise notes.txt"
      "explain what is in report.pdf"
      "summarise data.xlsx"

  Summarise all files in a folder:
      "summarise all files in C:\Users\You\Documents\project"

  Ask a general question:
      "what is machine learning?"
      "explain how photosynthesis works"

  Search the web:
      "/web latest news about AI"
      "search for python tutorials"

  Check battery status:
      "what is my battery percentage?"
      "am I plugged in?"

  View running processes:
      "show running processes"

  Rename / copy / move / delete files:
      "rename notes.txt to old.txt"
      "copy report.pdf to D:\backup"
      "delete file temp.txt"

  Search your documents (RAG):
      "what do my files say about X?"
      "reindex my files"

  Open a URL:
      "open google.com"

  Stock prices:
      "get stock price of Reliance"

  Slash commands (type in the input box):
      /task  — schedule a task
      /web   — web search
      /open  — open a file or URL
      /remember — save a memory
      /help  — show available commands


6. SETTINGS & THEMES
--------------------------------------------------------------------------------
  Click the three-dot menu (top-right of the Quick Menu) to access:

    - Settings: API key, model config, folder permissions, install packages
    - Theme: Switch between Dark, Light, and Blue themes
    - Reset Model: Clear LoRA fine-tuning
    - Train on Dataset: Select a folder of training data
    - About NEXUS: Version info, status, memory count


7. HOW TO TRAIN NEXUS WITH YOUR OWN DATA
--------------------------------------------------------------------------------
You can teach NEXUS new knowledge by training it on your own Q&A pairs.

  Step 1 — Create a .txt file in the  datasets/  folder.
           See  datasets/README.txt  for the required format.

           Example:
               Q: What is our company motto?
               A: Our company motto is "Innovation through simplicity."

  Step 2 — Use the three-dot menu > "Train on Dataset" in the Quick Menu,
           or run:  python src/trainer.py
           Training will take 30 minutes to 3 hours depending on your PC.

  Step 3 — After training completes, restart NEXUS (quickopen.bat).
           NEXUS will automatically detect and load your custom training.


8. WEB SEARCH SETUP (OPTIONAL)
--------------------------------------------------------------------------------
  NEXUS can search the web using the Google Gemini API (free tier).

  Step 1 — Get a free API key at: https://aistudio.google.com/apikey
  Step 2 — Open Settings (three-dot menu) and paste your key in the API Key field
           Or add it to config/api_keys.json:
               {"gemini_api_key": "YOUR_KEY_HERE"}


9. TROUBLESHOOTING
--------------------------------------------------------------------------------

  Problem: "Model file not found" error on startup
  Solution: Make sure qwen2.5-3b-instruct-q4_k_m.gguf is in the model/ folder.

  Problem: llama-cpp-python fails to install
  Solution: Install Visual Studio C++ Build Tools first, then retry.

  Problem: Agent is very slow / runs out of memory
  Solution: Open Settings (three-dot menu) and reduce max_tokens or n_ctx.

  Problem: "Permission denied" when summarising a file
  Solution: Open Settings > Folder Permissions and add the folder.

  Problem: Training crashes with "out of memory"
  Solution: Keep your dataset small (under 50 Q&A pairs).

  Problem: Agent gives wrong or nonsensical answers
  Solution: This is a 3B parameter model running locally — for best results:
            - Ask clear, specific questions
            - Keep file sizes reasonable (under 50 pages)
            - Train on domain-specific data for specialised topics


================================================================================
                     NEXUS — Built Offline. Runs Offline.
================================================================================
