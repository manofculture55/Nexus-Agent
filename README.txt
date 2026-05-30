================================================================================
                    NEXUS — Offline AI Agent  v1.0
================================================================================

1. WHAT IS NEXUS
--------------------------------------------------------------------------------
NEXUS is a fully offline AI assistant that runs entirely on your local machine.
It can summarise documents (TXT, PDF, Excel), answer general knowledge questions,
check your battery status, list running processes, and even be trained on your
own custom Q&A datasets using LoRA fine-tuning. No internet connection required.


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

  Step 3 — Install required libraries:
               pip install -r requirements.txt

           If llama-cpp-python fails to install, you may need the Visual Studio
           C++ Build Tools. See docs/NEXUS_TODO.md Section 0.3 for details.

  Step 4 — Download the AI model:
           Go to: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF
           Download: qwen2.5-3b-instruct-q4_k_m.gguf  (~2 GB)
           Place the file in: nexus-agent/model/

  Step 5 — You're ready! See "How to Start" below.


4. HOW TO START THE AGENT
--------------------------------------------------------------------------------
  Option A: Double-click  start.bat  in the nexus-agent folder.
  Option B: Open CMD in the nexus-agent folder and run:
                python src/agent.py

  On first launch, NEXUS will ask you to grant access to at least one folder.
  This is a security measure — NEXUS will only read files in folders you approve.

  The model takes 30–60 seconds to load. After that, you'll see the NEXUS prompt:
      You: _

  Type your request and press Enter. Type "exit" to quit.


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
      "what is the difference between Python and Java?"

  Check battery status:
      "what is my battery percentage?"
      "am I plugged in?"

  View running processes:
      "show running processes"
      "what programs are using the most memory?"

  Get help:
      "help"

  Exit:
      "exit"


6. HOW TO TRAIN NEXUS WITH YOUR OWN DATA
--------------------------------------------------------------------------------
You can teach NEXUS new knowledge by training it on your own Q&A pairs.

  Step 1 — Create a .txt file in the  datasets/  folder.
           See  datasets/README.txt  for the required format.

           Example:
               Q: What is our company motto?
               A: Our company motto is "Innovation through simplicity."

               Q: Who is the CEO?
               A: The CEO is Jane Smith, appointed in 2022.

  Step 2 — Double-click  train.bat  (or run:  python src/trainer.py).
           Training will take 30 minutes to 3 hours depending on your PC
           and the size of your dataset. Progress is shown in the console.

  Step 3 — After training completes, restart the agent (start.bat).
           NEXUS will automatically detect and load your custom training.

  NOTE:   Training a 3B model on CPU requires 16 GB+ RAM. If you have less,
          keep your dataset under 50 Q&A pairs, or use Google Colab (free GPU)
          and copy the lora-weights/ folder back to your machine.


7. TROUBLESHOOTING
--------------------------------------------------------------------------------

  Problem: "Model file not found" error on startup
  Solution: Make sure qwen2.5-3b-instruct-q4_k_m.gguf is in the model/ folder.
            Download it from HuggingFace (see Installation Step 4).

  Problem: llama-cpp-python fails to install
  Solution: Install Visual Studio C++ Build Tools first, then retry.
            Alternatively, search for a pre-built wheel for your Python version.

  Problem: Agent is very slow / runs out of memory
  Solution: - Close other programs to free RAM.
            - In config/settings.json, reduce "n_ctx" from 8192 to 4096.
            - Reduce "max_tokens" from 512 to 256.

  Problem: "Permission denied" when summarising a file
  Solution: The file is not in an allowed folder. Delete config/permissions.json
            and restart the agent to re-run the setup wizard, or add the folder
            path manually to config/permissions.json.

  Problem: Training crashes with "out of memory"
  Solution: - Keep your dataset small (under 50 Q&A pairs).
            - Close all other programs before training.
            - Consider using Google Colab with a free GPU instead.

  Problem: Agent gives wrong or nonsensical answers
  Solution: This is a 3B parameter model running locally — it won't match
            ChatGPT-level quality. For best results:
            - Ask clear, specific questions.
            - Keep file sizes reasonable (under 50 pages).
            - Train on domain-specific data for specialised topics.


================================================================================
                         NEXUS — Built Offline. Runs Offline.
================================================================================
