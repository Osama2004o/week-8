"""
Application Entrypoint
======================
Runs the Agentic RAG FastAPI server:
    python main.py
Or via uvicorn:
    uvicorn main:app --reload
"""

import uvicorn
from api.main import app
from config.settings import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=True)
