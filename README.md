# Siver AI Assistant

Siver AI Assistant is a powerful, locally-hosted desktop graphical interface that allows you to chat with offline AI models (via Ollama) and use RAG (Retrieval-Augmented Generation) to ingest and chat with massive PDF, CSV, and text files. It also features seamless cloud model integrations for Gemini and OpenRouter.

## Prerequisites

1. **Python 3.10+**: Ensure Python is installed on your system.
2. **Ollama**: Required only if you intend to use local, offline models (such as `qwen2.5:7b` or `deepseek-r1:8b`). Download and install it from [ollama.com](https://ollama.com/).

## Installation

1. **Clone or Extract the Project**
   Extract the zip file to your desired folder.

2. **Open a Terminal**
   Open your Command Prompt or PowerShell and navigate to the project directory:
   ```cmd
   cd path\to\Siver1
   ```

3. **Set Up a Virtual Environment (Recommended)**
   Keep your system Python clean by creating a virtual environment.
   ```cmd
   python -m venv siver-venv
   ```
   **Activate it:**
   - On Windows: `.\siver-venv\Scripts\activate`
   - On Mac/Linux: `source siver-venv/bin/activate`

4. **Install Dependencies**
   ```cmd
   pip install -r requirements.txt
   ```

## Configuration

Before starting, open the project folder and modify the default configuration templates if you plan to use cloud providers.
*   **`.env`**: Enter your API key here. By default, it looks for your `OPENROUTER_API_KEY`.
*   **`config.json`**: This file acts as your main toggle. You can set the target local `ollama_model` here, as well as your `gemini_api_key`.

## Usage

1. Start the application:
   ```cmd
   python main.py
   ```
   *(If you are set to `offline` mode in `config.json`, the app will automatically boot up your local Ollama server in the background!)*

2. **Ingesting Documents**: Drag and drop PDF, TXT, or CSV files directly into the GUI window, or click the paperclip icon in the bottom right context menu. Click the **"Ingest Documents"** button at the top to process the files into the AI's local knowledge base.
3. Switch AI models (Offline, Gemini, or OpenRouter) easily via the top right dropdown menu!
