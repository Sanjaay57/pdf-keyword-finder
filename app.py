import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import pandas as pd
import io

st.set_page_config(page_title="PDF Table Extractor by Keyword", layout="centered")
st.title("📄 PDF Table Extractor with OCR")
st.markdown("Upload a scanned or text-based PDF and search by keyword (e.g., Application No). Returns full matching line.")

# File upload
pdf_file = st.file_uploader("📁 Upload PDF", type=["pdf"])

# Keyword input
search_terms = []
input_method = st.radio("How to provide keywords?", ["Paste here", "Upload .txt or .csv"])

if input_method == "Paste here":
    kw_text = st.text_area("Enter keywords (one per line)")
    if kw_text:
        search_terms = [line.strip() for line in kw_text.splitlines() if line.strip()]
else:
    kw_file = st.file_uploader("Upload keyword file", type=["txt", "csv"])
    if kw_file:
        if kw_file.name.endswith(".txt"):
            search_terms = kw_file.read().decode("utf-8").splitlines()
            search_terms = [kw.strip() for kw in search_terms if kw.strip()]
        else:
            df = pd.read_csv(kw_file, header=None)
            search_terms = df.iloc[:, 0].dropna().astype(str).tolist()

# Extract lines (text or OCR)
@st.cache_data(show_spinner=False)
def extract_pdf_lines(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    all_lines = []
    for page in doc:
        text = page.get_text()
        if not text.strip():
            # Fallback to OCR
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img)
        page_lines = text.splitlines()
        all_lines.extend([line.strip() for line in page_lines if line.strip()])
    return all_lines

# Match each keyword to full line
def match_keywords_to_lines(lines, keywords):
    results = []
    for kw in keywords:
        matched_line = next((line for line in lines if kw.lower() in line.lower()), None)
        results.append({
            "Keyword": kw,
            "Found": "Yes" if matched_line else "No",
            "Full Line (if found)": matched_line or ""
        })
    return pd.DataFrame(results)

# Main action
if st.button("🔍 Find Matches"):
    if not pdf_file:
        st.warning("Please upload a PDF file.")
    elif not search_terms:
        st.warning("Please enter or upload keywords.")
    else:
        with st.spinner("Extracting lines and searching..."):
            lines = extract_pdf_lines(pdf_file.read())
            df = match_keywords_to_lines(lines, search_terms)
            st.success("✅ Done!")
            st.dataframe(df)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download as CSV", data=csv, file_name="matched_results.csv", mime="text/csv")
