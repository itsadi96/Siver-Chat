import os
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("antigravity-bridge")

app = FastAPI(title="Antigravity Gemini Bridge (WSL)")

# Paths to credentials (Native WSL path)
CREDS_PATH = os.path.expanduser("~/.gemini/oauth_creds.json")

def get_credentials():
    if not os.path.exists(CREDS_PATH):
        raise FileNotFoundError(f"Credentials not found at {CREDS_PATH}")
    
    with open(CREDS_PATH, 'r') as f:
        creds_data = json.load(f)
    
    # Standard Google CLI/Common Client IDs
    # These are often required for refreshing personal OAuth tokens
    client_id = creds_data.get("client_id")
    client_secret = creds_data.get("client_secret")

    creds = Credentials(
        token=creds_data.get("access_token"),
        refresh_token=creds_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=creds_data.get("scope", "").split()
    )
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            logger.info("Refreshing access token...")
            creds.refresh(GoogleRequest())
        except Exception as e:
            logger.warning(f"Refresh failed (likely missing client_id/secret): {e}")
        
    return creds

def init_genai():
    try:
        creds = get_credentials()
        genai.configure(credentials=creds)
        logger.info("Gemini SDK configured successfully with WSL OAuth session.")
    except Exception as e:
        logger.error(f"Failed to configure Gemini SDK: {e}")
        raise

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model_name = body.get("model", "gemini-3-flash-preview")
    
    # Allow mapping any gpt model to flash
    if "gpt" in model_name:
        model_name = "gemini-3-flash-preview"
    
    messages = body.get("messages", [])
    contents = []
    
    # Simple message conversion
    for m in messages:
        role = m["role"]
        content = m["content"]
        if role == "system":
            # Some Gemini versions handle system instructions separately
            # We'll prepend it contextually if the list is empty
            continue
        
        g_role = "user" if role == "user" else "model"
        contents.append({"role": g_role, "parts": [content]})

    try:
        model = genai.GenerativeModel(model_name)
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
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
    except Exception as e:
        logger.error(f"Error generating completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "gemini-3-flash-preview", "object": "model", "owned_by": "google"},
            {"id": "gemini-3-pro-preview", "object": "model", "owned_by": "google"}
        ]
    }

if __name__ == "__main__":
    init_genai()
    print("\n" + "="*50)
    print("ANTIGRAVITY GEMINI BRIDGE (WSL) RUNNING")
    print("Endpoint: http://127.0.0.1:18795/v1")
    print("="*50 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=18795)
