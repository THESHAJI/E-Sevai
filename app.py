import sys
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.validator import UserProfile
from src.scheme_service import load_schemes, search_schemes
from src.eligibility import evaluate_schemes
from src.ai_assistant import explain_with_llm

load_dotenv()

st.set_page_config(
    page_title="E-Sevai AI",
    page_icon="🇮🇳",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --gov-blue: #123f73;
        --gov-blue-2: #1d73c9;
        --gov-light: #edf4fb;
        --gov-border: #d8e4ef;
        --gov-text: #1d2d3e;
    }
    [data-testid="stAppViewContainer"] {background: #f4f7fb;}
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #123f73 0%, #0b4f9c 100%);
        border-right: 1px solid #083761;
    }
    [data-testid="stSidebar"] * {color: white;}
    [data-testid="stSidebar"] [role="radiogroup"] label {
        border-radius: 8px;
        padding: 6px 8px;
        margin: 2px 0;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: rgba(255,255,255,.16);
    }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {color: #eef5fc;}
    [data-testid="stSidebar"] [data-baseweb="select"] *,
    [data-testid="stSidebar"] [data-baseweb="select"] + div *,
    [data-testid="stSidebar"] [data-baseweb="popover"] * {color: #1d2d3e !important;}
    [data-testid="stHeader"] {background: #f7fafc;}
    .block-container {padding-top: 1.5rem; max-width: 1180px;}
    h1, h2, h3 {color: #123f73;}
    h1 {font-size: 2rem; letter-spacing: -.02em;}
    h2 {font-size: 1.35rem;}
    p, li, label {color: var(--gov-text);}
    .hero {
        background: linear-gradient(135deg, #123f73 0%, #1d73c9 100%);
        color: white; border-radius: 14px; padding: 30px 34px; margin-bottom: 20px;
        box-shadow: 0 8px 24px rgba(18,63,115,.16);
    }
    .hero h1, .hero p {color: white;}
    .hero p {font-size: 1.05rem; max-width: 760px; margin-bottom: 0;}
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid var(--gov-border);
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 3px 12px rgba(18,63,115,.06);
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: white;
        border: 1px solid var(--gov-border) !important;
        border-radius: 12px;
        box-shadow: 0 3px 12px rgba(18,63,115,.055);
    }
    [data-testid="stForm"] {
        background: white;
        border: 1px solid var(--gov-border);
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 3px 12px rgba(18,63,115,.055);
    }
    .status-badge {
        display: inline-block;
        border-radius: 999px;
        padding: 5px 11px;
        font-size: .88rem;
        font-weight: 700;
        letter-spacing: .01em;
    }
    .eligible {background:#e8f5ee; color:#16794b; border:1px solid #acd6bf;}
    .potential {background:#fff6df; color:#835800; border:1px solid #e9cf82;}
    .noteligible {background:#fdeeee; color:#b42318; border:1px solid #e7b2b2;}
    .section-note {
        background:#edf4fb;
        border-left:4px solid #1d73c9;
        border-radius:6px;
        padding:10px 14px;
        color:#234b73;
    }
    .official-links a {font-weight:600;}
    div.stButton > button, div.stLinkButton > button {
        border-radius: 8px;
        min-height: 42px;
        font-weight: 600;
    }
    div.stButton > button[kind="primary"] {
        background: #123f73;
        border-color: #123f73;
    }
    [data-testid="stAlert"] {border-radius:10px;}
    @media (max-width: 700px) {
        .block-container {padding-left: .8rem; padding-right: .8rem;}
        .hero {padding: 22px 20px;}
        h1 {font-size: 1.65rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "schemes" not in st.session_state:
    try:
        st.session_state.schemes = load_schemes()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        st.session_state.schemes = []
        st.session_state.scheme_load_error = str(exc)
if "profile" not in st.session_state:
    st.session_state.profile = None
if "results" not in st.session_state:
    st.session_state.results = []
if "selected_scheme_id" not in st.session_state:
    st.session_state.selected_scheme_id = None
if "language" not in st.session_state:
    st.session_state.language = "English"
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"


STATES_AND_UTS = [
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam",
    "Bihar", "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir",
    "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha",
    "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]

LANGUAGES = ["English", "Hindi", "Tamil"]

UI_TEXT = {
    "English": {
        "home": "Home", "profile": "Location / Profile", "results": "Find Schemes",
        "details": "Scheme Details", "assistant": "AI Assistant",
        "find": "Find eligible schemes", "status": "Eligibility",
    },
    "Hindi": {
        "home": "मुखपृष्ठ", "profile": "स्थान / प्रोफ़ाइल", "results": "योजनाएँ खोजें",
        "details": "योजना विवरण", "assistant": "AI सहायक",
        "find": "पात्र योजनाएँ खोजें", "status": "पात्रता",
    },
    "Tamil": {
        "home": "முகப்பு", "profile": "இடம் / சுயவிவரம்", "results": "திட்டங்களை கண்டறி",
        "details": "திட்ட விவரங்கள்", "assistant": "AI உதவியாளர்",
        "find": "தகுதியான திட்டங்களை கண்டறி", "status": "தகுதி",
    },
}


def ui(key: str) -> str:
    return UI_TEXT.get(st.session_state.language, UI_TEXT["English"]).get(
        key, UI_TEXT["English"][key]
    )


def tri_state(label: str, key: str, field_name: str | None = None):
    existing = None
    profile = st.session_state.profile
    if profile is not None:
        existing = getattr(profile, field_name or key, None)
    default_index = 0
    if existing is True:
        default_index = 1
    elif existing is False:
        default_index = 2
    choice = st.selectbox(
        label,
        ["Unknown", "Yes", "No"],
        index=default_index,
        key=key,
    )
    return None if choice == "Unknown" else choice == "Yes"


def status_class(status: str) -> str:
    return {"Eligible": "eligible", "Potentially Eligible": "potential", "Not Eligible": "noteligible"}[status]


def status_badge(status: str) -> str:
    return f"<span class='status-badge {status_class(status)}'>{status}</span>"


def select_index(options: list[str], value) -> int:
    if value is None:
        return options.index("Unknown") if "Unknown" in options else 0
    return options.index(value) if value in options else 0


def navigate_to(page: str):
    st.session_state.current_page = page
    st.rerun()


with st.sidebar:
    st.markdown("## E-Sevai AI")
    st.caption("Government Scheme Discovery")
    language_options = ["English", "Hindi", "Tamil"]
    st.session_state.language = st.selectbox(
        "Language / भाषा / மொழி",
        language_options,
        index=language_options.index(st.session_state.language),
    )
    labels = {
        "Home": ui("home"), "Profile": ui("profile"), "Scheme Results": ui("results"),
        "Scheme Details": ui("details"), "AI Assistant": ui("assistant"),
    }
    selected_page = st.radio(
        "Navigation",
        list(labels),
        index=list(labels).index(st.session_state.current_page),
        format_func=lambda item: labels[item],
        label_visibility="collapsed",
    )
    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
    st.divider()
    st.caption("English-first interface")
    st.caption("Final eligibility must be confirmed on official portals.")

page = st.session_state.current_page


if page == "Home":
    if st.session_state.get("scheme_load_error"):
        st.error(
            "Scheme data could not be loaded. Please verify data/schemes.json before using eligibility search."
        )
    st.markdown(
        '<div class="hero"><h1>E-Sevai AI</h1>'
        '<p>Discover Indian government schemes using a transparent, evidence-based eligibility check.</p></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Schemes in collection", len(st.session_state.schemes))
    c2.metric("Decision mode", "Deterministic")
    c3.metric("Official source links", "Available")
    st.caption(
        "Coverage: selected Central, Tamil Nadu, Maharashtra, Karnataka, Kerala and Delhi official sources "
        "are represented. This MVP does not crawl or claim coverage of every state website."
    )
    st.caption("Hindi and Tamil navigation are partially translated. Scheme names and all detailed scheme content remain in English.")

    st.subheader("How it works")
    a, b, c, d = st.columns(4)
    a.markdown("**1. Add profile**\nEnter age, state and household details.")
    b.markdown("**2. Compare rules**\nPython checks each configured condition.")
    c.markdown("**3. Review evidence**\nMatched, failed and unknown items are shown.")
    d.markdown("**4. Apply officially**\nUse the linked government portal.")

    if st.button("Create your profile", type="primary"):
        navigate_to("Profile")

elif page == "Profile":
    st.title("Your Profile")
    st.markdown("<div class='section-note'>Complete the information you know. Unknown fields are never treated as satisfied.</div>", unsafe_allow_html=True)

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Location")
            profile = st.session_state.profile
            state_options = ["Unknown"] + STATES_AND_UTS
            language_options = ["Unknown"] + LANGUAGES
            state = st.selectbox(
                "State / Union Territory",
                state_options,
                index=select_index(state_options, profile.state if profile else None),
            )
            district = st.text_input("District", value=profile.district if profile and profile.district else "")
            native_place = st.text_input("Native place (village, town or city)", value=profile.native_place if profile and profile.native_place else "")
            native_language = st.selectbox(
                "Preferred / native language",
                language_options,
                index=select_index(language_options, profile.native_language if profile else None),
            )
            st.subheader("Personal and household")
            age = st.number_input("Age (optional)", min_value=0, max_value=120, value=profile.age if profile and profile.age is not None else None, step=1)
            gender_options = ["Unknown", "Female", "Male", "Other"]
            gender = st.selectbox("Gender", gender_options, index=select_index(gender_options, profile.gender if profile else None))
            annual_income = st.number_input("Annual family income (Rs., optional)", min_value=0, max_value=100000000, value=profile.annual_income if profile and profile.annual_income is not None else None, step=10000)
        with col2:
            st.subheader("Profile")
            occupation_options = ["Unknown", "Farmer", "Agricultural laborer", "Self-employed", "Small business", "Micro-enterprise owner", "Unemployed", "Job seeker", "Student", "Salaried", "Other"]
            occupation = st.selectbox("Occupation", occupation_options, index=select_index(occupation_options, profile.occupation if profile else None))
            education_options = ["Unknown", "10th or below", "12th Passed", "ITI", "Diploma", "Undergraduate", "Postgraduate", "College Student", "Currently in higher education"]
            education = st.selectbox("Education", education_options, index=select_index(education_options, profile.education if profile else None))
            residence_options = ["Unknown", "Urban", "Rural", "Both"]
            residence_type = st.selectbox("Residence", residence_options, index=select_index(residence_options, profile.residence_type if profile else None))
            category_options = ["Unknown", "General", "OBC", "SC", "ST", "EWS"]
            category = st.selectbox("Social category (optional)", category_options, index=select_index(category_options, profile.category if profile else None))
            st.subheader("Additional conditions")
            is_farmer = tri_state("Are you a landholding farmer?", "is_farmer")
            is_pregnant = tri_state("Are you pregnant or a lactating mother?", "is_pregnant")
            is_first_pregnancy = tri_state("Is this your first pregnancy?", "is_first_pregnancy")
            is_govt_school_student = tri_state(
                "Did you study in a Tamil Nadu government school for relevant classes?",
                "govt_school",
                "is_govt_school_student",
            )
            bpl = tri_state("Is the family officially below poverty line?", "bpl")

        submitted = st.form_submit_button("Find eligible schemes", type="primary", use_container_width=True)

    if submitted:
        try:
            profile = UserProfile(
                age=age,
                state=None if state == "Unknown" else state,
                district=district.strip() or None,
                native_place=native_place.strip() or None,
                native_language=None if native_language == "Unknown" else native_language,
                annual_income=annual_income,
                occupation=None if occupation == "Unknown" else occupation,
                education=None if education == "Unknown" else education,
                gender=None if gender == "Unknown" else gender,
                category=None if category == "Unknown" else category,
                is_farmer=is_farmer,
                is_pregnant=is_pregnant,
                is_first_pregnancy=is_first_pregnancy,
                is_govt_school_student=is_govt_school_student,
                bpl=bpl,
                residence_type=None if residence_type == "Unknown" else residence_type,
            )
        except ValidationError as exc:
            st.error("Please correct the profile values: " + "; ".join(
                error["msg"] for error in exc.errors()
            ))
        else:
            st.session_state.profile = profile
            st.session_state.results = evaluate_schemes(profile, st.session_state.schemes)
            navigate_to("Scheme Results")

elif page == "Scheme Results":
    st.title("Scheme Results")
    if not st.session_state.profile:
        st.info("Complete your profile first.")
        if st.button("Go to Profile"):
            navigate_to("Profile")
    else:
        if st.button("Edit Profile"):
            navigate_to("Profile")
        st.caption("Rules are deterministic. Unknown fields are never counted as passed.")
        selected_state = st.session_state.profile.state
        indexed_states = sorted({
            state
            for scheme in st.session_state.schemes
            for state in scheme.get("states", [])
            if state != "All India"
        })
        if selected_state and selected_state not in indexed_states:
            st.markdown(
                "<div class='section-note'><strong>Local scheme data unavailable.</strong><br>"
                f"No state/UT-specific scheme records are indexed for {selected_state}. "
                "Central Government schemes remain available below.</div>",
                unsafe_allow_html=True,
            )
        st.caption("Scheme details are shown in English. Official names are preserved.")
        query = st.text_input("Search this result set")
        category = st.selectbox("Category", ["All"] + sorted({s["category"] for s in st.session_state.results}))
        filtered = search_schemes(st.session_state.results, query, category)

        eligible_count = sum(s["eligibility"]["status"] == "Eligible" for s in filtered)
        potential_count = sum(s["eligibility"]["status"] == "Potentially Eligible" for s in filtered)
        not_count = sum(s["eligibility"]["status"] == "Not Eligible" for s in filtered)
        m1, m2, m3 = st.columns(3)
        m1.metric("Eligible", eligible_count)
        m2.metric("Potentially eligible", potential_count)
        m3.metric("Not eligible", not_count)

        for scheme in filtered:
            result = scheme["eligibility"]
            with st.container(border=True):
                left, right = st.columns([4, 1])
                with left:
                    st.subheader(scheme["name"])
                    st.write(scheme["summary"])
                    st.markdown(status_badge(result["status"]), unsafe_allow_html=True)
                with right:
                    if st.button("View details", key=f"view_{scheme['id']}"):
                        st.session_state.selected_scheme_id = scheme["id"]
                        navigate_to("Scheme Details")

                matched = len(result["matched"])
                failed = len(result["failed"])
                unknown = len(result["unknown"])
                st.caption(f"{matched} matched · {failed} failed · {unknown} unknown")

elif page == "Scheme Details":
    st.title("Scheme Details")
    if st.button("Back to Results"):
        navigate_to("Scheme Results")
    scheme = None
    if st.session_state.selected_scheme_id:
        scheme = next((s for s in st.session_state.results if s["id"] == st.session_state.selected_scheme_id), None)
    if not scheme:
        schemes = st.session_state.results or st.session_state.schemes
        scheme = st.selectbox("Select a scheme", schemes, format_func=lambda s: s["name"]) if schemes else None

    if scheme:
        st.subheader(scheme["name"])
        st.caption("This page is displayed in English; the official scheme name is preserved.")
        if scheme.get("verification_status") == "needs_official_verification":
            st.warning("Some scheme details or criteria need official verification. They are not used to declare definite eligibility.")
        st.write(scheme["summary"])
        st.markdown("<div class='official-links'>", unsafe_allow_html=True)
        link_left, link_right = st.columns(2)
        with link_left:
            st.link_button("Official scheme source", scheme["official_url"], use_container_width=True)
        with link_right:
            st.link_button("Official application / registration", scheme["application_url"], use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if "eligibility" in scheme:
            result = scheme["eligibility"]
            st.markdown(f"### Eligibility<br>{status_badge(result['status'])}", unsafe_allow_html=True)
            matched_col, failed_col, unknown_col = st.columns(3)
            detail_columns = [
                (matched_col, "Matched conditions", result["matched"]),
                (failed_col, "Failed conditions", result["failed"]),
                (unknown_col, "Unknown conditions", result["unknown"]),
            ]
            for column, label, items in detail_columns:
                with column:
                    st.markdown(f"**{label}**")
                    if not items:
                        st.caption("None")
                    for item in items:
                        st.write(f"- {item['evidence']}")

        benefits_col, documents_col = st.columns(2)
        with benefits_col:
            st.markdown("### Benefits")
            for benefit in scheme["benefits"]:
                st.write(f"- {benefit}")
        with documents_col:
            st.markdown("### Required documents")
            for document in scheme["documents"]:
                st.write(f"- {document}")
        st.markdown("### Application steps")
        for index, step in enumerate(scheme["application_steps"], 1):
            st.write(f"{index}. {step}")
        st.caption(scheme["source_note"])

elif page == "AI Assistant":
    st.title("AI Assistant")
    st.caption("Grounded explanations only. The eligibility decision remains deterministic.")

    if not st.session_state.results:
        st.info("Create a profile and view scheme results before asking the assistant.")
    else:
        scheme = st.selectbox("Scheme", st.session_state.results, format_func=lambda s: s["name"])
        question = st.text_area("Question", placeholder="Explain why this scheme is potentially eligible...")
        if st.button("Explain with evidence", type="primary"):
            response = explain_with_llm(scheme, scheme["eligibility"], question)
            st.markdown(response["text"])
            st.caption(f"Response mode: {response['mode']}")
