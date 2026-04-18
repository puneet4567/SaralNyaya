from __future__ import annotations

import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from portal import auth, database
from portal.features import build_lawyer_feature_graph
from portal.server import application


def build_multipart_body(
    fields: dict[str, object],
    files: list[tuple[str, str, str, bytes]],
    boundary: str = "----CodexBoundary123456",
) -> tuple[bytes, str]:
    body = bytearray()

    for key, value in fields.items():
        values = value if isinstance(value, list) else [value]
        for item in values:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8")
            )
            body.extend(str(item).encode("utf-8"))
            body.extend(b"\r\n")

    for field_name, filename, content_type, content in files:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{field_name}"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


class PortalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["LAW_PORTAL_DB_PATH"] = str(Path(self.tempdir.name) / "portal.db")
        os.environ["LAW_PORTAL_UPLOAD_DIR"] = str(Path(self.tempdir.name) / "uploads")
        database.init_db()

    def tearDown(self) -> None:
        os.environ.pop("LAW_PORTAL_DB_PATH", None)
        os.environ.pop("LAW_PORTAL_UPLOAD_DIR", None)
        self.tempdir.cleanup()

    def call_app(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        content_type: str = "application/x-www-form-urlencoded",
        query_string: str = "",
        cookie: str = "",
    ) -> tuple[str, list[tuple[str, str]], bytes]:
        status_holder: list[str] = []
        headers_holder: list[list[tuple[str, str]]] = []

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            status_holder.append(status)
            headers_holder.append(headers)

        result = application(
            {
                "REQUEST_METHOD": method,
                "PATH_INFO": path,
                "QUERY_STRING": query_string,
                "CONTENT_TYPE": content_type,
                "CONTENT_LENGTH": str(len(body)),
                "HTTP_COOKIE": cookie,
                "wsgi.input": BytesIO(body),
            },
            start_response,
        )
        return status_holder[0], headers_holder[0], b"".join(result)

    def create_user(self, full_name: str, email: str, role: str) -> dict[str, object]:
        user_id = database.create_user(
            {
                "full_name": full_name,
                "email": email,
                "password_hash": auth.hash_password("password123"),
                "role": role,
            }
        )
        return database.get_user_by_id(user_id)

    def session_cookie_for(self, user: dict[str, object]) -> str:
        token = auth.new_session_token()
        database.create_session(int(user["id"]), token)
        return f"{auth.SESSION_COOKIE_NAME}={token}"

    def create_lawyer_profile(
        self,
        user: dict[str, object],
        accepting: bool = True,
        **overrides: object,
    ) -> int:
        payload = {
            "user_id": user["id"],
            "full_name": user["full_name"],
            "bar_council_id": f"{user['id']}-ENROLL",
            "bar_council_state": "Karnataka",
            "email": user["email"],
            "phone": "9876500000",
            "states_served": ["Karnataka"],
            "specialties": ["Labour / wage issue"],
            "languages": ["English", "Kannada"],
            "courts_of_practice": ["tribunal"],
            "years_experience": 7,
            "fee_model": "low_bono",
            "bio": "Supports labour disputes and salary non-payment matters.",
            "past_case_history": "Handled wage disputes, termination matters, and labour tribunal hearings.",
            "declaration_accepted": True,
            "is_accepting": accepting,
            "verification_status": "self_attested",
        }
        payload.update(overrides)
        payload["feature_graph"] = build_lawyer_feature_graph(payload)
        return database.save_lawyer_profile(
            payload
        )

    def submit_case_as_applicant(self, applicant_cookie: str) -> int:
        fields = {
            "full_name": "Asha Devi",
            "contact_phone": "9876543210",
            "whatsapp_number": "9876543210",
            "state": "Karnataka",
            "district": "Bengaluru Urban",
            "applicant_category": "low_income",
            "case_category": "Labour / wage issue",
            "court_level": "tribunal",
            "preferred_language": "English",
            "urgency": "high",
            "income_band": "Below Rs. 1.5 lakh / year",
            "preferred_channel": "whatsapp",
            "summary": "My salary has not been paid for three months after termination.",
            "permission_to_share": "yes",
            "next_hearing_date": "",
        }
        files = [
            (
                "documents",
                "notice.txt",
                "text/plain",
                b"Salary not paid. Employer issued termination letter. Wages pending.",
            )
        ]
        body, content_type = build_multipart_body(fields, files)
        status, _headers, _response_body = self.call_app(
            "POST",
            "/intake",
            body=body,
            content_type=content_type,
            cookie=applicant_cookie,
        )
        self.assertEqual(status, "303 See Other")
        return int(database.list_cases()[0]["id"])

    def test_homepage_renders(self) -> None:
        status, _headers, body = self.call_app("GET", "/")

        self.assertEqual(status, "200 OK")
        self.assertIn(b"SaralNyaya", body)
        self.assertIn(b"secure", body.lower())

    def test_dashboard_requires_login(self) -> None:
        status, headers, _body = self.call_app("GET", "/dashboard")

        self.assertEqual(status, "303 See Other")
        self.assertIn(("/dashboard" in dict(headers).get("Location", "")), [True])

    def test_lawyer_profile_persists_past_case_history(self) -> None:
        lawyer_user = self.create_user("Adv. Arjun Rao", "arjun@example.com", "lawyer")
        cookie = self.session_cookie_for(lawyer_user)
        body = urlencode_form(
            {
                "full_name": "Adv. Arjun Rao",
                "bar_council_id": "KA-1234",
                "bar_council_state": "Karnataka",
                "email": "arjun@example.com",
                "phone": "9876500000",
                "states_served": ["Karnataka"],
                "specialties": ["Labour / wage issue"],
                "languages": ["English", "Kannada"],
                "courts_of_practice": ["tribunal"],
                "years_experience": "7",
                "fee_model": "low_bono",
                "bio": "Supports labour disputes.",
                "past_case_history": "Handled salary non-payment matters and tribunal hearings.",
                "is_accepting": "yes",
                "declaration_accepted": "yes",
            }
        )

        status, _headers, _response_body = self.call_app(
            "POST",
            "/lawyers/onboard",
            body=body,
            cookie=cookie,
        )

        self.assertEqual(status, "303 See Other")
        lawyer_profile = database.get_lawyer_by_user_id(int(lawyer_user["id"]))
        self.assertIn("tribunal", lawyer_profile["feature_graph"]["keywords"])
        self.assertIn("wage", " ".join(lawyer_profile["feature_graph"]["past_case_keywords"]))

    def test_applicant_can_download_own_document(self) -> None:
        applicant = self.create_user("Asha Devi", "asha@example.com", "applicant")
        applicant_cookie = self.session_cookie_for(applicant)
        case_id = self.submit_case_as_applicant(applicant_cookie)

        documents = database.list_case_documents([case_id])[case_id]
        document_id = int(documents[0]["id"])

        status, _headers, body = self.call_app(
            "GET",
            f"/documents/{document_id}",
            cookie=applicant_cookie,
        )

        self.assertEqual(status, "200 OK")
        self.assertIn(b"Wages pending", body)

    def test_case_submission_auto_matches_best_lawyer_using_past_history(self) -> None:
        wage_lawyer_user = self.create_user(
            "Adv. Arjun Rao",
            "arjun@example.com",
            "lawyer",
        )
        property_lawyer_user = self.create_user(
            "Adv. Meera Sharma",
            "meera@example.com",
            "lawyer",
        )
        wage_lawyer_id = self.create_lawyer_profile(
            wage_lawyer_user,
            past_case_history="Handled salary non-payment, wage recovery, and termination hearings before labour tribunals.",
            years_experience=8,
        )
        self.create_lawyer_profile(
            property_lawyer_user,
            specialties=["Property dispute / land record"],
            bio="Supports partition and land mutation matters.",
            past_case_history="Handled partition suits and land mutation disputes.",
            courts_of_practice=["district_court"],
            languages=["English"],
            years_experience=12,
        )

        applicant = self.create_user("Asha Devi", "asha@example.com", "applicant")
        applicant_cookie = self.session_cookie_for(applicant)
        case_id = self.submit_case_as_applicant(applicant_cookie)

        case_record = database.get_case_by_id(case_id)

        self.assertEqual(case_record["assigned_lawyer_id"], wage_lawyer_id)
        self.assertEqual(case_record["case_stage"], "lawyer_matched")

    def test_other_applicant_cannot_download_document(self) -> None:
        applicant = self.create_user("Asha Devi", "asha@example.com", "applicant")
        applicant_cookie = self.session_cookie_for(applicant)
        case_id = self.submit_case_as_applicant(applicant_cookie)

        other_applicant = self.create_user("Rani", "rani@example.com", "applicant")
        other_cookie = self.session_cookie_for(other_applicant)
        document_id = int(database.list_case_documents([case_id])[case_id][0]["id"])

        status, _headers, body = self.call_app(
            "GET",
            f"/documents/{document_id}",
            cookie=other_cookie,
        )

        self.assertEqual(status, "403 Forbidden")
        self.assertIn(b"Document access denied", body)

    def test_assigned_lawyer_can_access_document_but_unassigned_cannot(self) -> None:
        applicant = self.create_user("Asha Devi", "asha@example.com", "applicant")
        applicant_cookie = self.session_cookie_for(applicant)
        case_id = self.submit_case_as_applicant(applicant_cookie)

        assigned_lawyer_user = self.create_user("Adv. Arjun Rao", "arjun@example.com", "lawyer")
        other_lawyer_user = self.create_user("Adv. Meera Sharma", "meera@example.com", "lawyer")
        assigned_lawyer_id = self.create_lawyer_profile(assigned_lawyer_user)
        self.create_lawyer_profile(other_lawyer_user)

        database.assign_lawyer(case_id, assigned_lawyer_id)
        document_id = int(database.list_case_documents([case_id])[case_id][0]["id"])

        assigned_status, _headers, assigned_body = self.call_app(
            "GET",
            f"/documents/{document_id}",
            cookie=self.session_cookie_for(assigned_lawyer_user),
        )
        other_status, _headers, other_body = self.call_app(
            "GET",
            f"/documents/{document_id}",
            cookie=self.session_cookie_for(other_lawyer_user),
        )

        self.assertEqual(assigned_status, "200 OK")
        self.assertIn(b"Wages pending", assigned_body)
        self.assertEqual(other_status, "403 Forbidden")
        self.assertIn(b"Document access denied", other_body)

    def test_public_lawyer_directory_still_renders(self) -> None:
        lawyer_user = self.create_user("Adv. Arjun Rao", "arjun@example.com", "lawyer")
        self.create_lawyer_profile(lawyer_user)

        status, _headers, body = self.call_app("GET", "/lawyers")

        self.assertEqual(status, "200 OK")
        self.assertIn(b"Adv. Arjun Rao", body)
        self.assertIn(b"Lawyer directory", body)

    def test_whatsapp_intake_endpoint_creates_case(self) -> None:
        payload = {
            "full_name": "Asha Devi",
            "contact_phone": "9876543210",
            "whatsapp_number": "9876543210",
            "state": "Delhi",
            "district": "North Delhi",
            "applicant_category": "low_income",
            "case_category": "Labour / wage issue",
            "court_level": "pre_litigation",
            "preferred_language": "Hindi",
            "urgency": "high",
            "income_band": "Below Rs. 1.5 lakh / year",
            "preferred_channel": "whatsapp",
            "summary": "Salary for the last three months has not been paid.",
            "permission_to_share": True,
        }

        status, _headers, body = self.call_app(
            "POST",
            "/api/whatsapp/intake",
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )

        self.assertEqual(status, "201 Created")
        self.assertIn(b'"ok": true', body)
        self.assertIn(b'"auto_matched": false', body)
        self.assertEqual(len(database.list_cases()), 1)


def urlencode_form(data: dict[str, object]) -> bytes:
    from urllib.parse import urlencode

    return urlencode(data, doseq=True).encode("utf-8")


if __name__ == "__main__":
    unittest.main()
