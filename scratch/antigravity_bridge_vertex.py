import os
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException
import uvicorn
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
import google.auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("antigravity-bridge")

app = FastAPI(title="Antigravity Gemini Bridge (Vertex AI)")

# Paths to credentials
CREDS_PATH = os.path.expanduser("~/.gemini/oauth_creds.json")

def init_vertex():
    try:
        if not os.path.exists(CREDS_PATH):
            raise FileNotFoundError(f"Credentials not found at {CREDS_PATH}")
        
        with open(CREDS_PATH, 'r') as f:
            creds_data = json.load(f)
        
        creds = Credentials(
            token=creds_data.get("access_token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
            scopes=creds_data.get("scope", "").split()
        )
        
        if creds.expired and creds.refresh_token:
            logger.info("Refreshing token...")
            creds.refresh(GoogleRequest())
            
        # Try to discover project ID
        project = None
        try:
            _, project = google.auth.default(credentials=creds)
        except:
            pass
        
        if not project:
            # Fallback: check an environment variable or a known one
            project = os.environ.get("GOOGLE_CLOUD_PROJECT", "shigga-app-404")

        vertexai.init(project=project, location="us-central1", credentials=creds)
        logger.info(f"Vertex AI initialized for project: {project}")
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}")
        raise

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model_name = body.get("model", "gemini-1.5-flash-002") # Use Vertex ID format
    
    # Map to Vertex Flash
    if "flash" in model_name or "gpt" in model_name:
        model_name = "gemini-1.5-flash-002"
    elif "pro" in model_name:
        model_name = "gemini-1.5-pro-002"

    messages = body.get("messages", [])
    contents = []
    
    for m in messages:
        role = m["role"]
        text = m["content"]
        if role == "system": continue
        
        g_role = "user" if role == "user" else "model"
        contents.append(Content(role=g_role, parts=[Part.from_text(text)]))

    try:
        model = GenerativeModel(model_name)
        response = await asyncio.to_thread(model.generate_content, contents)
        
        return {
            "id": f"chatcmpl-{os.urandom(8).hex()}",
            "object": "chat.completion",
            "created": 123456789,
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {"total_tokens": 0}
        }
    except Exception as e:
        logger.error(f"Vertex AI Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "gemini-1.5-flash-002", "object": "model", "owned_by": "google"},
            {"id": "gemini-1.5-pro-002", "object": "model", "owned_by": "google"}
        ]
    }

if __name__ == "__main__":
    init_vertex()
    print("\n" + "="*50)
    print("ANTIGRAVITY BRIDGE (VERTEX AI) RUNNING")
    print("Endpoint: http://127.0.0.1:18795/v1")
    print("="*50 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=18795)
