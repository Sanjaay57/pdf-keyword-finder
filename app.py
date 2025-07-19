import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import pandas as pd
import io

# ----------------- Streamlit Page Setup ------------------
st.set_page_config(page_title="PDF Keyword Finder with OCR", layout="centered")
st.title("📄 PDF Keyword Finder (with OCR for Scanned PDFs)")
st.markdown("Upload a PDF and input keywords to search. This tool also works with scanned PDFs using OCR.")

# ----------------- File Upload ---------------------------
pdf_file = st.file_uploader("📁 Upload PDF File", type=["pdf"])

# ----------------- Keyword Input Options -----------------
keywords_input = st.radio("How will you enter keywords?", ["Type/Paste", "Upload .txt or .csv"])
search_terms = []

if keywords_input == "Type/Paste":
    text_input = st.text_area("Enter keywords (one per line):", height=150)
    if text_input:
        search_terms = [line.strip() for line in text_input.splitlines() if line.strip()]

elif keywords_input == "Upload .txt or .csv":
    keyword_file = st.file_uploader("Upload Keywords File", type=["txt", "csv"])
    if keyword_file:
        if keyword_file.name.endswith(".txt"):
            content = keyword_file.read().decode("utf-8")
            search_terms = [line.strip() for line in content.splitlines() if line.strip()]
        elif keyword_file.name.endswith(".csv"):
            df = pd.read_csv(keyword_file, header=None)
            search_terms = df.iloc[:, 0].dropna().astype(str).tolist()

# ----------------- Text Extraction with OCR Fallback -----------------
def extract_text(page):
    text = page.get_text().strip()
    if text:
        return text  # Use direct text if available

    # Fallback to OCR
    pix = page.get_pixmap(dpi=300)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    ocr_text = pytesseract.image_to_string(image)
    return ocr_text

# ----------------- Keyword Search Logic -----------------
def search_keywords(pdf_bytes, keywords):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    results = []

    for term in keywords:
        pages_found = []
        for i in range(len(doc)):
            text = extract_text(doc[i])
            if term.lower() in text.lower():
                pages_found.append(str(i + 1))
        results.append({
            "Keyword": term,
            "Found": "Yes" if pages_found else "No",
            "Pages Found On": ", ".join(pages_found)
        })
    return pd.DataFrame(results)

# ----------------- Search and Display Results -----------------
if st.button("🔍 Start Search"):
    if not pdf_file:
        st.warning("Please upload a PDF file.")
    elif not search_terms:
        st.warning("Please enter or upload keywords.")
    else:
        with st.spinner("Processing PDF... This may take a moment."):
            results_df = search_keywords(pdf_file.read(), search_terms)
            st.success("✅ Search Completed!")
            st.dataframe(results_df)

            # Download button
            csv_data = results_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv_data,
                file_name="keyword_search_results.csv",
                mime="text/csv"
            )
