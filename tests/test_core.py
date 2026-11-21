import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import requests

from streamlit.testing.v1 import AppTest

from pydantic import ValidationError

from src.validator import UserProfile
from src.scheme_service import load_schemes
from src.eligibility import evaluate_scheme, evaluate_schemes
from src.ai_assistant import explain_with_llm, get_api_key, get_model


class ProfileTests(unittest.TestCase):
    def test_missing_age_and_income_remain_none(self):
        profile = UserProfile()
        self.assertIsNone(profile.age)
        self.assertIsNone(profile.annual_income)

    def test_blank_optional_text_is_none(self):
        profile = UserProfile(district="   ", state="")
        self.assertIsNone(profile.district)
        self.assertIsNone(profile.state)

    def test_negative_income_is_invalid(self):
        with self.assertRaises(ValidationError):
            UserProfile(annual_income=-1)

    def test_negative_and_over_range_age_are_invalid(self):
        with self.assertRaises(ValidationError):
            UserProfile(age=-1)
        with self.assertRaises(ValidationError):
            UserProfile(age=121)

    def test_age_and_income_boundaries_are_accepted(self):
        self.assertEqual(UserProfile(age=0).age, 0)
        self.assertEqual(UserProfile(age=120).age, 120)
        self.assertEqual(UserProfile(annual_income=0).annual_income, 0)
        self.assertEqual(UserProfile(annual_income=100000000).annual_income, 100000000)


class EligibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemes = load_schemes()
        cls.by_id = {scheme["id"]: scheme for scheme in cls.schemes}

    def test_missing_age_is_unknown(self):
        profile = UserProfile(state="Tamil Nadu", age=None)
        scheme = self.by_id["nps"]
        result = evaluate_scheme(profile, scheme)
        self.assertEqual(result["status"], "Potentially Eligible")
        self.assertTrue(result["unknown"])

    def test_missing_income_is_unknown(self):
        profile = UserProfile(state="Tamil Nadu", annual_income=None)
        scheme = self.by_id["pmjay"]
        result = evaluate_scheme(profile, scheme)
        self.assertEqual(result["status"], "Potentially Eligible")
        self.assertTrue(any("income" in item["evidence"].lower() or "income" in item["label"].lower()
                            for item in result["unknown"]))

    def test_central_schemes_apply_across_states(self):
        for state in ("Bihar", "Tamil Nadu", "Goa", "Ladakh"):
            profile = UserProfile(state=state)
            pm_kisan = evaluate_scheme(profile, self.by_id["pm-kisan"])
            resident_location = pm_kisan["matched"] + pm_kisan["unknown"] + pm_kisan["failed"]
            self.assertFalse(any("resident location" in item["label"].lower() for item in resident_location))

    def test_state_schemes_restrict_other_states(self):
        tamil_profile = UserProfile(state="Tamil Nadu")
        maharashtra_profile = UserProfile(state="Maharashtra")
        tamil_result = evaluate_scheme(tamil_profile, self.by_id["tn-naan-mudhalvan"])
        self.assertNotIn("Resident location", [item["label"] for item in tamil_result["failed"]])
        self.assertIn("Resident location",
                      [item["label"] for item in evaluate_scheme(maharashtra_profile, self.by_id["tn-naan-mudhalvan"])["failed"]])

    def test_unverified_conditions_never_produce_definite_eligibility(self):
        profile = UserProfile(
            state="Karnataka",
            age=30,
            annual_income=50000,
            residence_type="Urban",
        )
        result = evaluate_scheme(profile, self.by_id["ka-gruha-jyoti"])
        self.assertEqual(result["status"], "Potentially Eligible")
        self.assertTrue(result["unknown"])

    def test_unsupported_state_has_no_local_index_and_central_schemes_remain(self):
        state = "Bihar"
        profile = UserProfile(state=state)
        indexed_states = {value for scheme in self.schemes for value in scheme["states"] if value != "All India"}
        self.assertNotIn(state, indexed_states)
        results = evaluate_schemes(profile, self.schemes)
        central = [scheme for scheme in results if scheme["states"] == ["All India"]]
        self.assertGreater(len(central), 0)

    def test_fourteen_scheme_records_keep_unique_ids_and_source_links(self):
        self.assertEqual(len(self.schemes), 14)
        self.assertEqual(len({scheme["id"] for scheme in self.schemes}), 14)
        for scheme in self.schemes:
            self.assertTrue(scheme["official_url"].startswith("https://"))
            self.assertTrue(scheme["application_url"].startswith("https://"))

    def test_scheme_level_unverified_record_never_returns_eligible_or_criterion_false_not_eligible(self):
        scheme = self.by_id["pmjay"]
        profile = UserProfile(
            state="Bihar",
            age=30,
            annual_income=10000000,
            bpl=False,
        )
        result = evaluate_scheme(profile, scheme)
        self.assertEqual(result["status"], "Potentially Eligible")
        self.assertTrue(any(item["label"] == "Official verification" for item in result["unknown"]))


class AiSafetyTests(unittest.TestCase):
    def setUp(self):
        self.scheme = load_schemes()[0]
        self.result = {
            "status": "Potentially Eligible",
            "matched": [],
            "failed": [],
            "unknown": [{"label": "Income", "status": "unknown", "evidence": "Income was not provided"}],
        }

    def test_environment_api_key_and_model_are_read(self):
        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"},
            clear=False,
        ):
            self.assertEqual(get_api_key(), "test-key")
            self.assertEqual(get_model(), "test-model")

    def test_missing_api_key_uses_deterministic_fallback(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            response = explain_with_llm(self.scheme, self.result)
        self.assertEqual(response["mode"], "deterministic")
        self.assertIn("Potentially Eligible", response["text"])

    def test_llm_response_with_invented_url_is_rejected(self):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Potentially eligible. Apply at https://fake.example"}}]
        }
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False), \
             patch("src.ai_assistant.requests.post", return_value=mock_response):
            response = explain_with_llm(self.scheme, self.result)
        self.assertEqual(response["mode"], "deterministic")

    def test_llm_timeout_uses_deterministic_fallback(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False), \
             patch("src.ai_assistant.requests.post", side_effect=requests.Timeout("timed out")):
            response = explain_with_llm(self.scheme, self.result)
        self.assertEqual(response["mode"], "deterministic")
        self.assertIn("Potentially Eligible", response["text"])

    def test_empty_llm_response_uses_deterministic_fallback(self):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"choices": [{"message": {"content": "   "}}]}
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False), \
             patch("src.ai_assistant.requests.post", return_value=mock_response):
            response = explain_with_llm(self.scheme, self.result)
        self.assertEqual(response["mode"], "deterministic")

    def test_contradictory_llm_status_is_rejected(self):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "This applicant is not eligible."}}]
        }
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False), \
             patch("src.ai_assistant.requests.post", return_value=mock_response):
            response = explain_with_llm(self.scheme, self.result)
        self.assertEqual(response["mode"], "deterministic")


class AppJourneyTests(unittest.TestCase):
    def test_sidebar_profile_submit_results_details_and_back(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path), default_timeout=20).run()
        self.assertEqual(len(app.exception), 0)

        app.radio[0].set_value("Profile").run()
        self.assertEqual([title.value for title in app.title], ["Your Profile"])
        app.form_submit_button[0].click().run()
        self.assertEqual([title.value for title in app.title], ["Scheme Results"])

        view_buttons = [button for button in app.button if "View details" in button.label]
        self.assertTrue(view_buttons)
        view_buttons[0].click().run()
        self.assertEqual([title.value for title in app.title], ["Scheme Details"])
        back_button = next(button for button in app.button if button.label == "Back to Results")
        back_button.click().run()
        self.assertEqual([title.value for title in app.title], ["Scheme Results"])
        self.assertEqual(len(app.exception), 0)

    def test_profile_edit_prefills_saved_values(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path), default_timeout=20).run()
        app.radio[0].set_value("Profile").run()

        age_input = next(widget for widget in app.number_input if widget.label == "Age (optional)")
        age_input.set_value(35)
        app.form_submit_button[0].click().run()

        edit_button = next(button for button in app.button if button.label == "Edit Profile")
        edit_button.click().run()
        age_input = next(widget for widget in app.number_input if widget.label == "Age (optional)")
        self.assertEqual(age_input.value, 35)


if __name__ == "__main__":
    unittest.main()
