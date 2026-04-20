from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QFrame, QListWidget,
    QTextBrowser, QPushButton, QLineEdit
)
from PyQt6.QtGui import QPixmap, QMovie
from PyQt6.QtCore import Qt
import os

def create_top_bar():
    bar = QFrame()
    bar.setFixedHeight(60)
    bar.setStyleSheet("background-color: #1f2233;")
    
    layout = QHBoxLayout(bar)
    label = QLabel("Siver AI Dashboard")
    label.setStyleSheet("font-size: 20px; color: cyan;")
    layout.addWidget(label)
    layout.addStretch()

    # Profile picture (ensure path is correct)
    profile = QLabel()
    pixmap = QPixmap("assets/avatar.png")  # Update path to match location
    profile.setPixmap(pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    layout.addWidget(profile)

    return bar

def create_left_panel():
    panel = QFrame()
    panel.setStyleSheet("background-color: #181b2a; border-radius: 10px;")
    layout = QVBoxLayout(panel)

    title = QLabel("Search History")
    title.setStyleSheet("font-size: 16px; color: #00ffff;")
    layout.addWidget(title)

    history_list = QListWidget()
    for item in ["Weather", "Restaurants near me", "Latest tech news"]:
        history_list.addItem(item)
    layout.addWidget(history_list)

    return panel, history_list

def create_center_panel():
    panel = QFrame()
    panel.setStyleSheet("background-color: #1d1f2f; border-radius: 20px;")
    layout = QVBoxLayout(panel)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # 🔁 Animated orb (listening.gif)
    orb = QLabel()
    orb.setFixedSize(120, 120)
    orb.setStyleSheet("margin: 20px;")
    gif_path = os.path.join("assets", "listening.gif")

    if os.path.exists(gif_path):
        movie = QMovie(gif_path)
        orb.setMovie(movie)
        movie.start()
    else:
        orb.setText("🔊")  # Fallback if GIF isn't found

    layout.addWidget(orb, alignment=Qt.AlignmentFlag.AlignCenter)

    text = QLabel("Listening...")
    text.setStyleSheet("font-size: 18px; color: #00ffff;")
    layout.addWidget(text, alignment=Qt.AlignmentFlag.AlignCenter)

    chat_display = QTextBrowser()
    chat_display.setStyleSheet("background-color: transparent; color: white;")
    layout.addWidget(chat_display)

    return panel, chat_display, orb

def create_right_panel():
    panel = QFrame()
    panel.setStyleSheet("background-color: #181b2a; border-radius: 10px;")
    layout = QVBoxLayout(panel)

    title = QLabel("Search Results")
    title.setStyleSheet("font-size: 16px; color: #00ffff;")
    layout.addWidget(title)

    results_view = QTextBrowser()
    results_view.setStyleSheet("background: transparent; color: white;")
    results_view.setText("")
    layout.addWidget(results_view)

    return panel, results_view

def create_bottom_nav():
    nav = QFrame()
    nav.setFixedHeight(60)
    nav.setStyleSheet("background-color: #1f2233;")
    
    layout = QHBoxLayout(nav)
    home_btn = QPushButton("Home")
    mic_btn = QPushButton("🎤")
    stop_btn = QPushButton("❌")
    add_doc_btn = QPushButton("📎")
    input_field = QLineEdit()
    input_field.setPlaceholderText("Type a command...")

    for btn in [home_btn, add_doc_btn, mic_btn, stop_btn]:
        btn.setStyleSheet("background-color: #2b2f40; color: white; border-radius: 10px;")
        layout.addWidget(btn)

    layout.addWidget(input_field)

    return nav, input_field, mic_btn, stop_btn, add_doc_btn
