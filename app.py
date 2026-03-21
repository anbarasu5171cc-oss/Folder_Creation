import re
import zipfile
import tempfile
from pathlib import Path
from io import BytesIO

import streamlit as st


# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(page_title="Folder Structure Generator", layout="centered")
st.title("Folder Structure Generator")
st.write("Upload a text file containing a folder structure. The app will create the folders and files, then provide a ZIP file for download.")


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def clean_line(line: str) -> str:
    """
    Remove tree symbols like:
    ├──  └──  │
    """
    line = line.rstrip("\n").rstrip("\r")
    line = line.replace("\t", "    ")
    line = re.sub(r'^[\s│]*[├└]──\s*', '', line)
    line = line.replace("│", "")
    return line.rstrip()


def get_depth(raw_line: str) -> int:
    """
    Estimate nesting depth using indentation.
    Every 4 spaces is treated as one level.
    """
    line = raw_line.rstrip("\n").rstrip("\r").replace("\t", "    ")
    indent_part = re.match(r'^([\s│]*)', line)
    indent = indent_part.group(1) if indent_part else ""
    indent = indent.replace("│", " ")
    depth = len(indent) // 4
    return depth


def is_folder(name: str) -> bool:
    """
    A name ending with '/' is treated as a folder.
    """
    return name.endswith("/")


def normalize_name(name: str) -> str:
    """
    Remove ending slash and extra spaces.
    """
    return name.rstrip("/").strip()


def parse_structure_text(text: str):
    """
    Parse folder structure text into:
    [(depth, name, type), ...]
    """
    items = []
    lines = text.splitlines()

    useful_lines = [line for line in lines if line.strip()]

    for raw_line in useful_lines:
        depth = get_depth(raw_line)
        name = clean_line(raw_line).strip()

        if not name:
            continue

        item_type = "folder" if is_folder(name) else "file"
        items.append((depth, normalize_name(name), item_type))

    return items


def build_structure(items, default_root_name="generated_project"):
    """
    Build nested dictionary from parsed items.
    """
    if not items:
        return {default_root_name: {}}

    first_depth, first_name, first_type = items[0]

    if first_depth == 0 and first_type == "folder":
        root_name = first_name
        start_index = 1
    else:
        root_name = default_root_name
        start_index = 0

    root = {}
    structure = {root_name: root}

    stack = [(-1, root)]

    for depth, name, item_type in items[start_index:]:
        while stack and stack[-1][0] >= depth:
            stack.pop()

        parent_dict = stack[-1][1]

        if item_type == "folder":
            parent_dict[name] = {}
            stack.append((depth, parent_dict[name]))
        else:
            parent_dict[name] = None

    return structure


def create_structure(base_path: Path, structure: dict):
    """
    Create folders and files from structure dictionary.
    """
    for name, content in structure.items():
        current_path = base_path / name

        if isinstance(content, dict):
            current_path.mkdir(parents=True, exist_ok=True)
            create_structure(current_path, content)
        else:
            current_path.parent.mkdir(parents=True, exist_ok=True)
            current_path.touch(exist_ok=True)


def add_folder_to_zip(folder_path: Path) -> bytes:
    """
    Create ZIP in memory and return bytes.
    """
    memory_file = BytesIO()

    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in folder_path.rglob("*"):
            zf.write(file_path, arcname=file_path.relative_to(folder_path.parent))

    memory_file.seek(0)
    return memory_file.getvalue()


def structure_to_pretty_text(structure: dict, indent: int = 0) -> str:
    """
    Convert structure dict into a readable preview.
    """
    lines = []

    for name, content in structure.items():
        prefix = " " * indent
        if isinstance(content, dict):
            lines.append(f"{prefix}[Folder] {name}/")
            lines.extend(structure_to_pretty_text(content, indent + 4).splitlines())
        else:
            lines.append(f"{prefix}[File] {name}")

    return "\n".join(lines)


# =========================================================
# UI
# =========================================================
uploaded_file = st.file_uploader("Upload a text file", type=["txt"])

example_text = """AI_Traffic_Project/
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
"""

with st.expander("Example folder structure format"):
    st.code(example_text, language="text")

if uploaded_file is not None:
    try:
        file_text = uploaded_file.read().decode("utf-8")
        items = parse_structure_text(file_text)

        if not items:
            st.error("The uploaded file is empty or does not contain a valid folder structure.")
        else:
            structure = build_structure(items)
            root_name = list(structure.keys())[0]

            st.subheader("Parsed Structure Preview")
            st.code(structure_to_pretty_text(structure), language="text")

            if st.button("Create ZIP File"):
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)

                    create_structure(temp_path, structure)

                    root_folder_path = temp_path / root_name
                    zip_bytes = add_folder_to_zip(root_folder_path)

                    st.success("The folder structure was created successfully.")
                    st.download_button(
                        label="Download ZIP File",
                        data=zip_bytes,
                        file_name=f"{root_name}.zip",
                        mime="application/zip"
                    )

    except Exception as e:
        st.error(f"An error occurred: {e}")