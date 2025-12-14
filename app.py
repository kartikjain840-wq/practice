import streamlit as st
import pandas as pd
import requests
import re
import json
import fitz
from docx import Document
from bs4 import BeautifulSoup
from io import BytesIO
from openai import OpenAI

# =============================
# CONFIG
# =============================
st.set_page_config(
    page_title="Faber Infinite Consulting | AI Knowledge OS",
    layout="wide"
)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# =============================
# HEADER
# =============================
col1, col2 = st.columns([1, 5])
with col1:
    st.image("faber_logo.png", width=120)
with col2:
    st.markdown("## **Faber Infinite Consulting – AI Project Intelligence Dashboard**")
    st.caption("LLM-powered extraction from Google Drive files")

st.divider()

# =============================
# INPUT
# =============================
drive_link = st.text_input(
    "🔗 Paste Google Drive public folder link",
    placeholder="https://drive.google.com/drive/folders/XXXXXXXX"
)

# =============================
# HELPERS
# =============================
def extract_folder_id(url):
    match = re.search(r"folders/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None

def list_drive_files(folder_id):
    html = requests.get(
        f"https://drive.google.com/drive/folders/{folder_id}"
    ).text
    soup = BeautifulSoup(html, "html.parser")

    files = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if "/file/d/" in href:
            fid = href.split("/file/d/")[1].split("/")[0]
            files.append((a.text.strip(), fid))
    return list(set(files))

def download_file(file_id):
    return requests.get(f"https://drive.google.com/uc?id={file_id}").content

def read_text(name, content):
    if name.lower().endswith(".pdf"):
        doc = fitz.open(stream=content, filetype="pdf")
        return " ".join(p.get_text() for p in doc)

    if name.lower().endswith(".docx"):
        doc = Document(BytesIO(content))
        return " ".join(p.text for p in doc.paragraphs)

    if name.lower().endswith(".txt"):
        return content.decode(errors="ignore")

    return ""

# =============================
# AI EXTRACTION
# =============================
def ai_extract(text):
    prompt = f"""
You are a management consulting analyst.

From the text below, extract ONLY the following fields.
Return STRICT JSON.

Fields:
- industry
- location
- objectives
- results_delivered

Rules:
- Be concise
- If not clear, infer professionally
- Do not add extra text

TEXT:
{text[:6000]}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {
            "industry": "Not specified",
            "location": "Not specified",
            "objectives": "Not specified",
            "results_delivered": "Not specified"
        }

# =============================
# PROCESS
# =============================
if drive_link:
    folder_id = extract_folder_id(drive_link)

    if not folder_id:
        st.error("Invalid Google Drive folder link")
    else:
        with st.spinner("AI is analyzing your consulting files..."):
            rows = []

            for name, fid in list_drive_files(folder_id):
                content = download_file(fid)
                text = read_text(name, content)

                if text.strip():
                    result = ai_extract(text)
                    rows.append({
                        "Industry": result["industry"],
                        "Location": result["location"],
                        "Objectives": result["objectives"],
                        "Results Delivered": result["results_delivered"]
                    })

        if rows:
            df = pd.DataFrame(rows)
            st.subheader("📊 AI-Extracted Project Summary")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No readable files found")

# =============================
# FOOTER
# =============================
st.divider()
st.caption("© Faber Infinite Consulting | AI Knowledge OS")
