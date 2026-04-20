# core/llm.py
import requests
import os
from openai import OpenAI
import json

# Load .env so OPENROUTER_API_KEY is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import google.generativeai as genai


class LLMHandler:
    def __init__(self, config_path="config.json"):
        """Initialize model and load configuration"""

        # Load mode and API keys from config.json (create default if missing)
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {
                "mode": "openai",
                "ollama_model": "deepseek-r1:8b",
                "gemini_api_key": ""
            }

        # Configuration values
        self.mode = config.get("mode", "openai")
        self.gemini_api_key = config.get("gemini_api_key", "")
        self.offline_url = "http://127.0.0.1:11434/api/generate"
        self.model_name = config.get("ollama_model", "deepseek-r1:8b")

        # OpenRouter configuration (from .env or config.json fallback)
        self.openrouter_api_key = (
            os.getenv("OPENROUTER_API_KEY", "")
            or config.get("openrouter_api_key", "")
        )
        self.openrouter_base_url = (
            os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            or config.get("openrouter_base_url", "https://openrouter.ai/api/v1")
        )
        self.openrouter_model = (
            os.getenv("OPENROUTER_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1:free")
            or config.get("openrouter_model", "nvidia/llama-3.3-nemotron-super-49b-v1:free")
        )

        # Chat history memory
        self.history = []  # list of {"role": "user"/"assistant", "content": str}

        # Configure Gemini if applicable
        if self.mode == "gemini" and self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)

        try:
            from core.rag import RAGManager
            self.rag = RAGManager()
        except ImportError as e:
            self.rag = None
            print(f"RAG dependencies missing: {e}")

    # ------------------------------------------------------------------
    def ask(self, user_input: str) -> str:
        """Send a user query and return AI response"""
        self.history.append({"role": "user", "content": user_input})
        
        context_str = None
        sources = []
        if getattr(self, "rag", None):
            context_str, sources, evidence = self.rag.search_context(user_input)

        if context_str:
            prompt_injection = (
                "You are an expert AI assistant answering questions.\n"
                "Use the provided context if relevant.\n"
                "Be concise, structured, and cite your sources using the bracketed numbers (e.g., [1], [2]).\n\n"
                f"Context:\n{context_str}\n\n"
                f"Question: {user_input}\n\n"
                "Answer:"
            )
            # Replace the user's latest message with the augmented prompt in the backend conversation
            conversation = "\n".join(
                f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.history[:-1]
            )
            if self.history[:-1]:
                conversation += "\n"
            conversation += f"User: {prompt_injection}"
        else:
            conversation = "\n".join(
                f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.history
            )

        # Route to correct backend
        if self.mode == "offline":
            response = self.ask_offline(conversation)
        elif self.mode == "gemini":
            response = self.ask_gemini(conversation)
        elif self.mode == "openai":
            response = self.ask_openai(conversation)
        else:
            response = f"⚠️ Unsupported mode: {self.mode}"

        if sources:
            source_names = ", ".join(sources)
            response += f"\n\n**Sources Cited:** {source_names}"

        # Save assistant reply
        self.history.append({"role": "assistant", "content": response})
        return response

    # ------------------------------------------------------------------
    def ask_offline(self, prompt: str) -> str:
        """Send prompt to local Ollama/DeepSeek model"""
        try:
            response = requests.post(
                self.offline_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=300,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                return f"⚠️ Offline Error: {response.status_code}: {response.text}"
        except Exception as e:
            return f"⚠️ Offline Error: {str(e)}"

    # ------------------------------------------------------------------
    def ask_gemini(self, prompt: str) -> str:
        """Send prompt to Gemini via API key (auto-detect working model)"""
        if not self.gemini_api_key:
            return "⚠️ Gemini API key missing in config.json or llm.py."

        try:
            genai.configure(api_key=self.gemini_api_key)

            # Try models in order of availability
            possible_models = [
                "models/gemini-1.5-flash",
                "models/gemini-1.5-pro",
                "gemini-pro",   # fallback for older SDKs
                "gemini-1.0-pro"
            ]

            last_error = None

            for model_name in possible_models:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    if hasattr(response, "text") and response.text:
                        return response.text.strip()
                    elif hasattr(response, "candidates") and response.candidates:
                        return response.candidates[0].content.parts[0].text.strip()
                except Exception as e:
                    last_error = str(e)
                    continue

            return f"⚠️ Gemini Error: All model versions failed. Last error: {last_error}"

        except Exception as e:
            return f"⚠️ Gemini Error: {str(e)}"

    # ------------------------------------------------------------------
    def ask_openai(self, prompt: str) -> str:
        """Send prompt to OpenRouter via openai SDK"""
        if not self.openrouter_api_key:
            return "⚠️ OpenRouter API key missing. Set OPENROUTER_API_KEY in .env file."

        try:
            client = OpenAI(
                base_url=self.openrouter_base_url,
                api_key=self.openrouter_api_key,
            )

            response = client.chat.completions.create(
                model=self.openrouter_model,
                messages=[
                    {"role": "system", "content": "You are Siver, a helpful AI assistant. Be concise and helpful."},
                    {"role": "user", "content": prompt},
                ],
                extra_body={"reasoning": {"enabled": True}},
            )

            msg = response.choices[0].message
            return msg.content.strip() if msg.content else "⚠️ OpenRouter returned empty response."

        except Exception as e:
            return f"⚠️ OpenRouter Error: {str(e)}"

    # ------------------------------------------------------------------
    def reset_history(self):
        """Clear all chat history"""
        self.history = []

    # ------------------------------------------------------------------
    def change_mode(self, new_mode: str):
        """Switch between offline, gemini, and openai dynamically"""
        if new_mode not in ["offline", "gemini", "openai"]:
            return f"⚠️ Invalid mode: {new_mode}"

        self.mode = new_mode

        if new_mode == "gemini" and self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
            except Exception as e:
                return f"⚠️ Failed to initialize Gemini: {e}"

        if new_mode == "openai" and not self.openrouter_api_key:
            return "⚠️ Mode set to OpenRouter but API key is missing. Add OPENROUTER_API_KEY to .env"

        return f"✅ Mode switched to {self.mode}"

    # ------------------------------------------------------------------
    def list_gemini_models(self) -> str:
        """List all available Gemini models for debugging"""
        try:
            genai.configure(api_key=self.gemini_api_key)
            models = genai.list_models()
            available = [m.name for m in models if "generateContent" in m.supported_generation_methods]
            return "🧠 Available Gemini models:\n" + "\n".join(available)
        except Exception as e:
            return f"⚠️ Could not list models: {e}"
