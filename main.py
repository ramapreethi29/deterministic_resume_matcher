
"""FastAPI entry point for the Resume Matcher."""

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from pypdf.errors import PdfReadError
from engine.profile_builder import build_resume_profile
from engine.jd_parser import parse_jd
from engine.resume_parser import parse_resume_pdf_bytes
from engine.service import analyze

app = FastAPI(
    title="Deterministic Resume Matcher",
    version="1.0.0",
)


class JDRequest(BaseModel):
    jd_text: str = Field(min_length=50, max_length=5000)


@app.get("/health")
def health():
    return {"status": "healthy"}



from fastapi import Body

@app.post("/jd")
def parse_jd_endpoint(
    jd_text: str = Body(
        ...,
        media_type="text/plain",
        min_length=50,
        max_length=5000,
    )
):
    """Accept plain JD text and parse its requirements."""
    try:
        result = parse_jd(jd_text)
        return result.model_dump()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@app.post("/resume")
async def parse_resume_endpoint(
    file: UploadFile = File(...)
):
    """Upload and parse a PDF resume."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF resume.",
        )

    try:
        pdf_bytes = await file.read()
        parsed_resume = parse_resume_pdf_bytes(pdf_bytes)
        return build_resume_profile(parsed_resume)

    except (ValueError, PdfReadError, OSError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    finally:
        await file.close()


@app.post("/analyze")
async def analyze_endpoint(
    file: UploadFile = File(...),
    jd_text: str = Form(..., min_length=50, max_length=5000),
):
    """Analyze an uploaded resume against a job description."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF resume.",
        )

    try:
        pdf_bytes = await file.read()
        parsed_resume = parse_resume_pdf_bytes(pdf_bytes)
        resume_json = build_resume_profile(parsed_resume)
        print("ANALYZE JD TEXT:")
        print(repr(jd_text))
        return analyze(
            resume_json=resume_json,
            jd_text=jd_text,
        )

    except (ValueError, RuntimeError, PdfReadError, OSError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    finally:
        await file.close()
