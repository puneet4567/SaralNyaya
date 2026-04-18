from __future__ import annotations

import json
import os
import re
import uuid
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode
from wsgiref.simple_server import make_server

from portal import auth, database
from portal.features import (
    build_case_feature_graph,
    build_lawyer_feature_graph,
    extract_document_text,
    infer_legal_tags,
)
from portal.options import CASE_CATEGORIES, COURT_LEVEL_OPTIONS, ELIGIBILITY_OPTIONS
from portal.views import (
    render_access_denied,
    render_auth_page,
    render_case_form,
    render_dashboard,
    render_eligibility_guide,
    render_home,
    render_lawyer_directory,
    render_lawyer_form,
    render_my_assignments,
    render_my_cases,
    render_whatsapp_guide,
)


STATIC_DIR = Path(__file__).resolve().parent / "static"
BASE_DIR = Path(__file__).resolve().parent.parent


def upload_root() -> Path:
    configured = os.environ.get("LAW_PORTAL_UPLOAD_DIR")
    path = Path(configured) if configured else BASE_DIR / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_default_admin() -> None:
    admin_email = os.environ.get("LAW_PORTAL_ADMIN_EMAIL", "admin@nyayasetu.local")
    admin_password = os.environ.get("LAW_PORTAL_ADMIN_PASSWORD", "admin1234")
    admin_name = os.environ.get("LAW_PORTAL_ADMIN_NAME", "NyayaSetu Admin")
    if database.get_user_by_email(admin_email):
        return
    database.create_user(
        {
            "full_name": admin_name,
            "email": admin_email,
            "password_hash": auth.hash_password(admin_password),
            "role": "admin",
        }
    )


def read_request_body(environ: dict[str, Any]) -> bytes:
    content_length = int(environ.get("CONTENT_LENGTH") or 0)
    if content_length <= 0:
        return b""
    return environ["wsgi.input"].read(content_length)


def add_value(data: dict[str, Any], key: str, value: Any) -> None:
    if key not in data:
        data[key] = value
        return
    existing = data[key]
    if isinstance(existing, list):
        existing.append(value)
    else:
        data[key] = [existing, value]


def parse_multipart_form(
    content_type: str, raw_body: bytes
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    message = BytesParser(policy=default).parsebytes(
        (
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode(
                "utf-8"
            )
            + raw_body
        )
    )

    data: dict[str, Any] = {}
    files: list[dict[str, Any]] = []
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            if not payload and not filename:
                continue
            files.append(
                {
                    "field_name": name,
                    "filename": filename,
                    "content_type": part.get_content_type(),
                    "content": payload,
                }
            )
            continue

        charset = part.get_content_charset() or "utf-8"
        add_value(data, name, payload.decode(charset, errors="ignore"))
    return data, files


def parse_request_data(
    environ: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw_body = read_request_body(environ)
    content_type = environ.get("CONTENT_TYPE", "")

    if "application/json" in content_type:
        if not raw_body:
            return {}, []
        return json.loads(raw_body.decode("utf-8")), []

    if "multipart/form-data" in content_type:
        return parse_multipart_form(content_type, raw_body)

    parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    data: dict[str, Any] = {}
    for key, value in parsed.items():
        data[key] = value if len(value) > 1 else value[0]
    return data, []


def parse_query_params(environ: dict[str, Any]) -> dict[str, str]:
    parsed = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
    return {key: value[0] for key, value in parsed.items() if value}


def get_current_user(environ: dict[str, Any]) -> dict[str, Any] | None:
    cookies = auth.parse_cookie_header(environ.get("HTTP_COOKIE"))
    session_token = cookies.get(auth.SESSION_COOKIE_NAME)
    if not session_token:
        return None
    return database.get_user_by_session_token(session_token)


def response_headers(
    content_type: str, payload: bytes, extra_headers: list[tuple[str, str]] | None = None
) -> list[tuple[str, str]]:
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(payload))),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    return headers


def html_response(
    body: str,
    status: str = "200 OK",
    extra_headers: list[tuple[str, str]] | None = None,
) -> tuple[str, list[tuple[str, str]], list[bytes]]:
    payload = body.encode("utf-8")
    return (
        status,
        response_headers("text/html; charset=utf-8", payload, extra_headers),
        [payload],
    )


def json_response(
    data: dict[str, Any],
    status: str = "200 OK",
    extra_headers: list[tuple[str, str]] | None = None,
) -> tuple[str, list[tuple[str, str]], list[bytes]]:
    payload = json.dumps(data).encode("utf-8")
    return (
        status,
        response_headers("application/json; charset=utf-8", payload, extra_headers),
        [payload],
    )


def binary_response(
    payload: bytes,
    content_type: str,
    filename: str,
) -> tuple[str, list[tuple[str, str]], list[bytes]]:
    headers = response_headers(content_type, payload)
    headers.append(
        ("Content-Disposition", f'attachment; filename="{filename}"')
    )
    return ("200 OK", headers, [payload])


def redirect(
    location: str,
    extra_headers: list[tuple[str, str]] | None = None,
) -> tuple[str, list[tuple[str, str]], list[bytes]]:
    headers = [("Location", location), ("Content-Length", "0")]
    if extra_headers:
        headers.extend(extra_headers)
    return ("303 See Other", headers, [b""])


def serve_static(path: str) -> tuple[str, list[tuple[str, str]], list[bytes]]:
    file_path = STATIC_DIR / path.replace("/static/", "", 1)
    if not file_path.exists() or not file_path.is_file():
        return html_response("<h1>Not Found</h1>", "404 Not Found")

    content_type = "text/plain; charset=utf-8"
    if file_path.suffix == ".css":
        content_type = "text/css; charset=utf-8"

    payload = file_path.read_bytes()
    return ("200 OK", response_headers(content_type, payload), [payload])


def user_has_role(user: dict[str, Any] | None, *roles: str) -> bool:
    return bool(user and user.get("role") in roles)


def validate_case_form(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "full_name": "Full name is required.",
        "contact_phone": "A contact phone is required.",
        "state": "Please choose a state or union territory.",
        "applicant_category": "Please choose the applicant eligibility group or select not sure.",
        "case_category": "Please choose the type of legal issue.",
        "court_level": "Please choose where the matter currently sits.",
        "summary": "Please add a short summary of the legal problem.",
    }
    for field, message in required_fields.items():
        if not str(data.get(field, "")).strip():
            errors.append(message)
    if str(data.get("permission_to_share", "")).strip() not in {
        "yes",
        "no",
        "True",
        "False",
        "true",
        "false",
    }:
        errors.append("Please choose whether the case can be shared with lawyers.")
    return errors


def validate_lawyer_form(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "full_name": "Lawyer name is required.",
        "bar_council_id": "Enrollment number is required.",
        "bar_council_state": "Please choose the State Bar Council.",
        "email": "Email is required.",
        "phone": "Phone is required.",
        "past_case_history": "Please add a short past case history for matching.",
    }
    for field, message in required_fields.items():
        if not str(data.get(field, "")).strip():
            errors.append(message)
    if not database.parse_multi_value_field(data.get("states_served")):
        errors.append("Select at least one state served.")
    if not database.parse_multi_value_field(data.get("specialties")):
        errors.append("Select at least one specialty.")
    if not database.parse_multi_value_field(data.get("courts_of_practice")):
        errors.append("Select at least one court or forum of practice.")
    if not database.normalize_bool(data.get("declaration_accepted")):
        errors.append("Please accept the lawyer declaration before submitting the profile.")
    return errors


def validate_registration_form(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not str(data.get("full_name", "")).strip():
        errors.append("Full name is required.")
    email = str(data.get("email", "")).strip().lower()
    if not email or "@" not in email:
        errors.append("A valid email is required.")
    password = str(data.get("password", ""))
    confirm = str(data.get("confirm_password", ""))
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if password != confirm:
        errors.append("Password confirmation does not match.")
    if str(data.get("role", "")).strip() not in {"applicant", "lawyer"}:
        errors.append("Role must be applicant or lawyer.")
    if email and database.get_user_by_email(email):
        errors.append("An account already exists for that email.")
    return errors


def validate_login_form(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not str(data.get("email", "")).strip():
        errors.append("Email is required.")
    if not str(data.get("password", "")):
        errors.append("Password is required.")
    return errors


def build_case_payload(data: dict[str, Any], applicant_user_id: int | None = None) -> dict[str, Any]:
    return {
        "applicant_user_id": applicant_user_id,
        "full_name": data.get("full_name", ""),
        "contact_phone": data.get("contact_phone", ""),
        "whatsapp_number": data.get("whatsapp_number", ""),
        "state": data.get("state", ""),
        "district": data.get("district", ""),
        "applicant_category": data.get("applicant_category", ""),
        "case_category": data.get("case_category", ""),
        "court_level": data.get("court_level", ""),
        "preferred_language": data.get("preferred_language", ""),
        "urgency": data.get("urgency", "medium"),
        "income_band": data.get("income_band", ""),
        "preferred_channel": data.get("preferred_channel", "phone"),
        "summary": data.get("summary", ""),
        "permission_to_share": str(data.get("permission_to_share", "")).strip().lower()
        in {"yes", "true", "1"},
        "case_stage": data.get("case_stage", "intake_received"),
        "next_hearing_date": data.get("next_hearing_date", ""),
    }


def build_lawyer_payload(data: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "user_id": user["id"],
        "full_name": data.get("full_name", user["full_name"]),
        "bar_council_id": data.get("bar_council_id", ""),
        "bar_council_state": data.get("bar_council_state", ""),
        "email": data.get("email", user["email"]),
        "phone": data.get("phone", ""),
        "states_served": data.get("states_served", []),
        "specialties": data.get("specialties", []),
        "languages": data.get("languages", []),
        "courts_of_practice": data.get("courts_of_practice", []),
        "years_experience": data.get("years_experience", 0),
        "fee_model": data.get("fee_model", "pro_bono"),
        "bio": data.get("bio", ""),
        "past_case_history": data.get("past_case_history", ""),
        "verification_status": "self_attested",
        "declaration_accepted": data.get("declaration_accepted", ""),
        "is_accepting": str(data.get("is_accepting", "")).strip().lower() != "no",
    }
    payload["feature_graph"] = build_lawyer_feature_graph(payload)
    return payload


def prepare_uploaded_documents(
    uploaded_files: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prepared_documents: list[dict[str, Any]] = []
    for uploaded_file in uploaded_files:
        filename = str(uploaded_file.get("filename", "")).strip()
        content = uploaded_file.get("content", b"")
        if not filename or not content:
            continue
        extracted_text = extract_document_text(
            filename,
            str(uploaded_file.get("content_type", "")),
            content,
        )
        prepared_documents.append(
            {
                **uploaded_file,
                "extracted_text": extracted_text,
                "feature_tags": infer_legal_tags(f"{filename} {extracted_text[:4000]}"),
            }
        )
    return prepared_documents


def save_case_documents(case_id: int, uploaded_files: list[dict[str, Any]]) -> None:
    root = upload_root()
    for uploaded_file in uploaded_files:
        suffix = Path(str(uploaded_file["filename"])).suffix
        stored_filename = f"{case_id}-{uuid.uuid4().hex}{suffix}"
        (root / stored_filename).write_bytes(uploaded_file["content"])
        database.create_case_document(
            {
                "case_id": case_id,
                "original_filename": uploaded_file["filename"],
                "stored_filename": stored_filename,
                "content_type": uploaded_file.get("content_type", ""),
                "extracted_text": uploaded_file.get("extracted_text", ""),
                "feature_tags": uploaded_file.get("feature_tags", []),
            }
        )


def attach_case_documents(cases: list[dict[str, Any]]) -> None:
    case_ids = [int(case["id"]) for case in cases]
    grouped_documents = database.list_case_documents(case_ids)
    for case in cases:
        case["documents"] = grouped_documents.get(int(case["id"]), [])


def auto_assign_case_if_possible(case_id: int) -> dict[str, Any] | None:
    case = database.get_case_by_id(case_id)
    if not case or not case.get("permission_to_share"):
        return None

    lawyers = database.list_lawyers(only_accepting=True)
    matches = database.match_lawyers_for_case(case, lawyers)
    if not matches:
        return None

    best_match = matches[0]
    database.assign_lawyer(case_id, int(best_match["lawyer"]["id"]))
    return best_match


def build_dashboard_html(
    query_params: dict[str, str],
    user: dict[str, Any],
    success_messages: list[str] | None = None,
) -> str:
    state = query_params.get("state", "").strip()
    case_category = query_params.get("case_category", "").strip()
    court_level = query_params.get("court_level", "").strip()
    cases = database.list_cases(
        state=state or None,
        case_category=case_category or None,
        court_level=court_level or None,
    )
    attach_case_documents(cases)
    all_lawyers = database.list_lawyers(
        state=state or None,
        court_level=court_level or None,
    )
    for case in cases:
        case["matches"] = database.match_lawyers_for_case(case, all_lawyers)
    stats = database.get_overview_stats()
    return render_dashboard(
        stats=stats,
        cases=cases,
        lawyers=all_lawyers,
        selected_state=state,
        selected_category=case_category,
        selected_court_level=court_level,
        success_messages=success_messages,
        user=user,
    )


def build_lawyer_directory_html(
    query_params: dict[str, str],
    user: dict[str, Any] | None = None,
) -> str:
    state = query_params.get("state", "").strip()
    bar_council_state = query_params.get("bar_council_state", "").strip()
    case_category = query_params.get("case_category", "").strip()
    court_level = query_params.get("court_level", "").strip()
    query = query_params.get("q", "").strip()
    lawyers = database.list_lawyers(
        state=state or None,
        court_level=court_level or None,
        case_category=case_category or None,
        query=query or None,
        bar_council_state=bar_council_state or None,
    )
    return render_lawyer_directory(
        lawyers=lawyers,
        selected_state=state,
        selected_bar_council_state=bar_council_state,
        selected_category=case_category,
        selected_court_level=court_level,
        query=query,
        user=user,
    )


def applicant_can_access_case(user: dict[str, Any], case: dict[str, Any]) -> bool:
    return case.get("applicant_user_id") == user["id"]


def lawyer_can_access_case(user: dict[str, Any], case: dict[str, Any]) -> bool:
    lawyer_profile = database.get_lawyer_by_user_id(int(user["id"]))
    if not lawyer_profile:
        return False
    return case.get("assigned_lawyer_id") == lawyer_profile["id"]


def can_access_case_documents(user: dict[str, Any] | None, case: dict[str, Any]) -> bool:
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    if user.get("role") == "applicant":
        return applicant_can_access_case(user, case)
    if user.get("role") == "lawyer":
        return lawyer_can_access_case(user, case)
    return False


def login_user_redirect(user: dict[str, Any], next_path: str = "") -> str:
    if next_path:
        return next_path
    if user["role"] == "applicant":
        return "/my-cases"
    if user["role"] == "lawyer":
        return "/my-assignments"
    return "/dashboard"


def handle_request(
    environ: dict[str, Any]
) -> tuple[str, list[tuple[str, str]], list[bytes]]:
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/")
    current_user = get_current_user(environ)

    if path.startswith("/static/"):
        return serve_static(path)

    query_params = parse_query_params(environ)

    if method == "GET" and path == "/":
        return html_response(render_home(database.get_overview_stats(), user=current_user))

    if method == "GET" and path == "/eligibility":
        return html_response(render_eligibility_guide(user=current_user))

    if method == "GET" and path == "/register":
        role = query_params.get("role", "applicant")
        return html_response(
            render_auth_page(
                mode="register",
                role=role if role in {"applicant", "lawyer"} else "applicant",
                next_path=query_params.get("next", ""),
                user=current_user,
            )
        )

    if method == "POST" and path == "/register":
        form_data, _uploaded_files = parse_request_data(environ)
        errors = validate_registration_form(form_data)
        if errors:
            return html_response(
                render_auth_page(
                    mode="register",
                    role=str(form_data.get("role", "applicant")),
                    next_path=str(form_data.get("next", "")),
                    values=form_data,
                    errors=errors,
                    user=current_user,
                ),
                "422 Unprocessable Entity",
            )
        user_id = database.create_user(
            {
                "full_name": form_data.get("full_name", ""),
                "email": form_data.get("email", ""),
                "password_hash": auth.hash_password(str(form_data.get("password", ""))),
                "role": form_data.get("role", "applicant"),
            }
        )
        user = database.get_user_by_id(user_id)
        session_token = auth.new_session_token()
        database.create_session(user_id, session_token)
        return redirect(
            login_user_redirect(user, str(form_data.get("next", ""))),
            extra_headers=[("Set-Cookie", auth.build_session_cookie(session_token))],
        )

    if method == "GET" and path == "/login":
        return html_response(
            render_auth_page(
                mode="login",
                role="applicant",
                next_path=query_params.get("next", ""),
                user=current_user,
            )
        )

    if method == "POST" and path == "/login":
        form_data, _uploaded_files = parse_request_data(environ)
        errors = validate_login_form(form_data)
        user = database.get_user_by_email(str(form_data.get("email", "")).strip().lower())
        if not errors and (
            not user
            or not auth.verify_password(str(form_data.get("password", "")), user["password_hash"])
        ):
            errors.append("Email or password is incorrect.")
        if errors:
            return html_response(
                render_auth_page(
                    mode="login",
                    role="applicant",
                    next_path=str(form_data.get("next", "")),
                    values=form_data,
                    errors=errors,
                    user=current_user,
                ),
                "422 Unprocessable Entity",
            )
        session_token = auth.new_session_token()
        database.create_session(int(user["id"]), session_token)
        return redirect(
            login_user_redirect(user, str(form_data.get("next", ""))),
            extra_headers=[("Set-Cookie", auth.build_session_cookie(session_token))],
        )

    if method == "GET" and path == "/logout":
        cookies = auth.parse_cookie_header(environ.get("HTTP_COOKIE"))
        session_token = cookies.get(auth.SESSION_COOKIE_NAME)
        if session_token:
            database.delete_session(session_token)
        return redirect(
            "/",
            extra_headers=[("Set-Cookie", auth.build_clear_session_cookie())],
        )

    if method == "GET" and path == "/intake":
        if not user_has_role(current_user, "applicant", "admin"):
            return redirect("/register?role=applicant&next=/intake")
        submitted_case_id = (
            int(query_params["id"])
            if query_params.get("submitted") == "1" and query_params.get("id")
            else None
        )
        return html_response(
            render_case_form(
                submitted_case_id=submitted_case_id,
                auto_matched=query_params.get("auto_matched") == "1",
                user=current_user,
            )
        )

    if method == "POST" and path == "/intake":
        if not user_has_role(current_user, "applicant", "admin"):
            return redirect("/register?role=applicant&next=/intake")
        form_data, uploaded_files = parse_request_data(environ)
        errors = validate_case_form(form_data)
        if errors:
            return html_response(
                render_case_form(values=form_data, errors=errors, user=current_user),
                "422 Unprocessable Entity",
            )
        prepared_documents = prepare_uploaded_documents(uploaded_files)
        case_payload = build_case_payload(
            form_data,
            applicant_user_id=int(current_user["id"]) if current_user else None,
        )
        case_payload["feature_graph"] = build_case_feature_graph(
            case_payload,
            [document.get("extracted_text", "") for document in prepared_documents],
        )
        case_id = database.create_case(case_payload, source="web")
        save_case_documents(case_id, prepared_documents)
        auto_match = auto_assign_case_if_possible(case_id)
        redirect_query = {"submitted": "1", "id": str(case_id)}
        if auto_match:
            redirect_query["auto_matched"] = "1"
        return redirect("/intake?" + urlencode(redirect_query))

    if method == "GET" and path == "/my-cases":
        if not user_has_role(current_user, "applicant"):
            return redirect("/login?next=/my-cases")
        cases = database.list_cases(applicant_user_id=int(current_user["id"]))
        attach_case_documents(cases)
        return html_response(render_my_cases(cases=cases, user=current_user))

    if method == "GET" and path == "/lawyers":
        return html_response(build_lawyer_directory_html(query_params, user=current_user))

    if method == "GET" and path == "/lawyers/onboard":
        if not user_has_role(current_user, "lawyer", "admin"):
            return redirect("/register?role=lawyer&next=/lawyers/onboard")
        submitted_lawyer_id = (
            int(query_params["id"])
            if query_params.get("submitted") == "1" and query_params.get("id")
            else None
        )
        existing_profile = database.get_lawyer_by_user_id(int(current_user["id"]))
        return html_response(
            render_lawyer_form(
                values=existing_profile or {},
                submitted_lawyer_id=submitted_lawyer_id,
                user=current_user,
            )
        )

    if method == "POST" and path == "/lawyers/onboard":
        if not user_has_role(current_user, "lawyer", "admin"):
            return redirect("/register?role=lawyer&next=/lawyers/onboard")
        form_data, _uploaded_files = parse_request_data(environ)
        errors = validate_lawyer_form(form_data)
        if errors:
            return html_response(
                render_lawyer_form(values=form_data, errors=errors, user=current_user),
                "422 Unprocessable Entity",
            )
        lawyer_id = database.save_lawyer_profile(build_lawyer_payload(form_data, current_user))
        return redirect(f"/lawyers/onboard?submitted=1&id={lawyer_id}")

    if method == "GET" and path == "/my-assignments":
        if not user_has_role(current_user, "lawyer"):
            return redirect("/login?next=/my-assignments")
        lawyer_profile = database.get_lawyer_by_user_id(int(current_user["id"]))
        cases = database.list_cases(assigned_lawyer_user_id=int(current_user["id"]))
        attach_case_documents(cases)
        success_messages = (
            [f"Progress updated for case #{query_params['progress']}."]
            if query_params.get("progress")
            else None
        )
        return html_response(
            render_my_assignments(
                cases=cases,
                user=current_user,
                lawyer_profile=lawyer_profile,
                success_messages=success_messages,
            )
        )

    if method == "GET" and path == "/dashboard":
        if not user_has_role(current_user, "admin"):
            return redirect("/login?next=/dashboard")
        success_messages: list[str] = []
        if query_params.get("assigned"):
            success_messages.append(f"Lawyer assigned to case #{query_params['assigned']}.")
        if query_params.get("progress"):
            success_messages.append(f"Progress updated for case #{query_params['progress']}.")
        return html_response(
            build_dashboard_html(
                query_params,
                user=current_user,
                success_messages=success_messages or None,
            )
        )

    if method == "POST" and path == "/assign":
        if not user_has_role(current_user, "admin"):
            return html_response(
                render_access_denied(
                    "Admin access required",
                    "Only admins can assign lawyers to cases.",
                    user=current_user,
                ),
                "403 Forbidden",
            )
        form_data, _uploaded_files = parse_request_data(environ)
        case_id = int(str(form_data.get("case_id", "")).strip())
        lawyer_id = int(str(form_data.get("lawyer_id", "0")).strip() or "0")
        if lawyer_id <= 0:
            return redirect("/dashboard")
        database.assign_lawyer(case_id, lawyer_id)
        query_parts = {"assigned": case_id}
        for key in ("state", "case_category", "court_level"):
            value = str(form_data.get(key, "")).strip()
            if value:
                query_parts[key] = value
        return redirect("/dashboard?" + urlencode(query_parts))

    if method == "POST" and path == "/progress":
        if not current_user:
            return redirect("/login?next=/my-assignments")
        form_data, _uploaded_files = parse_request_data(environ)
        case_id = int(str(form_data.get("case_id", "")).strip())
        case = database.get_case_by_id(case_id)
        if not case:
            return html_response("<h1>Not Found</h1>", "404 Not Found")
        is_admin = user_has_role(current_user, "admin")
        is_assigned_lawyer = user_has_role(current_user, "lawyer") and lawyer_can_access_case(
            current_user, case
        )
        if not (is_admin or is_assigned_lawyer):
            return html_response(
                render_access_denied(
                    "Access denied",
                    "You can update progress only for cases you are allowed to manage.",
                    user=current_user,
                ),
                "403 Forbidden",
            )
        database.update_case_progress(
            case_id=case_id,
            case_stage=str(form_data.get("case_stage", "intake_received")),
            next_hearing_date=str(form_data.get("next_hearing_date", "")),
        )
        origin = str(form_data.get("origin", "dashboard"))
        if origin == "assignments":
            return redirect(f"/my-assignments?progress={case_id}")
        query_parts = {"progress": case_id}
        for key in ("state", "case_category", "court_level"):
            value = str(form_data.get(key, "")).strip()
            if value:
                query_parts[key] = value
        return redirect("/dashboard?" + urlencode(query_parts))

    if method == "GET" and re.fullmatch(r"/documents/\d+", path):
        document_id = int(path.rsplit("/", 1)[-1])
        if not current_user:
            return redirect(f"/login?next={path}")
        document = database.get_case_document(document_id)
        if not document:
            return html_response("<h1>Not Found</h1>", "404 Not Found")
        case = database.get_case_by_id(int(document["case_id"]))
        if not case or not can_access_case_documents(current_user, case):
            return html_response(
                render_access_denied(
                    "Document access denied",
                    "You are not allowed to view this document.",
                    user=current_user,
                ),
                "403 Forbidden",
            )
        file_path = upload_root() / str(document["stored_filename"])
        if not file_path.exists():
            return html_response("<h1>Not Found</h1>", "404 Not Found")
        return binary_response(
            file_path.read_bytes(),
            str(document.get("content_type") or "application/octet-stream"),
            str(document["original_filename"]),
        )

    if method == "GET" and path == "/whatsapp":
        return html_response(render_whatsapp_guide(user=current_user))

    if method == "POST" and path == "/api/whatsapp/intake":
        payload, _uploaded_files = parse_request_data(environ)
        normalized_payload = {
            **payload,
            "permission_to_share": payload.get("permission_to_share", "true"),
            "applicant_category": payload.get("applicant_category", "not_sure"),
            "court_level": payload.get("court_level", "pre_litigation"),
        }
        errors = validate_case_form(normalized_payload)
        if errors:
            return json_response({"ok": False, "errors": errors}, "422 Unprocessable Entity")
        case_payload = build_case_payload(normalized_payload)
        case_payload["feature_graph"] = build_case_feature_graph(case_payload, [])
        case_id = database.create_case(case_payload, source="whatsapp")
        auto_match = auto_assign_case_if_possible(case_id)
        return json_response(
            {
                "ok": True,
                "case_id": case_id,
                "auto_matched": bool(auto_match),
                "matched_lawyer_id": auto_match["lawyer"]["id"] if auto_match else None,
            },
            "201 Created",
        )

    if method == "GET" and path == "/health":
        return json_response(
            {
                "ok": True,
                "categories": CASE_CATEGORIES,
                "eligibility_categories": [value for value, _ in ELIGIBILITY_OPTIONS],
                "court_levels": [value for value, _ in COURT_LEVEL_OPTIONS],
                "secure_document_access": True,
            }
        )

    return html_response("<h1>Not Found</h1>", "404 Not Found")


def application(environ: dict[str, Any], start_response: Any) -> list[bytes]:
    try:
        status, headers, body = handle_request(environ)
    except Exception as exc:  # pragma: no cover - local debugging fallback
        status, headers, body = html_response(
            f"<h1>Server error</h1><pre>{exc!s}</pre>",
            "500 Internal Server Error",
        )

    start_response(status, headers)
    return body


def run_dev_server() -> None:
    database.init_db()
    ensure_default_admin()
    host = os.environ.get("LAW_PORTAL_HOST", "127.0.0.1")
    port = int(os.environ.get("LAW_PORTAL_PORT", "8000"))
    with make_server(host, port, application) as server:
        print(f"NyayaSetu running on http://{host}:{port}")
        server.serve_forever()
