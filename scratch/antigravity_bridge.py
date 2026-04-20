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

app = FastAPI(title="Antigravity Gemini Bridge")

# Paths to credentials
CREDS_PATH = r"\\wsl.localhost\Ubuntu-22.04\home\adi\.gemini\oauth_creds.json"

def get_credentials():
    if not os.path.exists(CREDS_PATH):
        raise FileNotFoundError(f"Credentials not found at {CREDS_PATH}")
    
    with open(CREDS_PATH, 'r') as f:
        creds_data = json.load(f)
    
    # Standard Google CLI/Common Client ID if missing
    # Many users use the Google SDK client ID: 764086051750-6v0vuvk8uub447p0c8l7re5dca2iibmd.apps.googleusercontent.com
    # (This is a common one for Google's own CLI tools)
    client_id = creds_data.get("client_id") 
    client_secret = creds_data.get("client_secret")
    
    # Fallback to a common one if missing (often required for refresh)
    if not client_id:
        # Note: This is an example placeholder. In a real scenario, we'd hope it's in the JSON.
        # However, for Antigravity, we might need to find where EXACTLY it's stored.
        pass

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
        logger.info("Refreshing access token...")
        logger.warning("If client_id/secret are missing, this may fail.")
        creds.refresh(GoogleRequest())
        
    return creds

def init_genai():
    try:
        creds = get_credentials()
        genai.configure(credentials=creds)
        logger.info("Gemini SDK configured successfully with OAuth session.")
    except Exception as e:
        logger.error(f"Failed to configure Gemini SDK: {e}")
        raise

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model_name = body.get("model", "gemini-3-flash-preview")
    # Map common OpenAI models to Gemini if needed
    if "gpt" in model_name:
        model_name = "gemini-3-flash-preview"
    
    messages = body.get("messages", [])
    
    # Convert OpenAI messages to Gemini history/prompt
    # This is a simplified version
    contents = []
    for m in messages:
        role = m["role"]
        content = m["content"]
        if role == "system":
            # Gemini's system instruction handling varies by SDK version
            # Here we just prepend it to the first user message or handle it separately
            continue
        
        g_role = "user" if role == "user" else "model"
        contents.append({"role": g_role, "parts": [content]})

    try:
        model = genai.GenerativeModel(model_name)
        # Note: Simple generation for now, could use start_chat for multi-turn if needed
        response = await asyncio.to_thread(model.generate_content, contents)
        
        # Format response as OpenAI completion
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
            {"id": "gemini-3-flash-preview", "object": "model", "created": 123456789, "owned_by": "google"},
            {"id": "gemini-3-pro-preview", "object": "model", "created": 123456789, "owned_by": "google"}
        ]
    }

if __name__ == "__main__":
    init_genai()
    print("\n" + "="*50)
    print("ANTIGRAVITY GEMINI BRIDGE RUNNING")
    print("Endpoint: http://localhost:18791/v1")
    print("From WSL, use your host IP (e.g. 172.x.x.1)")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=18791)
