import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import pandas as pd
import io
import re

st.set_page_config(page_title="Structured Table Extractor", layout="centered")
st.title("📄 PDF Table Extractor (Search + Structured Output)")

# Upload PDF
pdf_file = st.file_uploader("📁 Upload PDF File", type=["pdf"])

# Upload or Paste Keywords
search_terms = []
input_method = st.radio("Keyword Input Method", ["Paste manually", "Upload .txt or .csv"])

if input_method == "Paste manually":
    text_input = st.text_area("Enter keywords (Application No or Seat No):", height=150)
    if text_input:
        search_terms = [line.strip() for line in text_input.splitlines() if line.strip()]
else:
    kw_file = st.file_uploader("Upload keyword file", type=["txt", "csv"])
    if kw_file:
        if kw_file.name.endswith(".txt"):
            content = kw_file.read().decode("utf-8")
            search_terms = [line.strip() for line in content.splitlines() if line.strip()]
        else:
            df = pd.read_csv(kw_file, header=None)
            search_terms = df.iloc[:, 0].dropna().astype(str).tolist()

# Extract lines from PDF (OCR if needed)
@st.cache_data(show_spinner=False)
def extract_lines(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_lines = []
    for page in doc:
        text = page.get_text()
        if not text.strip():
            # OCR fallback
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img)
        page_lines = text.splitlines()
        all_lines.extend([line.strip() for line in page_lines if line.strip()])
    return all_lines

# Parse structured row from matched line
def parse_row(line):
    parts = [p.strip() for p in re.split(r'\s*\|\s*', line)]
    return {
        "Common Merit No": parts[0] if len(parts) > 0 else "",
        "Application No": parts[1] if len(parts) > 1 else "",
        "Seat No": parts[2] if len(parts) > 2 else "",
        "Category": parts[3] if len(parts) > 3 else "",
        "Remarks": parts[4] if len(parts) > 4 else "",
        "Raw Line": line
    }

# Search and extract rows
def match_and_parse(lines, keywords):
    results = []
    for keyword in keywords:
        matched_line = next((line for line in lines if keyword.lower() in line.lower()), None)
        if matched_line:
            parsed = parse_row(matched_line)
            parsed["Keyword"] = keyword
            parsed["Found"] = "Yes"
        else:
            parsed = {
                "Keyword": keyword,
                "Found": "No",
                "Common Merit No": "",
                "Application No": "",
                "Seat No": "",
                "Category": "",
                "Remarks": "",
                "Raw Line": ""
            }
        results.append(parsed)
    return pd.DataFrame(results)

# Action
if st.button("🔍 Search Now"):
    if not pdf_file:
        st.warning("Please upload a PDF.")
    elif not search_terms:
        st.warning("Please provide keywords.")
    else:
        with st.spinner("Processing PDF..."):
            all_lines = extract_lines(pdf_file.read())
            df = match_and_parse(all_lines, search_terms)
            st.success("✅ Done!")
            st.dataframe(df)

            # Download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download CSV", data=csv, file_name="matched_results.csv", mime="text/csv")
