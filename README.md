# Minerva - AI Tutor

Minerva is built to feel like a real tutor instead of a search engine. It helps students in the exact moment they’re stuck, using their own course materials, while guiding them toward understanding rather than just giving answers. Minerva is a real-time voice tutoring app. Students upload PDFs or connect to their Canvas, then start a live session. The tutor (powered by Gemini Live) talks through problems, asks check-in questions, and teaches step by step. It also uses Pinecone to ground responses in course content, builds small learning plans, tracks progress, and rewards users with coins they can spend in a small in-app store.


## Demo Video


https://github.com/user-attachments/assets/5f7a45ce-be72-47cd-b713-d4adc06400cc


## How to use:

1. In order to use canvas, get Canvas access token from the settings and url from canvas and paste it in the settings
2. Now you should be able to see your classes, Minerva will collect lecture data and then your able to click on one of them and then you can navigate to a specific assignment to talk to Minerva about it
3. Your now able to talk to Minerva about your specific assignment to help your understanding
4. If you want to upload a file instead, your able to in the custom tab, upload file, click upload pdf, type what you want to talk about, and then start session


## Tech Stack

- Backend: FastAPI, Python, WebSockets
- AI: Gemini Live + LangChain
- Retrieval: Pinecone
- Database: SQLite
- Frontend: HTML, CSS, JavaScript

## AI Disclosure

This project was developed with the assistance of AI tools, including Codex and Claude, primarily for coding support and debugging. All implementation decisions and final integrations were made by the development team.

## Track Selection

This project is designed for the Google Gemini Track where we used the gemini ai to promote learning by using voice commands, tracking streaks each day, and rewarding users with coins to by mascots to there account. Minerva Ai also has features with uploading files and full support for canvas.

## Quick Start

### 1. Backend Setup

Install dependencies and start the FastAPI server using `uv`:

```bash
# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Start the server
uv run python main.py
```

### 2. Frontend

Open your browser and navigate to:

[http://localhost:8000](http://localhost:8000)

The landing page is a login screen. New users can create an account at:

[http://localhost:8000/create-user](http://localhost:8000/create-user)

After logging in, the tutor is available at:

[http://localhost:8000/tutor](http://localhost:8000/tutor)

