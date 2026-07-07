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
st.title("📁 Folder Structure Generator")
st.write("Paste your folder structure or upload a text file. The app will create the folders and files, then provide a ZIP file for download.")


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
            lines.append(f"{prefix}📁 {name}/")
            lines.extend(structure_to_pretty_text(content, indent + 4).splitlines())
        else:
            lines.append(f"{prefix}📄 {name}")

    return "\n".join(lines)


# =========================================================
# UI
# =========================================================

# Simple example format
example_text = """my_project/
  src/
    main.py
    utils.py
  tests/
    test_main.py
  data/
    raw/
    processed/
  README.md
  requirements.txt"""

with st.expander("📖 How to write folder structure", expanded=True):
    st.markdown("""
    **Simple format:**
    - Use `/` at the end for folders
    - Use indentation (spaces or tabs) for nesting
    - Files don't need any special character
    
    **Example:**
    """)
    st.code(example_text, language="text")

# Input methods
st.subheader("📝 Enter your folder structure")

# Create two columns for input methods
col1, col2 = st.columns([3, 1])

with col1:
    # Text area for copy-paste
    user_input = st.text_area(
        "Paste your folder structure here",
        height=200,
        placeholder="my_project/\n  src/\n    main.py\n  README.md",
        help="Copy and paste your folder structure. Use / for folders and indentation for nesting."
    )

with col2:
    st.markdown("### OR")
    # File upload
    uploaded_file = st.file_uploader("Upload a .txt file", type=["txt"], label_visibility="collapsed")

# Process input
input_text = None

if uploaded_file is not None:
    try:
        input_text = uploaded_file.read().decode("utf-8")
        st.success("✅ File uploaded successfully!")
    except Exception as e:
        st.error(f"Error reading file: {e}")
elif user_input and user_input.strip():
    input_text = user_input
    st.info("📝 Using pasted content")

# Process and display results
if input_text:
    try:
        items = parse_structure_text(input_text)

        if not items:
            st.error("❌ The input is empty or does not contain a valid folder structure.")
        else:
            structure = build_structure(items)
            root_name = list(structure.keys())[0]

            st.subheader("📋 Parsed Structure Preview")
            st.code(structure_to_pretty_text(structure), language="text")

            st.write(f"**Root folder:** `{root_name}`")
            st.write(f"**Total items:** {len(items)}")

            if st.button("🚀 Generate ZIP File", type="primary"):
                with st.spinner("Creating folder structure..."):
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)

                        create_structure(temp_path, structure)

                        root_folder_path = temp_path / root_name
                        zip_bytes = add_folder_to_zip(root_folder_path)

                        st.success("✅ Folder structure created successfully!")
                        st.download_button(
                            label="📥 Download ZIP File",
                            data=zip_bytes,
                            file_name=f"{root_name}.zip",
                            mime="application/zip",
                            type="primary"
                        )

    except Exception as e:
        st.error(f"❌ An error occurred: {e}")
        st.exception(e)

# Footer
st.markdown("---")
st.caption("💡 Tip: You can either paste your structure or upload a .txt file. Both work!")
