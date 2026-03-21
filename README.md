# 📁 Folder Structure Generator

A simple and powerful Streamlit web app that converts a text-based folder structure into real folders and files — and lets you download everything as a ZIP file.

---

## 🚀 Features

- 📂 Upload a `.txt` file containing folder structure
- ⚡ Automatically creates folders and files
- 📦 Generates a downloadable ZIP file
- 👀 Preview structure before creation
- 🌐 Clean and simple UI using Streamlit

---

## 🧠 How It Works

1. User uploads a text file with folder structure
2. App parses the structure (like tree format)
3. Creates folders and files dynamically
4. Compresses everything into a ZIP
5. Provides download button

---

## 📄 Example Input

```text
AI_Traffic_Project/
├── backend/
│   ├── app.py
│   ├── model.py
│   └── utils.py
├── frontend/
├── data/
│   ├── raw/
│   └── processed/
├── models/
├── static/
└── README.md