# ResumeIQ – Resume Match Analyzer

ResumeIQ is a Python-based resume analysis application that evaluates a candidate's resume against a job description. It identifies matching skills, missing requirements, experience alignment, and areas for improvement.

## Features

- Upload resumes in PDF format.
- Analyze job descriptions.
- Identify required and preferred skills.
- Detect matched, partially matched, and missing skills.
- Evaluate professional and internship experience.
- Compare educational qualifications and certifications.
- Calculate an overall resume match score.
- Display score breakdowns and visualizations.
- Generate actionable improvement suggestions.

## Tech Stack

- Python
- FastAPI
- Streamlit
- Plotly
- PyPDF

## Project Structure

```text
ResumeIQ/
│
├── app/
│   └── ...
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
git clone YOUR_GITHUB_REPOSITORY_URL
cd ResumeIQ
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Start the backend

```bash
python -m uvicorn main:app --reload
```

Backend: `http://127.0.0.1:8000`

API documentation: `http://127.0.0.1:8000/docs`

### 5. Start the frontend

Open another terminal:

```bash
python -m streamlit run streamlit_app.py
```

## How to Use

1. Upload your resume in PDF format.
2. Paste a job description.
3. Click Analyze Resume.
4. View your resume match score.
5. Review matching and missing skills.
6. Explore experience, education, and certification alignment.
7. Follow the improvement suggestions.

## Future Enhancements

- User authentication
- Resume analysis history
- Downloadable analysis reports
- Enhanced reporting and visualizations

## Author

Developed as a Python-based resume analysis and backend development project.