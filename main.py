import torch
import faiss
import sys
import subprocess
import time
import os
import json
import requests
import psutil
from PyQt6.QtWidgets import QApplication
from gui.siver_gui import SiverGUI
from core.llm import LLMHandler


def get_current_mode():
    """Read the current mode from config.json"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("mode", "openai")
    except Exception as e:
        print(f"Error reading config.json: {e}")
    return "openai"


def ensure_ollama_running():
    """Check if Ollama is running, if not start it in the background."""
    for proc in psutil.process_iter(attrs=['pid', 'name']):
        if "ollama" in proc.info['name'].lower():
            print("✅ Ollama is already running")
            return
    
    print("🚀 Starting Ollama server...")
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Wait until Ollama API responds
    print("⏳ Waiting for Ollama to be ready...")
    for _ in range(30):  # try for ~30 seconds
        try:
            r = requests.head("http://127.0.0.1:11434/")
            if r.status_code == 200:
                print("✅ Ollama is ready!")
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    print("⚠️ Warning: Ollama did not respond in time.")


def main():
    # Only start Ollama if mode is offline
    mode = get_current_mode()
    print(f"🔧 Current mode: {mode}")

    if mode == "offline":
        ensure_ollama_running()
    else:
        print(f"☁️ Using {mode} mode — skipping Ollama startup")

    # Initialize application
    app = QApplication(sys.argv)

    # Initialize the Siver GUI
    window = SiverGUI()
    window.show()

    # Start the application loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
