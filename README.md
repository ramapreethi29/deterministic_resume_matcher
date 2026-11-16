# ResumeIQ – Technical Resume Matcher

ResumeIQ is a Python-based resume matching application designed for **Software Development, AI/ML, and Data roles**. It evaluates a candidate's resume against a job description to identify matching skills, missing requirements, experience alignment, and areas for improvement.

The project combines **deterministic matching and explainable scoring with AI-assisted skill resolution** to provide structured and evidence-based resume analysis.

## Features

- Upload resumes in PDF format.
- Extract and analyze resume information.
- Analyze job descriptions and identify required and preferred qualifications.
- Normalize technical skills for consistent matching.
- Identify matched, partially matched, and missing skills.
- Evaluate professional and internship experience.
- Compare educational qualifications and certifications.
- Calculate an overall resume match score.
- Display score breakdowns and visualizations.
- Generate actionable improvement suggestions.
- Use AI-assisted fallback for unresolved skill identification.

## Matching Approach

ResumeIQ uses a hybrid approach:

- **Deterministic matching:** Handles skill matching, experience evaluation, education, certifications, and scoring using rule-based logic.
- **AI-assisted skill resolution:** Uses an LLM fallback to help resolve skills that cannot be confidently identified through deterministic processing.
- **Explainable results:** Provides structured matching results and score breakdowns.

## Tech Stack

- Python
- FastAPI
- Streamlit
- Plotly
- PyPDF
- LLM-assisted skill resolution

## Project Structure

```text
deterministic_resume_matcher/
│
├── data/
├── engine/
│   ├── jd_parser.py
│   ├── llm_fallback.py
│   ├── matcher.py
│   ├── normalize.py
│   ├── profile_builder.py
│   ├── report.py
│   ├── resume_parser.py
│   ├── resume_scan.py
│   ├── schemas.py
│   ├── scorer.py
│   ├── service.py
│   ├── skills.json
│   └── suggestions.py
│
├── main.py
├── streamlit_app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/ramapreethi29/deterministic_resume_matcher.git
cd deterministic_resume_matcher
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Start the backend

```bash
python -m uvicorn main:app --reload
```

Backend: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

### 6. Start the frontend

Open another terminal, activate the virtual environment, and run:

```bash
python -m streamlit run streamlit_app.py
```

## How to Use

1. Upload your resume in PDF format.
2. Paste the job description.
3. Click **Analyze Resume**.
4. View the overall resume match score.
5. Review matching, partially matching, and missing skills.
6. Explore experience, education, and certification alignment.
7. Review the improvement suggestions.

## Future Enhancements

- User authentication
- Resume analysis history
- Downloadable analysis reports
- Enhanced reporting and visualizations

## Author

Developed as a Python project focused on backend development, deterministic algorithms, and AI-assisted resume analysis.