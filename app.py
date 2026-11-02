
import streamlit as st
import io
import json
import re
import os
from groq import Groq
from pypdf import PdfReader
from docx import Document

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="Resume ATS Analyzer",
    page_icon="📄",
    layout="wide"
)

# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>
.main {
    background-color: #f8fafc;
}
h1 {
    color: #1e293b;
}
.stButton>button {
    background-color: #2563eb;
    color: white;
    border-radius: 8px;
    height: 45px;
    font-weight: bold;
}
.stDownloadButton>button {
    background-color: #059669;
    color: white;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- GROQ CLIENT ----------------

def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

    if not api_key:
        raise ValueError(
            "Groq API key is missing. Add GROQ_API_KEY to Streamlit Secrets."
        )

    return Groq(api_key=api_key)


# ---------------- RESUME TEXT EXTRACTION ----------------

def extract_resume_text(uploaded_file):

    file_name = uploaded_file.name.lower()

    if file_name.endswith(".pdf"):
        pdf = PdfReader(io.BytesIO(uploaded_file.getvalue()))

        text = ""

        for page in pdf.pages:
            text += page.extract_text() or ""

        return text

    elif file_name.endswith(".docx"):
        document = Document(io.BytesIO(uploaded_file.getvalue()))

        text = "\n".join(
            paragraph.text for paragraph in document.paragraphs
        )

        for table in document.tables:
            for row in table.rows:
                text += "\n" + " | ".join(
                    cell.text for cell in row.cells
                )

        return text

    else:
        raise ValueError("Only PDF and DOCX files are supported.")


# ---------------- AI ANALYSIS ----------------

def analyze_resume(resume_text, job_description):

    client = get_groq_client()

    prompt = f"""
You are an expert ATS resume analyzer and professional career advisor.

Analyze the following resume against the job description.

RESUME:
{resume_text[:18000]}

JOB DESCRIPTION:
{job_description[:8000] if job_description.strip() else "No job description provided."}

Provide an honest and detailed analysis.

Return ONLY valid JSON in this exact structure:

{{
    "ats_score": 75,
    "summary": "Short overall resume evaluation.",
    "strengths": [
        "Strength 1",
        "Strength 2",
        "Strength 3"
    ],
    "weaknesses": [
        "Weakness 1",
        "Weakness 2",
        "Weakness 3"
    ],
    "missing_keywords": [
        "Keyword 1",
        "Keyword 2"
    ],
    "improvements": [
        "Improvement 1",
        "Improvement 2",
        "Improvement 3"
    ],
    "formatting_feedback": [
        "Formatting suggestion 1",
        "Formatting suggestion 2"
    ],
    "job_match": "Explain how well the resume matches the job description."
}}

IMPORTANT:
- ATS score must be an integer between 0 and 100.
- Evaluate actual resume content.
- Do not invent qualifications or experience.
- If no job description is provided, evaluate general ATS compatibility.
- Keep suggestions practical and professional.
- Return valid JSON only.
"""

    response = client.chat.completions.create(
      model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": "You are a professional ATS resume analysis assistant. Return only valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=2500,
        response_format={"type": "json_object"}
    )

    result = response.choices[0].message.content

    # Remove accidental Markdown formatting
    result = re.sub(r"^```(?:json)?\s*", "", result.strip())
    result = re.sub(r"\s*```$", "", result)

    return json.loads(result)


# ---------------- REPORT GENERATION ----------------

def generate_report(data):

    report = f"""
RESUME ATS ANALYSIS REPORT
==========================

ATS SCORE: {data.get('ats_score', 'N/A')}/100

SUMMARY
-------
{data.get('summary', 'N/A')}


STRENGTHS
---------
"""

    for item in data.get("strengths", []):
        report += f"- {item}\n"

    report += "\nWEAKNESSES\n----------\n"

    for item in data.get("weaknesses", []):
        report += f"- {item}\n"

    report += "\nMISSING KEYWORDS\n----------------\n"

    for item in data.get("missing_keywords", []):
        report += f"- {item}\n"

    report += "\nIMPROVEMENT SUGGESTIONS\n-----------------------\n"

    for item in data.get("improvements", []):
        report += f"- {item}\n"

    report += "\nFORMATTING FEEDBACK\n-------------------\n"

    for item in data.get("formatting_feedback", []):
        report += f"- {item}\n"

    report += "\nJOB MATCH\n---------\n"

    report += data.get("job_match", "N/A")

    report += "\n\nGenerated by Resume ATS Analyzer"

    return report


# ---------------- MAIN UI ----------------

st.title("📄 Resume ATS Analyzer")

st.write(
    "Upload your resume and discover its ATS compatibility, "
    "strengths, weaknesses, and improvement opportunities."
)

st.divider()

# ---------------- INPUT SECTION ----------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("📤 Upload Resume")

    uploaded_file = st.file_uploader(
        "Upload your resume (PDF or DOCX)",
        type=["pdf", "docx"]
    )

with col2:
    st.subheader("💼 Job Description")

    job_description = st.text_area(
        "Paste the job description (optional)",
        placeholder="Paste the job requirements here...",
        height=150
    )

st.divider()

# ---------------- ANALYZE BUTTON ----------------

if st.button("🚀 Analyze My Resume", use_container_width=True):

    if uploaded_file is None:

        st.warning("Please upload your resume first.")

    else:

        try:
            with st.spinner("Extracting resume information..."):

                resume_text = extract_resume_text(uploaded_file)

            if not resume_text.strip():

                st.error(
                    "No readable text found. "
                    "Please upload a text-based PDF or DOCX resume."
                )

            else:

                with st.spinner(
                    "AI is analyzing your resume. Please wait..."
                ):

                    analysis = analyze_resume(
                        resume_text,
                        job_description
                    )

                st.session_state["analysis"] = analysis

                st.success("Resume analysis completed successfully!")

        except json.JSONDecodeError:

            st.error(
                "AI returned an invalid response. Please try again."
            )

        except Exception as e:

            st.error("Analysis failed.")

            st.code(str(e))


# ---------------- DISPLAY RESULTS ----------------

if "analysis" in st.session_state:

    data = st.session_state["analysis"]

    st.divider()

    st.header("📊 ATS Analysis Results")

    score = data.get("ats_score", 0)

    try:
        score = max(0, min(100, int(score)))
    except (ValueError, TypeError):
        score = 0

    col1, col2 = st.columns([1, 2])

    with col1:

        st.metric(
            label="ATS Compatibility Score",
            value=f"{score}/100"
        )

        st.progress(score / 100)

        if score >= 80:
            st.success("Strong ATS compatibility")

        elif score >= 60:
            st.warning("Moderate ATS compatibility")

        else:
            st.error("Needs improvement")

    with col2:

        st.subheader("📝 Overall Summary")

        st.write(data.get("summary", "No summary available."))

    st.divider()

    # Strengths and Weaknesses

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("✅ Resume Strengths")

        for item in data.get("strengths", []):
            st.write(f"• {item}")

    with col2:

        st.subheader("⚠️ Resume Weaknesses")

        for item in data.get("weaknesses", []):
            st.write(f"• {item}")

    st.divider()

    # Missing Keywords

    st.subheader("🔑 Missing Keywords")

    keywords = data.get("missing_keywords", [])

    if keywords:

        st.write(", ".join(keywords))

    else:

        st.write("No major missing keywords identified.")

    st.divider()

    # Improvements

    st.subheader("💡 Recommended Improvements")

    for index, item in enumerate(
        data.get("improvements", []), start=1
    ):

        st.write(f"**{index}.** {item}")

    st.divider()

    # Formatting Feedback

    st.subheader("📋 Formatting Feedback")

    for item in data.get("formatting_feedback", []):
        st.write(f"• {item}")

    st.divider()

    # Job Match

    st.subheader("🎯 Job Description Match")

    st.write(data.get("job_match", "Not available."))

    st.divider()

    # Download Report

    st.subheader("📥 Download Your Report")

    report = generate_report(data)

    st.download_button(
        label="Download ATS Analysis Report",
        data=report,
        file_name="resume_ats_report.txt",
        mime="text/plain",
        use_container_width=True
    )

# ---------------- FOOTER ----------------

st.divider()

st.caption(
    "Resume ATS Analyzer | Powered by Groq AI | "
    "AI-generated scores are estimates, not actual employer ATS results."
)
