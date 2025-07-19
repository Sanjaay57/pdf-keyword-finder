import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import pandas as pd
import io

st.set_page_config(page_title="Fast PDF Keyword Finder (OCR)", layout="centered")
st.title("⚡ Fast PDF Keyword Finder with OCR Fallback")

pdf_file = st.file_uploader("📄 Upload PDF", type=["pdf"])

# Keyword Input
search_terms = []
method = st.radio("How do you want to enter keywords?", ["Paste manually", "Upload .txt or .csv"])
if method == "Paste manually":
    input_text = st.text_area("Enter one keyword per line")
    if input_text:
        search_terms = [line.strip() for line in input_text.splitlines() if line.strip()]
else:
    keyword_file = st.file_uploader("Upload .txt or .csv file", type=["txt", "csv"])
    if keyword_file:
        if keyword_file.name.endswith(".txt"):
            content = keyword_file.read().decode("utf-8")
            search_terms = [line.strip() for line in content.splitlines() if line.strip()]
        else:
            df = pd.read_csv(keyword_file, header=None)
            search_terms = df.iloc[:, 0].dropna().astype(str).tolist()

# Extract all text from PDF once
@st.cache_data(show_spinner=False)
def extract_all_text(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_texts = []
    for page in doc:
        text = page.get_text().strip()
        if not text:
            # OCR fallback
            pix = page.get_pixmap(dpi=200)  # reduced DPI for speed
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(image)
        page_texts.append(text)
    return page_texts

def find_keywords_in_texts(page_texts, keywords):
    results = []
    for kw in keywords:
        found_pages = [str(i + 1) for i, text in enumerate(page_texts) if kw.lower() in text.lower()]
        results.append({
            "Keyword": kw,
            "Found": "Yes" if found_pages else "No",
            "Pages": ", ".join(found_pages)
        })
    return pd.DataFrame(results)

# Trigger search
if st.button("🔍 Search Keywords"):
    if not pdf_file:
        st.warning("Please upload a PDF file.")
    elif not search_terms:
        st.warning("Please enter or upload keywords.")
    else:
        with st.spinner("Extracting text and scanning PDF..."):
            all_texts = extract_all_text(pdf_file.read())
            result_df = find_keywords_in_texts(all_texts, search_terms)
            st.success("✅ Done!")
            st.dataframe(result_df)

            csv = result_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Results as CSV", csv, "results.csv", "text/csv")
