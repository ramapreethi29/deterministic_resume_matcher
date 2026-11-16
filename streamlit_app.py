
import html

import requests
import streamlit as st
import plotly.graph_objects as go


API_URL = "http://127.0.0.1:8000"


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="ResumeIQ | Resume Matcher",
    page_icon="R",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# SESSION STATE
# =========================================================

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None


# =========================================================
# PROFESSIONAL BLUE THEME
# =========================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* GLOBAL */

.stApp {
    background: #F3F6FA;
    font-family: 'Inter', sans-serif;
    color: #1E293B;
}

.block-container {
    max-width: 1250px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1, h2, h3, h4 {
    color: #173B63 !important;
    font-weight: 700 !important;
}

h1 { font-size: 32px !important; }
h2 { font-size: 25px !important; }
h3 { font-size: 20px !important; }
h4 { font-size: 17px !important; }

p, label {
    color: #475569;
    font-size: 15px;
}

/* HEADER */

.hero {
    background: linear-gradient(120deg, #12365B, #2866A5);
    padding: 30px 34px;
    border-radius: 18px;
    margin-bottom: 30px;
    box-shadow: 0 5px 18px rgba(23, 59, 99, 0.12);
}

.hero h1 {
    color: #FFFFFF !important;
    font-size: 32px !important;
    margin-bottom: 8px;
}

.hero p {
    color: #E1EDFA !important;
    font-size: 15px;
    margin-bottom: 0;
}

/* SECTION HEADINGS */

.section-title {
    font-size: 24px;
    font-weight: 800;
    color: #173B63;
    margin: 20px 0 16px 0;
}

.subsection-heading {
    font-size: 19px;
    font-weight: 750;
    color: #173B63;
    margin: 22px 0 14px 0;
}

.panel-heading {
    color: #173B63;
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 12px;
}

/* METRIC CARDS */


.metric-card {
    display: block !important;
    background: linear-gradient(145deg, #EAF2FC, #F3F7FD) !important;
    border: 1px solid #C8DCF5 !important;
    border-radius: 14px !important;
    padding: 20px !important;
    min-height: 115px;
    margin-bottom: 12px;
    box-shadow: 0 3px 8px rgba(23, 59, 99, 0.05);
}

.metric-label {
    color: #58718D !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    text-transform: uppercase;
}

.metric-value {
    color: #174A80 !important;
    font-size: 27px !important;
    font-weight: 800 !important;
    margin-top: 10px;
}

.metric-subtitle {
    color: #8295AB !important;
    font-size: 12px !important;
    margin-top: 5px;
}

/* MATCHED SKILLS - LIGHT GREEN */

.skill-card.skill-matched {
    display: block !important;
    background: #EAF7EF !important;
    border: 1px solid #B9E4C8 !important;
    border-left: 4px solid #36A269 !important;
    border-radius: 12px;
    padding: 15px 17px;
    margin-bottom: 12px;
    box-shadow: 0 2px 6px rgba(22, 101, 52, 0.04);
    color: #185C38 !important;
}

/* MISSING SKILLS - LIGHT RED */

.skill-card.skill-missing {
    display: block !important;
    background: #FCEEEE !important;
    border: 1px solid #F0C5C5 !important;
    border-left: 4px solid #D95353 !important;
    border-radius: 12px;
    padding: 15px 17px;
    margin-bottom: 12px;
    box-shadow: 0 2px 6px rgba(153, 27, 27, 0.04);
    color: #922F35 !important;
}

/* PARTIAL SKILLS - LIGHT YELLOW */

.skill-card.skill-partial {
    display: block !important;
    background: #FFF7E6 !important;
    border: 1px solid #F1D9A8 !important;
    border-left: 4px solid #D69E16 !important;
    border-radius: 12px;
    padding: 15px 17px;
    margin-bottom: 12px;
    box-shadow: 0 2px 6px rgba(146, 99, 14, 0.04);
    color: #805817 !important;
}

/* SKILL NAME AND EVIDENCE */

.skill-name {
    display: block;
    color: inherit !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    line-height: 1.5;
}

.skill-detail {
    display: block;
    color: #52677E !important;
    font-size: 13px !important;
    line-height: 1.55;
    margin: 7px 0 0 0 !important;
}

/* INFORMATION CARDS */

.info-card {
    display: block !important;
    background: #F0F6FD !important;
    border: 1px solid #D5E4F5 !important;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    box-shadow: 0 2px 7px rgba(15, 23, 42, 0.04);
}

.info-label {
    color: #58718D;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 7px;
}

.info-value {
    color: #174A80;
    font-size: 15px;
    font-weight: 700;
    line-height: 1.5;
    overflow-wrap: anywhere;
}

.info-subtitle {
    color: #8295AB;
    font-size: 12px;
    margin-top: 6px;
}

/* JOB CONDITIONS */

.conditions-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 25px;
}

.condition-card {
    background: linear-gradient(145deg, #FFFFFF, #EDF4FC);
    border: 1px solid #D4E3F4;
    border-radius: 13px;
    padding: 17px;
    min-height: 100px;
    box-shadow: 0 3px 9px rgba(30, 64, 100, 0.04);
}

.condition-label {
    color: #6A829E;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.7px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.condition-value {
    color: #174A80;
    font-size: 16px;
    font-weight: 750;
    overflow-wrap: anywhere;
}

/* SOFT SKILLS */

.soft-skill-card {
    background: #FFFFFF;
    border: 1px solid #D8E5F4;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 13px;
    box-shadow: 0 3px 9px rgba(30, 64, 100, 0.04);
}

.soft-card-title {
    color: #174A80;
    font-size: 16px;
    font-weight: 750;
    margin-bottom: 14px;
}

.soft-skill-container {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
}

.soft-skill-tag {
    display: inline-flex;
    align-items: center;
    background: #EAF2FC;
    color: #285B8C;
    border: 1px solid #D0E1F4;
    border-radius: 20px;
    padding: 7px 13px;
    font-size: 13px;
    font-weight: 650;
}

.soft-empty {
    color: #8A9BB0;
    font-size: 13px;
}

.soft-card-note {
    border-top: 1px solid #E8EEF5;
    padding-top: 11px;
    margin-top: 14px;
    color: #8295AB;
    font-size: 11px;
}

/* OTHER REQUIREMENTS */

.requirement-card {
    background: #FFFFFF;
    border: 1px solid #D8E5F4;
    border-radius: 13px;
    padding: 17px;
    margin-bottom: 12px;
    box-shadow: 0 3px 9px rgba(30, 64, 100, 0.04);
}

.requirement-name {
    color: #294B70;
    font-size: 14px;
    font-weight: 700;
    line-height: 1.5;
    margin-bottom: 12px;
}

.requirement-bottom {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}

.requirement-note {
    color: #8A9BB0;
    font-size: 11px;
    margin-top: 10px;
}

.status-badge {
    display: inline-block;
    padding: 5px 11px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 750;
    white-space: nowrap;
}

.status-verified {
    background: #E6F5EC;
    color: #21804D !important;
}

.status-partial {
    background: #FFF4DE;
    color: #A66B0C !important;
}

.status-missing {
    background: #FCEAEA;
    color: #BD4141 !important;
}

.status-unverified {
    background: #EAF2FC;
    color: #4776A8 !important;
}

/* IMPROVEMENT SUGGESTIONS */

.suggestion-card {
    background: linear-gradient(135deg, #FFFFFF, #F0F6FD);
    border: 1px solid #D3E3F5;
    border-left: 4px solid #528BCB;
    border-radius: 13px;
    padding: 19px;
    margin-bottom: 13px;
    box-shadow: 0 3px 9px rgba(30, 64, 100, 0.04);
}

.suggestion-top {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}

.suggestion-index {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 29px;
    height: 29px;
    flex-shrink: 0;
    border-radius: 9px;
    background: #DCEBFA;
    color: #2866A5;
    font-size: 12px;
    font-weight: 800;
}

.suggestion-heading {
    color: #386D9F;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.6px;
    text-transform: uppercase;
}

.suggestion-text {
    color: #365674;
    font-size: 14px;
    line-height: 1.7;
}

/* ANALYZE BUTTON */

div[data-testid="stFormSubmitButton"] button {
    background: #174A8B !important;
    color: #FFFFFF !important;
    border: 1px solid #123D73 !important;
    border-radius: 10px !important;
    min-height: 49px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    box-shadow: 0 3px 8px rgba(23, 74, 139, 0.18);
}

div[data-testid="stFormSubmitButton"] button p {
    color: #FFFFFF !important;
    font-weight: 700 !important;
}

div[data-testid="stFormSubmitButton"] button:hover {
    background: #103967 !important;
    border-color: #103967 !important;
}

/* INPUTS */

.stTextArea textarea,
.stTextInput input {
    background: #FFFFFF !important;
    color: #243B53 !important;
    border: 1px solid #CBD8E6 !important;
    border-radius: 9px !important;
    font-size: 14px !important;
}

[data-testid="stFileUploader"] {
    background: #FFFFFF;
    border: 1px dashed #AFC4DB;
    border-radius: 12px;
    padding: 12px;
}

/* TABS */

.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    border-bottom: 1px solid #D7E2EE;
}

.stTabs [data-baseweb="tab"] {
    color: #526780;
    font-weight: 600;
    font-size: 14px;
}

.stTabs [aria-selected="true"] {
    color: #174A80 !important;
}

/* DIVIDERS */

hr {
    border-color: #DCE5EF !important;
}

/* RESPONSIVE */

@media (max-width: 768px) {
    .hero {
        padding: 23px;
    }

    .hero h1 {
        font-size: 27px !important;
    }

    .section-title {
        font-size: 21px;
    }

    .info-value {
        font-size: 14px;
    }

    .suggestion-text {
        font-size: 13px;
    }

    .conditions-grid {
        grid-template-columns: 1fr;
    }

    .condition-card {
        min-height: auto;
    }
}

/* JOB CONDITION CARDS */
.condition-card {
    background: #FFFFFF !important;
    border: 1px solid #DCE6F1 !important;
    border-left: 4px solid #5689C7 !important;
    border-radius: 12px !important;
    padding: 15px 17px !important;
    min-height: 65px;
    margin-bottom: 12px;
    box-shadow: 0 2px 7px rgba(30, 60, 90, 0.04);
}

.condition-text {
    color: #344B63 !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    line-height: 1.5 !important;
}

/* SUGGESTION CARDS */
.suggestion-card {
    display: flex !important;
    align-items: flex-start !important;
    gap: 14px;
    background: #F0F6FD !important;
    border: 1px solid #D5E5F7 !important;
    border-radius: 12px !important;
    padding: 17px 19px !important;
    margin-bottom: 12px;
}

.suggestion-number {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: #DCEBFA !important;
    color: #245B91 !important;
    font-size: 14px !important;
    font-weight: 800 !important;
}

.suggestion-text {
    color: #344B63 !important;
    font-size: 14px !important;
    line-height: 1.7 !important;
    font-weight: 500 !important;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# HELPERS
# =========================================================

def safe_text(value):
    return html.escape(str(value))


def item_name(entry):
    item = entry.get("item", "Unknown")

    if isinstance(item, dict):
        if "any_of" in item:
            return " OR ".join(map(str, item["any_of"]))

        if "domain" in item:
            return f"Experience: {item.get('domain') or 'General'}"

        if "min_months" in item:
            return f"Experience: {item.get('min_months', 0)} months minimum"

        return str(item)

    return str(item)


# =========================================================
# SKILL CARDS
# =========================================================

def display_skill_cards(items, status):
    if not items:
        st.caption("No items in this category.")
        return

    styles = {
        "matched": "skill-matched",
        "missing": "skill-missing",
        "partial": "skill-partial",
    }

    css_class = styles.get(status, "skill-matched")

    for entry in items:
        name = item_name(entry)

        evidence = (
            entry.get("evidence")
            or entry.get("reason")
            or ""
        )

        st.markdown(
            f"""
            <div class="skill-card {css_class}">
                <div class="skill-name">
                    {safe_text(name)}
                </div>
                {
                    f'<div class="skill-detail">{safe_text(evidence)}</div>'
                    if evidence else ''
                }
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# METRIC CARDS
# =========================================================

def metric_card(label, value, subtitle=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{safe_text(label)}</div>
            <div class="metric-value">{safe_text(value)}</div>
            {f'<div class="metric-subtitle">{safe_text(subtitle)}</div>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# INFORMATION CARDS
# =========================================================

def information_card(label, value, subtitle=""):
    st.markdown(
        f"""
        <div class="info-card">
            <div class="info-label">
                {safe_text(label)}
            </div>

            <div class="info-value">
                {safe_text(value)}
            </div>

            <div class="info-subtitle">
                {safe_text(subtitle)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# JOB CONDITIONS
# =========================================================
def job_conditions_section(conditions):
    if not conditions:
        st.caption("No job conditions identified.")
        return

    if isinstance(conditions, dict):
        entries = conditions.items()
    elif isinstance(conditions, list):
        entries = []
        for condition in conditions:
            if isinstance(condition, dict):
                label = (
                    condition.get("name")
                    or condition.get("key")
                    or condition.get("type")
                    or "Condition"
                )
                value = (
                    condition.get("value")
                    or condition.get("condition")
                    or condition.get("text")
                    or ""
                )
                entries.append((label, value))
            else:
                entries.append(("Condition", condition))
    else:
        entries = [("Condition", conditions)]

    entries = [
        (label, value)
        for label, value in entries
        if value is not None and str(value).strip()
    ]

    if not entries:
        st.caption("No job conditions identified.")
        return

    cols = st.columns(3)

    for i, (label, value) in enumerate(entries):
        if isinstance(value, list):
            value = ", ".join(map(str, value))

        readable_label = str(label).replace("_", " ").title()

        with cols[i % 3]:
            st.markdown(
                f"""
                <div class="condition-card">
                    <div class="condition-label">
                        {safe_text(readable_label)}
                    </div>
                    <div class="condition-value">
                        {safe_text(value)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
# =========================================================
# SOFT SKILL CARDS
# =========================================================
def soft_skill_card(title, skills):
    if not skills:
        content = """
            <span class="soft-empty">No skills identified</span>
        """
    else:
        tags = "".join(
            f'<span class="soft-skill-tag">{safe_text(skill)}</span>'
            for skill in skills
        )

        content = f"""
            <div class="soft-skill-container">
                {tags}
            </div>
        """

    card_html = f"""
        <div class="soft-skill-card">
            <div class="soft-card-title">{safe_text(title)}</div>
            {content}
            <div class="soft-card-note">
                Informational only · Not included in match score
            </div>
        </div>
    """

    st.html(card_html)
# =========================================================
# OTHER REQUIREMENT CARDS
# =========================================================
def requirement_card(item, status="unverified"):
    status_text = str(status).lower().replace(" ", "_")

    status_map = {
        "verified": ("status-verified", "Verified"),
        "matched": ("status-verified", "Verified"),
        "demonstrated": ("status-verified", "Verified"),
        "partial": ("status-partial", "Partial"),
        "partially_matched": ("status-partial", "Partial"),
        "missing": ("status-missing", "Missing"),
        "unmatched": ("status-missing", "Missing"),
    }

    color_class, label = status_map.get(
        status_text,
        ("status-unverified", "Unverified"),
    )

    if isinstance(item, dict):
        item = (
            item.get("name")
            or item.get("requirement")
            or item.get("text")
            or item.get("value")
            or str(item)
        )

    card_html = f"""
        <div class="requirement-card">
            <div class="requirement-name">
                {safe_text(item)}
            </div>

            <div class="requirement-bottom">
                <span class="requirement-note">
                    Requirement status
                </span>

                <span class="status-badge {color_class}">
                    {label}
                </span>
            </div>

            <div class="requirement-note">
                Informational only · Not scored
            </div>
        </div>
    """

    st.html(card_html)

# =========================================================
# SUGGESTION CARDS
# =========================================================
def suggestion_cards(suggestions):
    if not suggestions:
        st.caption("No suggestions available.")
        return

    for i, suggestion in enumerate(suggestions, start=1):
        if isinstance(suggestion, dict):
            suggestion = (
                suggestion.get("text")
                or suggestion.get("suggestion")
                or suggestion.get("description")
                or str(suggestion)
            )

        st.markdown(
            f"""
            <div class="suggestion-card">
                <div class="suggestion-number">{i}</div>
                <div class="suggestion-text">
                    {safe_text(suggestion)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# =========================================================
# REQUIREMENT GROUPS
# =========================================================

def display_requirement_group(data):
    categories = [
        ("matched", "Matched", "matched"),
        ("partial", "Partially matched", "partial"),
        ("missing", "Missing", "missing"),
    ]

    if not isinstance(data, dict):
        st.caption("No requirements available.")
        return

    for key, heading, status in categories:
        entries = data.get(key, [])

        if entries:
            st.markdown(f"#### {heading} ({len(entries)})")
            display_skill_cards(entries, status)

    if not any(data.get(key, []) for key in ("matched", "partial", "missing")):
        st.caption("No requirements in this category.")
# =========================================================
# SCORE COLORS
# =========================================================

def score_color(score):
    if score > 80:
        return "#168653"
    elif score >= 60:
        return "#2878C8"
    elif score >= 40:
        return "#D69E16"
    else:
        return "#DC4545"


# =========================================================
# SCORE CHART
# =========================================================

def score_chart(score):
    score = max(0, min(100, score))
    remaining = 100 - score

    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Matched", "Remaining"],
                values=[score, remaining],
                hole=0.70,
                sort=False,
                direction="clockwise",
                marker=dict(
                    colors=[
                        score_color(score),
                        "#E4ECF5",
                    ],
                    line=dict(
                        color="white",
                        width=3,
                    ),
                ),
                textinfo="none",
                hovertemplate=(
                    "%{label}: %{value:.1f}%<extra></extra>"
                ),
            )
        ]
    )

    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            x=0.5,
            xanchor="center",
            y=-0.08,
            font=dict(
                size=12,
                color="#526780",
            ),
        ),
        annotations=[
            dict(
                text=f"<b>{score:.0f}%</b>",
                x=0.5,
                y=0.53,
                font=dict(
                    size=34,
                    color="#17365D",
                ),
                showarrow=False,
            ),
            dict(
                text="MATCH SCORE",
                x=0.5,
                y=0.37,
                font=dict(
                    size=10,
                    color="#8091A7",
                ),
                showarrow=False,
            ),
        ],
        margin=dict(
            t=10,
            b=35,
            l=10,
            r=10,
        ),
        height=270,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


# =========================================================
# HEADER
# =========================================================

st.markdown("""
<div class="hero">
    <h1>Resume Match Analyzer</h1>

    
</div>
""", unsafe_allow_html=True)


# =========================================================
# INPUT FORM
# =========================================================

st.markdown(
    '<div class="section-title">Analyze your resume</div>',
    unsafe_allow_html=True,
)

with st.form(
    "resume_analysis_form",
    clear_on_submit=False,
):

    left, right = st.columns(
        [1, 1.5],
        gap="large",
    )

    with left:
        st.markdown("**01 · Upload your resume**")

        resume_file = st.file_uploader(
            "Upload PDF resume",
            type=["pdf"],
            label_visibility="collapsed",
            key="resume_upload",
        )

        st.caption("PDF format only")

    with right:
        st.markdown("**02 · Job description**")

        jd_text = st.text_area(
            "Job description",
            height=180,
            placeholder="Paste the complete job description here...",
            label_visibility="collapsed",
            key="jd_input",
        )

    st.write("")

    analyze_button = st.form_submit_button(
        "Analyze Resume  →",
        type="primary",
        use_container_width=True,
    )


# =========================================================
# ANALYZE API
# =========================================================

if analyze_button:

    if resume_file is None:
        st.error("Please upload your PDF resume.")

    elif not jd_text.strip():
        st.error("Please paste a job description.")

    elif len(jd_text.strip()) < 50:
        st.error(
            "Job description must contain at least 50 characters."
        )

    elif len(jd_text.strip()) > 5000:
        st.error(
            "Job description cannot exceed 5000 characters."
        )

    else:
        try:
            with st.spinner(
                "Analyzing your resume. Please wait..."
            ):

                response = requests.post(
                    f"{API_URL}/analyze",
                    files={
                        "file": (
                            resume_file.name,
                            resume_file.getvalue(),
                            "application/pdf",
                        )
                    },
                    data={
                        "jd_text": jd_text.strip()
                    },
                    timeout=180,
                )

            if response.status_code == 200:
                st.session_state.analysis_result = (
                    response.json()
                )

                st.success(
                    "Resume analysis completed successfully."
                )

            else:
                try:
                    error = response.json().get(
                        "detail",
                        response.text,
                    )
                except ValueError:
                    error = response.text

                st.error(f"Analysis failed: {error}")

        except requests.exceptions.ConnectionError:
            st.error(
                "Cannot connect to FastAPI. "
                "Start the backend before analyzing."
            )

        except requests.exceptions.Timeout:
            st.error(
                "The request timed out. Please try again."
            )

        except requests.exceptions.RequestException as exc:
            st.error(f"Request error: {exc}")

        except ValueError:
            st.error(
                "The backend returned an invalid response."
            )


# =========================================================
# RESULTS
# =========================================================

result = st.session_state.analysis_result

if result:

    st.divider()

    st.markdown(
        '<div class="section-title">Analysis overview</div>',
        unsafe_allow_html=True,
    )

    score = float(result.get("score", 0))

    breakdown = result.get("score_breakdown", {})

    required_score = breakdown.get("required", {})
    preferred_score = breakdown.get("preferred", {})

    # -----------------------------------------------------
    # SCORE AND METRICS
    # -----------------------------------------------------

    chart_col, metrics_col = st.columns(
        [1, 1.5],
        gap="large",
    )

    with chart_col:

        st.markdown(
            '<div class="panel-heading">Overall match score</div>',
            unsafe_allow_html=True,
        )

        st.plotly_chart(
            score_chart(score),
            use_container_width=True,
            config={
                "displayModeBar": False
            },
        )

    with metrics_col:

        st.markdown(
            '<div class="panel-heading">Score breakdown</div>',
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)

        with c1:
            metric_card(
                "Required match",
                f"{required_score.get('pct', 0) * 100:.1f}%",
            )

        with c2:
            metric_card(
                "Preferred match",
                f"{preferred_score.get('pct', 0) * 100:.1f}%",
            )

        c3, c4 = st.columns(2)

        with c3:
            metric_card(
                "Required credit",
                (
                    f"{required_score.get('credit', 0)} / "
                    f"{required_score.get('total', 0)}"
                ),
            )

        with c4:
            metric_card(
                "Preferred credit",
                (
                    f"{preferred_score.get('credit', 0)} / "
                    f"{preferred_score.get('total', 0)}"
                ),
            )

    # -----------------------------------------------------
    # SKILLS COMPARISON
    # -----------------------------------------------------

    st.divider()

    st.markdown(
        '<div class="section-title">Skills comparison</div>',
        unsafe_allow_html=True,
    )

    required_data = result.get("required", {})
    preferred_data = result.get("preferred", {})

    all_matched = (
        required_data.get("matched", [])
        + preferred_data.get("matched", [])
    )

    all_missing = (
        required_data.get("missing", [])
        + preferred_data.get("missing", [])
    )

    all_partial = (
        required_data.get("partial", [])
        + preferred_data.get("partial", [])
    )

    matched_skills = [
        x for x in all_matched
        if x.get("kind") == "skill"
    ]

    missing_skills = [
        x for x in all_missing
        if x.get("kind") == "skill"
    ]

    partial_skills = [
        x for x in all_partial
        if x.get("kind") == "skill"
    ]

    matched_col, missing_col = st.columns(
        2,
        gap="large",
    )

    with matched_col:

        st.markdown(
            f"""
            ### <span style='color:#168653'>
            Matched skills ({len(matched_skills)})
            </span>
            """,
            unsafe_allow_html=True,
        )

        display_skill_cards(
            matched_skills,
            "matched",
        )

    with missing_col:

        st.markdown(
            f"""
            ### <span style='color:#C53D3D'>
            Missing skills ({len(missing_skills)})
            </span>
            """,
            unsafe_allow_html=True,
        )

        display_skill_cards(
            missing_skills,
            "missing",
        )

    if partial_skills:

        st.markdown(
            f"""
            ### <span style='color:#B7791F'>
            Partially matched skills ({len(partial_skills)})
            </span>
            """,
            unsafe_allow_html=True,
        )

        display_skill_cards(
            partial_skills,
            "partial",
        )
    # -----------------------------------------------------
    # REQUIRED AND PREFERRED DETAILS
    # -----------------------------------------------------

    st.divider()

    st.markdown(
        '<div class="section-title">Requirement details</div>',
        unsafe_allow_html=True,
    )

    required_col, preferred_col = st.columns(
        2,
        gap="large",
    )

    with required_col:
        st.markdown("### Required requirements")
        display_requirement_group(required_data)

    with preferred_col:
        st.markdown("### Preferred requirements")
        display_requirement_group(preferred_data)

    # -----------------------------------------------------
    # ADDITIONAL INFORMATION
    # -----------------------------------------------------

    st.divider()

    st.markdown(
        '<div class="section-title">Additional information</div>',
        unsafe_allow_html=True,
    )

    info1, info2 = st.columns(
        [1, 1],
        gap="large",
    )

    # LEFT COLUMN
    with info1:

        st.markdown(
            '<div class="subsection-heading">Job conditions</div>',
            unsafe_allow_html=True,
        )

        conditions = result.get("job_conditions", {})
        job_conditions_section(conditions)

        st.markdown(
            '<div class="subsection-heading">Soft skills</div>',
            unsafe_allow_html=True,
        )

        soft = result.get("soft_skills", {})

        if not isinstance(soft, dict):
            soft = {}

        soft_skill_card(
            "From job description",
            soft.get("jd", []),
        )

        soft_skill_card(
            "From resume",
            soft.get("resume", []),
        )

    # RIGHT COLUMN
    with info2:

        st.markdown(
            '<div class="subsection-heading">Other requirements</div>',
            unsafe_allow_html=True,
        )

        other = result.get("other_requirements", [])

        if isinstance(other, list) and other:
            for entry in other:

                if isinstance(entry, dict):
                    item = (
                        entry.get("item")
                        or entry.get("name")
                        or entry.get("requirement")
                        or entry.get("text")
                        or "Requirement"
                    )

                    status = entry.get("status", "unverified")

                else:
                    item = entry
                    status = "unverified"

                requirement_card(item, status)

        else:
            st.caption(
                "No additional requirements identified."
            )

        st.markdown(
            '<div class="subsection-heading">Improvement suggestions</div>',
            unsafe_allow_html=True,
        )

        suggestion_cards(
            result.get("suggestions", [])
        )
