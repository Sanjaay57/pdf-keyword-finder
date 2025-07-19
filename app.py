import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import pandas as pd
import io
import re

st.set_page_config(page_title="Smart PDF Table Finder", layout="centered")
st.title("📄 Auto Table Extractor with Search")

pdf_file = st.file_uploader("📁 Upload PDF File", type=["pdf"])

search_terms = []
input_method = st.radio("Input Search Terms", ["Paste", "Upload .txt/.csv"])

if input_method == "Paste":
    text_input = st.text_area("Enter search terms:", height=150)
    if text_input:
        search_terms = [line.strip() for line in text_input.splitlines() if line.strip()]
else:
    file = st.file_uploader("Upload keyword file", type=["txt", "csv"])
    if file:
        if file.name.endswith(".txt"):
            content = file.read().decode("utf-8")
            search_terms = [line.strip() for line in content.splitlines() if line.strip()]
        else:
            df = pd.read_csv(file, header=None)
            search_terms = df.iloc[:, 0].dropna().astype(str).tolist()

@st.cache_data(show_spinner=False)
def extract_text_lines(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_lines = []
    for page in doc:
        text = page.get_text()
        if not text.strip():
            # OCR fallback
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img)
        page_lines = [line.strip() for line in text.splitlines() if line.strip()]
        all_lines.extend(page_lines)
    return all_lines

def is_likely_header(line):
    return any(keyword in line.lower() for keyword in ["application", "seat", "category", "merit", "remarks"]) and len(re.split(r'\s{2,}|\|', line)) >= 3

def extract_table(lines):
    header = None
    rows = []
    col_count = 0

    for i, line in enumerate(lines):
        if is_likely_header(line):
            header_parts = re.split(r'\s{2,}|\|', line)
            if len(header_parts) >= 3:
                header = [h.strip() for h in header_parts]
                col_count = len(header)
                continue

        if header:
            row_parts = re.split(r'\s{2,}|\|', line)
            if len(row_parts) == col_count:
                rows.append([cell.strip() for cell in row_parts])

    return header, rows

def search_table_rows(rows, search_terms):
    matched = []
    for row in rows:
        row_str = ' '.join(row).lower()
        for term in search_terms:
            if term.lower() in row_str:
                matched.append(row)
                break
    return matched

if st.button("🔍 Start Search"):
    if not pdf_file:
        st.warning("Upload a PDF first.")
    elif not search_terms:
        st.warning("Please enter search terms.")
    else:
        with st.spinner("Extracting and analyzing..."):
            lines = extract_text_lines(pdf_file.read())
            header, rows = extract_table(lines)
            if header:
                matched_rows = search_table_rows(rows, search_terms)
                if matched_rows:
                    df = pd.DataFrame(matched_rows, columns=header[:len(matched_rows[0])])
                    st.success("✅ Matches found:")
                    st.dataframe(df)

                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Download CSV", data=csv, file_name="results.csv")
                else:
                    st.info("No matches found.")
            else:
                st.error("No table headers found. Please check the PDF format.")
