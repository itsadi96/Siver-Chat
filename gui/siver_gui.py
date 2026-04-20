import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGraphicsOpacityEffect, QComboBox, QGraphicsBlurEffect
)
from PyQt6.QtCore import Qt, QEvent, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor, QMovie

from gui.components import (
    create_top_bar, create_left_panel, create_center_panel, create_bottom_nav
)
from core.llm import LLMHandler


# ---------------- Worker Thread ----------------
class LLMWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, llm_handler, prompt):
        super().__init__()
        self.llm_handler = llm_handler
        self.prompt = prompt

    def run(self):
        response = self.llm_handler.ask(self.prompt)
        self.finished.emit(response)


# ---------------- Main GUI ----------------
class SiverGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Siver AI Assistant")
        self.setGeometry(100, 100, 1400, 800)
        self.setStyleSheet("background-color: #0f111a; color: white;")

        # Core systems
        self.llm_handler = LLMHandler()
        self.command_history = []
        self.command_index = -1

        # Load previous chat history
        self.load_history()

        # Layout setup
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.setAcceptDrops(True)
        self.layout = QVBoxLayout(self.central)

        # ---------------- Top Bar ----------------
        self.top_bar = create_top_bar()
        self.layout.addWidget(self.top_bar)

        # Buttons
        self.toggle_history_btn = QPushButton("Toggle History")
        self.new_chat_btn = QPushButton("New Chat")
        self.clear_history_btn = QPushButton("Clear History")
        self.ingest_btn = QPushButton("Ingest Documents")
        self.ingest_btn.setStyleSheet("background-color: #2b2f40; color: orange;")

        # Model Selector Dropdown
        self.model_selector = QComboBox()
        self.model_selector.addItems(["Offline (DeepSeek)", "Gemini", "OpenRouter"])
        mode_map = {"offline": "Offline (DeepSeek)", "gemini": "Gemini", "openai": "OpenRouter"}
        self.model_selector.setCurrentText(
            mode_map.get(self.llm_handler.mode, "OpenRouter")
        )
        self.model_selector.setStyleSheet("""
            QComboBox {
                background-color: #1a1c24;
                color: white;
                border: 1px solid #2e74b5;
                padding: 4px;
                border-radius: 6px;
            }
            QComboBox:hover {
                border: 1px solid #00ffff;
            }
        """)

        self.top_bar.layout().addWidget(self.toggle_history_btn)
        self.top_bar.layout().addWidget(self.ingest_btn)
        self.top_bar.layout().addWidget(self.new_chat_btn)
        self.top_bar.layout().addWidget(self.clear_history_btn)
        self.top_bar.layout().addWidget(self.model_selector)

        self.toggle_history_btn.clicked.connect(self.toggle_history)
        self.ingest_btn.clicked.connect(self.ingest_documents)
        self.new_chat_btn.clicked.connect(self.new_chat)
        self.clear_history_btn.clicked.connect(self.clear_history)
        self.model_selector.currentTextChanged.connect(self.change_model_mode)

        # ---------------- Middle Layout ----------------
        self.middle_layout = QHBoxLayout()
        self.left_panel, self.history_list = create_left_panel()
        self.center_panel, self.chat_display, self.orb = create_center_panel()

        # --- Hide old orb or "Listening" label (removes black square / text)
        try:
            if hasattr(self, "orb") and self.orb:
                self.orb.hide()
            for child in self.center_panel.findChildren(QLabel):
                if "listening" in child.text().strip().lower():
                    child.hide()
        except Exception:
            pass

        # 🌌 Animated Background (aesthetic + seamless)
        self.bg_label = QLabel(self.center_panel)
        self.bg_label.setGeometry(0, 0, self.center_panel.width(), self.center_panel.height())
        self.bg_label.setScaledContents(True)
        self.bg_movie = QMovie("assets/listening.gif")
        self.bg_label.setMovie(self.bg_movie)
        self.bg_movie.start()

        # Soft opacity effect
        self.bg_opacity = QGraphicsOpacityEffect()
        self.bg_opacity.setOpacity(0.10)
        self.bg_label.setGraphicsEffect(self.bg_opacity)

        # Optional subtle blur (comment out if performance drops)
        try:
            blur = QGraphicsBlurEffect()
            blur.setBlurRadius(8)
            # NOTE: Qt supports one effect at a time — if you prefer blur over opacity, use this:
            # self.bg_label.setGraphicsEffect(blur)
        except Exception:
            pass

        # Ensure background stays behind chat
        self.bg_label.lower()
        self.chat_display.raise_()

        # Layout positioning
        self.middle_layout.addWidget(self.left_panel, 2)
        self.middle_layout.addWidget(self.center_panel, 8)
        self.layout.addLayout(self.middle_layout)
        
        # Hide history by default
        self.left_panel.hide()

        # ---------------- Bottom Nav ----------------
        self.bottom_nav, self.input_field, _, self.stop_btn, self.add_doc_btn = create_bottom_nav()
        self.layout.addWidget(self.bottom_nav)

        # ---------------- Event Binding ----------------
        self.add_doc_btn.clicked.connect(self.add_document)
        self.input_field.installEventFilter(self)
        self.bind_events()

        # Thread reference
        self.worker = None

        # Restore previous chat
        self.restore_chat_display()

    # ---------------- Resize Event ----------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "bg_label"):
            self.bg_label.setGeometry(0, 0, self.center_panel.width(), self.center_panel.height())

    # ---------------- Event Binding ----------------
    def bind_events(self):
        if hasattr(self.input_field, "returnPressed"):
            self.input_field.returnPressed.connect(self.process_input)

    # ---------------- Input Handling ----------------
    def process_input(self):
        user_text = (
            self.input_field.text().strip()
            if hasattr(self.input_field, "text")
            else self.input_field.toPlainText().strip()
        )
        if not user_text:
            return

        self.chat_display.append(f"<b style='color:#00ffff;'>You:</b> {user_text}")
        self.history_list.addItem(user_text)

        if hasattr(self.input_field, "clear"):
            self.input_field.clear()
        else:
            self.input_field.setPlainText("")

        self.command_history.append(user_text)
        self.command_index = len(self.command_history)

        self.chat_display.append("<i style='color:gray;'>Siver is thinking...</i>")
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

        self.worker = LLMWorker(self.llm_handler, user_text)
        self.worker.finished.connect(self.display_response)
        self.worker.start()

    # ---------------- Display Response ----------------
    def clean_response(self, text: str) -> str:
        import re
        text = text.strip()
        text = re.sub(r'^(okay,|hmm,|let\'s|note:)\s*', '', text, flags=re.IGNORECASE)
        return text

    def format_response(self, text: str) -> str:
        import markdown
        try:
            html = markdown.markdown(text, extensions=['extra'])
            # Add some basic inline styles to tables so QTextBrowser renders borders
            html = html.replace("<table>", "<table width='100%' border='1' cellspacing='0' cellpadding='5' style='margin: 10px 0; border-collapse: collapse;'>")
            html = html.replace("<th>", "<th style='background-color: #2b2f40; padding: 5px; text-align: left;'>")
            html = html.replace("<td>", "<td style='padding: 5px;'>")
            return f"<div style='color:orange;'>{html}</div>"
        except Exception as e:
            # Fallback in case of error
            lines = text.split("\n")
            return "".join(f"<p style='margin:2px 0; color:orange;'>{para}</p>" for para in lines)

    def display_response(self, response: str):
        clean_text = self.clean_response(response)
        formatted_text = self.format_response(clean_text)
        self.chat_display.append(f"<b style='color:orange;'>Siver:</b> {formatted_text}")
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
        self.save_history()

    # ---------------- Keyboard Handling ----------------
    def eventFilter(self, source, event):
        if source == self.input_field and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.process_input()
                return True
            elif event.key() == Qt.Key.Key_Up and self.command_history:
                self.command_index = max(0, self.command_index - 1)
                self.set_input_text(self.command_history[self.command_index])
                return True
            elif event.key() == Qt.Key.Key_Down and self.command_history:
                self.command_index = min(len(self.command_history) - 1, self.command_index + 1)
                self.set_input_text(self.command_history[self.command_index])
                return True
        return super().eventFilter(source, event)

    def set_input_text(self, text):
        if hasattr(self.input_field, "setText"):
            self.input_field.setText(text)
        else:
            self.input_field.setPlainText(text)

    # ---------------- Mode Switching ----------------
    def change_model_mode(self, text):
        if "Offline" in text:
            mode = "offline"
        elif "Gemini" in text:
            mode = "gemini"
        else:
            mode = "openai"
        result = self.llm_handler.change_mode(mode)
        self.chat_display.append(f"<i style='color:gray;'>{result}</i>")

        try:
            config = {}
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            config["mode"] = mode
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving mode: {e}")

    # ---------------- Add Document / Ingest / Clear History ----------------
    def add_document(self):
        import os
        import shutil
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Document", "", "Documents (*.pdf *.txt *.csv)"
        )

        if not file_path:
            return

        doc_dir = os.path.join(os.getcwd(), "documents")
        os.makedirs(doc_dir, exist_ok=True)

        try:
            filename = os.path.basename(file_path)
            destination = os.path.join(doc_dir, filename)
            shutil.copy2(file_path, destination)
            self.chat_display.append(f"<i style='color:#00ffff;'>📎 Added {filename} to documents. Auto-ingesting...</i>")
            
            # Trigger ingestion implicitly
            self.ingest_documents()
        except Exception as e:
            self.chat_display.append(f"<i style='color:red;'>⚠️ Failed to copy document: {e}</i>")
            self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def ingest_documents(self):
        if not getattr(self.llm_handler, 'rag', None):
            self.chat_display.append("<i style='color:orange;'>⚠️ RAG capabilities are not initialized. Check terminal for missing packages.</i>")
            return
            
        self.chat_display.append("<i style='color:gray;'>⏳ Ingesting documents... please wait.</i>")
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
        
        # Build index and report back
        try:
            # Force events to process so UI shows "Ingesting..." message before blocking
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            result = self.llm_handler.rag.build_index()
            self.chat_display.append(f"<i style='color:#00ffff;'>{result}</i>")
        except Exception as e:
            self.chat_display.append(f"<i style='color:red;'>⚠️ Ingestion failed: {e}</i>")
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def toggle_history(self):
        if self.left_panel.isVisible():
            self.left_panel.hide()
        else:
            self.left_panel.show()

    def new_chat(self):
        self.save_history()
        self.llm_handler.reset_history()
        self.chat_display.clear()
        self.history_list.clear()
        self.command_history = []
        self.command_index = -1
        self.chat_display.append("<i style='color:gray;'>New chat started.</i>")

    def clear_history(self):
        self.llm_handler.reset_history()
        self.chat_display.clear()
        self.history_list.clear()
        self.command_history = []
        self.command_index = -1
        try:
            with open("chat_history.json", "w", encoding="utf-8") as f:
                json.dump([], f)
            if os.path.exists("chat_sessions"):
                for file in os.listdir("chat_sessions"):
                    os.remove(os.path.join("chat_sessions", file))
            self.chat_display.append("<i style='color:gray;'>All history cleared.</i>")
        except Exception as e:
            print(f"Error clearing history: {e}")

    # ---------------- Persistent History ----------------
    def save_history(self):
        try:
            os.makedirs("chat_sessions", exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            session_path = os.path.join("chat_sessions", f"session_{timestamp}.json")
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(self.llm_handler.history, f, ensure_ascii=False, indent=2)
            with open("chat_history.json", "w", encoding="utf-8") as f:
                json.dump(self.llm_handler.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def load_history(self):
        try:
            with open("chat_history.json", "r", encoding="utf-8") as f:
                self.llm_handler.history = json.load(f)
        except FileNotFoundError:
            self.llm_handler.history = []

    def restore_chat_display(self):
        for msg in self.llm_handler.history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            color = "#00ffff" if role == "user" else "orange"
            
            if role != "user":
                content = self.format_response(self.clean_response(content))
                
            self.chat_display.append(f"<b style='color:{color};'>{role.capitalize()}:</b> {content}")
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    # ---------------- Drag and Drop Documents ----------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        import os
        import shutil

        doc_dir = os.path.join(os.getcwd(), "documents")
        os.makedirs(doc_dir, exist_ok=True)

        ingested_files = []
        urls = event.mimeData().urls()
        
        # Bring window to front to acknowledge drop
        self.activateWindow()

        for url in urls:
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                filename = os.path.basename(file_path)
                destination = os.path.join(doc_dir, filename)
                try:
                    shutil.copy2(file_path, destination)
                    ingested_files.append(filename)
                except Exception as e:
                    self.chat_display.append(f"<i style='color:red;'>⚠️ Failed to drop {filename}: {e}</i>")

        if ingested_files:
            files_str = ", ".join(ingested_files)
            self.chat_display.append(f"<i style='color:#00ffff;'>📥 Dropped {files_str}. Auto-ingesting...</i>")
            self.ingest_documents()
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
