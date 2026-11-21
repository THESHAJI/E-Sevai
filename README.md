# E-Sevai AI

A working Streamlit MVP for discovering Indian government schemes across Central and selected State/UT coverage, with deterministic eligibility explanations.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit.

## Optional LLM

Copy `.env.example` to `.env` and set `OPENAI_API_KEY` if you want grounded LLM explanations.
The API key is read only from environment variables. Without a key or if the API fails, the app uses deterministic explanations.

For Streamlit Community Cloud, add this under **App settings → Secrets**:

```toml
OPENAI_API_KEY = "your-key-from-your-provider"
OPENAI_MODEL = "gpt-4o-mini"
```

The app also accepts the nested form:

```toml
[openai]
api_key = "your-key-from-your-provider"
model = "gpt-4o-mini"
```

Environment variables and Streamlit Secrets are optional. No key means deterministic explanations only.

## Modules

- `app.py`: Streamlit interface
- `data/schemes.json`: scheme records and configured eligibility rules
- `src/eligibility.py`: deterministic eligibility engine
- `src/scheme_service.py`: loading and search
- `src/validator.py`: Pydantic profile validation
- `src/ai_assistant.py`: grounded optional LLM output with fallback

## Eligibility transparency

The MVP never uses an LLM for decisions. A missing profile value produces an unknown condition and cannot count as satisfied. Matched, failed and unknown evidence is shown in results and details.

## Official sources

Official and application links are included for each record in `data/schemes.json`. Several benefit, document and eligibility fields are intentionally marked as subject to official rules where the source did not provide a simple verifiable local value.

## Coverage and localization

- Profile supports all 28 states and 8 Union Territories, native place and native/preferred language.
- Central schemes apply across India; State/UT schemes are automatically marked location-ineligible for residents elsewhere.
- The interface provides English, Hindi and Tamil navigation labels; detailed scheme content and eligibility explanations remain English.
- Scheme names, benefits and source links preserve their original English/official form when a reliable translation is unavailable.
- A source registry in `src/scheme_service.py` identifies Central and currently represented State/UT sources. The MVP does not crawl or claim exhaustive coverage.

## Tested functionality

- Profile submission and optional/blank fields
- Profile editing from results
- Central scheme matching across states
- State scheme location restrictions
- Unknown and unverified eligibility conditions
- Negative income and out-of-range age validation
- Missing API key and LLM hallucination fallback
- Home, Profile, Results, Details, Back navigation and sidebar navigation

Run automated tests with:

```bash
python -m unittest discover -s tests -v
```

## Honest limitations

- Scheme coverage is limited to 14 selected records.
- State/UT indexing is currently limited to Tamil Nadu, Maharashtra, Karnataka, Kerala and Delhi.
- Several criteria are marked for official verification and cannot produce a definite eligible or ineligible decision.
- Hindi and Tamil navigation labels are implemented; detailed scheme content remains English.
- Live external URLs should be re-checked before application because portals can change.
