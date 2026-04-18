from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from portal.features import score_feature_graph_overlap
from portal.options import COURT_LEVEL_OPTIONS


BASE_DIR = Path(__file__).resolve().parent.parent
COURT_LEVEL_LABELS = dict(COURT_LEVEL_OPTIONS)


def database_path() -> Path:
    configured = os.environ.get("LAW_PORTAL_DB_PATH")
    if configured:
        return Path(configured)
    return BASE_DIR / "data" / "portal.db"


def get_connection() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_columns(
    connection: sqlite3.Connection, table_name: str, column_specs: dict[str, str]
) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_spec in column_specs.items():
        if column_name in existing_columns:
            continue
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_spec}"
        )


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS lawyers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                full_name TEXT NOT NULL,
                bar_council_id TEXT NOT NULL,
                bar_council_state TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                states_served TEXT NOT NULL DEFAULT '[]',
                specialties TEXT NOT NULL DEFAULT '[]',
                languages TEXT NOT NULL DEFAULT '[]',
                courts_of_practice TEXT NOT NULL DEFAULT '[]',
                years_experience INTEGER NOT NULL DEFAULT 0,
                fee_model TEXT NOT NULL DEFAULT 'pro_bono',
                bio TEXT NOT NULL DEFAULT '',
                past_case_history TEXT NOT NULL DEFAULT '',
                feature_graph TEXT NOT NULL DEFAULT '{}',
                verification_status TEXT NOT NULL DEFAULT 'self_attested',
                declaration_accepted INTEGER NOT NULL DEFAULT 0,
                is_accepting INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                applicant_user_id INTEGER,
                full_name TEXT NOT NULL,
                contact_phone TEXT NOT NULL,
                whatsapp_number TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL,
                district TEXT NOT NULL DEFAULT '',
                applicant_category TEXT NOT NULL DEFAULT '',
                case_category TEXT NOT NULL,
                court_level TEXT NOT NULL DEFAULT '',
                preferred_language TEXT NOT NULL DEFAULT '',
                urgency TEXT NOT NULL DEFAULT 'medium',
                income_band TEXT NOT NULL DEFAULT '',
                preferred_channel TEXT NOT NULL DEFAULT 'phone',
                summary TEXT NOT NULL,
                permission_to_share INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'web',
                status TEXT NOT NULL DEFAULT 'new',
                case_stage TEXT NOT NULL DEFAULT 'intake_received',
                next_hearing_date TEXT NOT NULL DEFAULT '',
                feature_graph TEXT NOT NULL DEFAULT '{}',
                assigned_lawyer_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (applicant_user_id) REFERENCES users(id),
                FOREIGN KEY (assigned_lawyer_id) REFERENCES lawyers(id)
            );

            CREATE TABLE IF NOT EXISTS case_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT '',
                extracted_text TEXT NOT NULL DEFAULT '',
                feature_tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            );
            """
        )

        ensure_columns(
            connection,
            "lawyers",
            {
                "user_id": "INTEGER",
                "bar_council_state": "TEXT NOT NULL DEFAULT ''",
                "courts_of_practice": "TEXT NOT NULL DEFAULT '[]'",
                "past_case_history": "TEXT NOT NULL DEFAULT ''",
                "feature_graph": "TEXT NOT NULL DEFAULT '{}'",
                "verification_status": "TEXT NOT NULL DEFAULT 'self_attested'",
                "declaration_accepted": "INTEGER NOT NULL DEFAULT 0",
            },
        )
        ensure_columns(
            connection,
            "cases",
            {
                "applicant_user_id": "INTEGER",
                "applicant_category": "TEXT NOT NULL DEFAULT ''",
                "court_level": "TEXT NOT NULL DEFAULT ''",
                "case_stage": "TEXT NOT NULL DEFAULT 'intake_received'",
                "next_hearing_date": "TEXT NOT NULL DEFAULT ''",
                "feature_graph": "TEXT NOT NULL DEFAULT '{}'",
            },
        )

        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_lawyers_user_id ON lawyers(user_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_cases_applicant_user_id ON cases(applicant_user_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)"
        )


def parse_multi_value_field(value: Any) -> list[str]:
    if value is None:
        return []

    candidates: list[Any]
    if isinstance(value, list):
        candidates = value
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                candidates = parsed
            else:
                candidates = re.split(r"[,|\n]+", stripped)
        else:
            candidates = re.split(r"[,|\n]+", stripped)
    else:
        candidates = [value]

    values: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        item = str(candidate).strip()
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(item)
    return values


def serialize_multi_value_field(value: Any) -> str:
    return json.dumps(parse_multi_value_field(value))


def parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def serialize_json_object(value: Any) -> str:
    return json.dumps(parse_json_object(value))


def normalize_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def normalize_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def hydrate_user(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def hydrate_lawyer(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    record["states_served"] = parse_multi_value_field(record.get("states_served"))
    record["specialties"] = parse_multi_value_field(record.get("specialties"))
    record["languages"] = parse_multi_value_field(record.get("languages"))
    record["courts_of_practice"] = parse_multi_value_field(
        record.get("courts_of_practice")
    )
    record["feature_graph"] = parse_json_object(record.get("feature_graph"))
    record["is_accepting"] = bool(record.get("is_accepting"))
    record["declaration_accepted"] = bool(record.get("declaration_accepted"))
    record["years_experience"] = normalize_int(record.get("years_experience"))
    return record


def hydrate_case(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    record["permission_to_share"] = bool(record.get("permission_to_share"))
    record["feature_graph"] = parse_json_object(record.get("feature_graph"))
    return record


def hydrate_case_document(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    record["feature_tags"] = parse_multi_value_field(record.get("feature_tags"))
    return record


def create_user(payload: dict[str, Any]) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                str(payload.get("full_name", "")).strip(),
                str(payload.get("email", "")).strip().lower(),
                str(payload.get("password_hash", "")).strip(),
                str(payload.get("role", "")).strip(),
            ),
        )
        return int(cursor.lastrowid)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    return hydrate_user(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return hydrate_user(row) if row else None


def create_session(user_id: int, token: str) -> None:
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO sessions (token, user_id) VALUES (?, ?)",
            (token, user_id),
        )


def delete_session(token: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))


def get_user_by_session_token(token: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
    return hydrate_user(row) if row else None


def get_lawyer_by_user_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM lawyers WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return hydrate_lawyer(row) if row else None


def create_case(payload: dict[str, Any], source: str = "web") -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO cases (
                applicant_user_id,
                full_name,
                contact_phone,
                whatsapp_number,
                state,
                district,
                applicant_category,
                case_category,
                court_level,
                preferred_language,
                urgency,
                income_band,
                preferred_channel,
                summary,
                permission_to_share,
                source,
                status,
                case_stage,
                next_hearing_date,
                feature_graph
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("applicant_user_id"),
                str(payload.get("full_name", "")).strip(),
                str(payload.get("contact_phone", "")).strip(),
                str(payload.get("whatsapp_number", "")).strip(),
                str(payload.get("state", "")).strip(),
                str(payload.get("district", "")).strip(),
                str(payload.get("applicant_category", "")).strip(),
                str(payload.get("case_category", "")).strip(),
                str(payload.get("court_level", "")).strip(),
                str(payload.get("preferred_language", "")).strip(),
                str(payload.get("urgency", "medium")).strip(),
                str(payload.get("income_band", "")).strip(),
                str(payload.get("preferred_channel", "phone")).strip(),
                str(payload.get("summary", "")).strip(),
                int(normalize_bool(payload.get("permission_to_share"))),
                source,
                str(payload.get("status", "new")).strip(),
                str(payload.get("case_stage", "intake_received")).strip(),
                str(payload.get("next_hearing_date", "")).strip(),
                serialize_json_object(payload.get("feature_graph")),
            ),
        )
        return int(cursor.lastrowid)


def create_case_document(payload: dict[str, Any]) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO case_documents (
                case_id,
                original_filename,
                stored_filename,
                content_type,
                extracted_text,
                feature_tags
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                normalize_int(payload.get("case_id")),
                str(payload.get("original_filename", "")).strip(),
                str(payload.get("stored_filename", "")).strip(),
                str(payload.get("content_type", "")).strip(),
                str(payload.get("extracted_text", "")).strip(),
                serialize_multi_value_field(payload.get("feature_tags")),
            ),
        )
        return int(cursor.lastrowid)


def save_lawyer_profile(payload: dict[str, Any]) -> int:
    user_id = payload.get("user_id")
    existing = get_lawyer_by_user_id(normalize_int(user_id)) if user_id else None
    values = (
        user_id,
        str(payload.get("full_name", "")).strip(),
        str(payload.get("bar_council_id", "")).strip(),
        str(payload.get("bar_council_state", "")).strip(),
        str(payload.get("email", "")).strip().lower(),
        str(payload.get("phone", "")).strip(),
        serialize_multi_value_field(payload.get("states_served")),
        serialize_multi_value_field(payload.get("specialties")),
        serialize_multi_value_field(payload.get("languages")),
        serialize_multi_value_field(payload.get("courts_of_practice")),
        normalize_int(payload.get("years_experience")),
        str(payload.get("fee_model", "pro_bono")).strip(),
        str(payload.get("bio", "")).strip(),
        str(payload.get("past_case_history", "")).strip(),
        serialize_json_object(payload.get("feature_graph")),
        str(payload.get("verification_status", "self_attested")).strip(),
        int(normalize_bool(payload.get("declaration_accepted"))),
        int(normalize_bool(payload.get("is_accepting", "1"))),
    )

    with get_connection() as connection:
        if existing:
            connection.execute(
                """
                UPDATE lawyers
                SET
                    user_id = ?,
                    full_name = ?,
                    bar_council_id = ?,
                    bar_council_state = ?,
                    email = ?,
                    phone = ?,
                    states_served = ?,
                    specialties = ?,
                    languages = ?,
                    courts_of_practice = ?,
                    years_experience = ?,
                    fee_model = ?,
                    bio = ?,
                    past_case_history = ?,
                    feature_graph = ?,
                    verification_status = ?,
                    declaration_accepted = ?,
                    is_accepting = ?
                WHERE id = ?
                """,
                (*values, existing["id"]),
            )
            return int(existing["id"])

        cursor = connection.execute(
            """
            INSERT INTO lawyers (
                user_id,
                full_name,
                bar_council_id,
                bar_council_state,
                email,
                phone,
                states_served,
                specialties,
                languages,
                courts_of_practice,
                years_experience,
                fee_model,
                bio,
                past_case_history,
                feature_graph,
                verification_status,
                declaration_accepted,
                is_accepting
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        return int(cursor.lastrowid)


def list_lawyers(
    state: str | None = None,
    court_level: str | None = None,
    case_category: str | None = None,
    query: str | None = None,
    bar_council_state: str | None = None,
    only_accepting: bool = False,
) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM lawyers ORDER BY is_accepting DESC, years_experience DESC, created_at DESC"
        ).fetchall()
    lawyers = [hydrate_lawyer(row) for row in rows]
    filtered: list[dict[str, Any]] = []
    query_lower = (query or "").strip().casefold()

    for lawyer in lawyers:
        if only_accepting and not lawyer["is_accepting"]:
            continue
        if state and state not in lawyer["states_served"]:
            continue
        if court_level and court_level not in lawyer["courts_of_practice"]:
            continue
        if case_category and case_category not in lawyer["specialties"]:
            continue
        if bar_council_state and lawyer.get("bar_council_state") != bar_council_state:
            continue
        if query_lower:
            haystack = " ".join(
                [
                    lawyer.get("full_name", ""),
                    lawyer.get("bio", ""),
                    lawyer.get("past_case_history", ""),
                    lawyer.get("bar_council_id", ""),
                    " ".join(lawyer.get("feature_graph", {}).get("keywords", [])),
                ]
            ).casefold()
            if query_lower not in haystack:
                continue
        filtered.append(lawyer)
    return filtered


def list_cases(
    state: str | None = None,
    case_category: str | None = None,
    court_level: str | None = None,
    applicant_user_id: int | None = None,
    assigned_lawyer_user_id: int | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            cases.*,
            lawyers.full_name AS assigned_lawyer_name
        FROM cases
        LEFT JOIN lawyers ON lawyers.id = cases.assigned_lawyer_id
    """
    filters: list[str] = []
    params: list[Any] = []
    if state:
        filters.append("cases.state = ?")
        params.append(state)
    if case_category:
        filters.append("cases.case_category = ?")
        params.append(case_category)
    if court_level:
        filters.append("cases.court_level = ?")
        params.append(court_level)
    if applicant_user_id is not None:
        filters.append("cases.applicant_user_id = ?")
        params.append(applicant_user_id)
    if assigned_lawyer_user_id is not None:
        filters.append("lawyers.user_id = ?")
        params.append(assigned_lawyer_user_id)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY datetime(cases.created_at) DESC, cases.id DESC"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [hydrate_case(row) for row in rows]


def get_case_by_id(case_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                cases.*,
                lawyers.full_name AS assigned_lawyer_name
            FROM cases
            LEFT JOIN lawyers ON lawyers.id = cases.assigned_lawyer_id
            WHERE cases.id = ?
            """,
            (case_id,),
        ).fetchone()
    return hydrate_case(row) if row else None


def list_case_documents(case_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    if not case_ids:
        return {}

    placeholders = ",".join("?" for _ in case_ids)
    query = (
        "SELECT * FROM case_documents WHERE case_id IN ("
        + placeholders
        + ") ORDER BY id ASC"
    )
    with get_connection() as connection:
        rows = connection.execute(query, case_ids).fetchall()

    grouped: dict[int, list[dict[str, Any]]] = {case_id: [] for case_id in case_ids}
    for row in rows:
        document = hydrate_case_document(row)
        grouped.setdefault(int(document["case_id"]), []).append(document)
    return grouped


def get_case_document(document_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM case_documents WHERE id = ?",
            (document_id,),
        ).fetchone()
    return hydrate_case_document(row) if row else None


def assign_lawyer(case_id: int, lawyer_id: int) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE cases
            SET assigned_lawyer_id = ?, status = 'lawyer_assigned', case_stage = 'lawyer_matched'
            WHERE id = ?
            """,
            (lawyer_id, case_id),
        )


def update_case_progress(case_id: int, case_stage: str, next_hearing_date: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE cases
            SET case_stage = ?, next_hearing_date = ?
            WHERE id = ?
            """,
            (case_stage.strip(), next_hearing_date.strip(), case_id),
        )


def get_overview_stats() -> dict[str, int]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM cases) AS total_cases,
                (SELECT COUNT(*) FROM lawyers) AS total_lawyers,
                (SELECT COUNT(*) FROM cases WHERE permission_to_share = 1) AS consented_cases,
                (SELECT COUNT(*) FROM cases WHERE assigned_lawyer_id IS NOT NULL) AS assigned_cases,
                (SELECT COUNT(*) FROM cases WHERE applicant_category = 'not_sure') AS screening_cases,
                (SELECT COUNT(*) FROM lawyers WHERE verification_status = 'verified') AS verified_lawyers,
                (SELECT COUNT(*) FROM case_documents) AS total_documents,
                (SELECT COUNT(*) FROM users WHERE role = 'applicant') AS total_applicants,
                (SELECT COUNT(*) FROM users WHERE role = 'lawyer') AS total_lawyer_accounts
            """
        ).fetchone()
    return {
        "total_cases": int(row["total_cases"]),
        "total_lawyers": int(row["total_lawyers"]),
        "consented_cases": int(row["consented_cases"]),
        "assigned_cases": int(row["assigned_cases"]),
        "screening_cases": int(row["screening_cases"]),
        "verified_lawyers": int(row["verified_lawyers"]),
        "total_documents": int(row["total_documents"]),
        "total_applicants": int(row["total_applicants"]),
        "total_lawyer_accounts": int(row["total_lawyer_accounts"]),
    }


def match_lawyers_for_case(
    case_record: dict[str, Any], lawyers: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    ranked_matches: list[dict[str, Any]] = []
    for lawyer in lawyers:
        if not lawyer["is_accepting"]:
            continue

        score = 0
        reasons: list[str] = []

        if case_record["state"] in lawyer["states_served"]:
            score += 50
            reasons.append(f"Serves {case_record['state']}")
        else:
            continue

        if case_record["case_category"] in lawyer["specialties"]:
            score += 35
            reasons.append("Matches the case category")

        case_court_level = str(case_record.get("court_level", "")).strip()
        if case_court_level and case_court_level in lawyer["courts_of_practice"]:
            score += 18
            reasons.append(
                f"Practises in {COURT_LEVEL_LABELS.get(case_court_level, case_court_level)}"
            )

        if case_record.get("preferred_language") and case_record["preferred_language"] in lawyer["languages"]:
            score += 12
            reasons.append(f"Can communicate in {case_record['preferred_language']}")

        graph_score, graph_reasons = score_feature_graph_overlap(
            case_record.get("feature_graph", {}),
            lawyer.get("feature_graph", {}),
        )
        score += graph_score
        reasons.extend(graph_reasons)

        if lawyer["fee_model"] == "pro_bono":
            score += 12
            reasons.append("Open to pro bono work")
        elif lawyer["fee_model"] == "low_bono":
            score += 8
            reasons.append("Accepts nominal-fee matters")

        if lawyer.get("declaration_accepted"):
            score += 6
            reasons.append("Has accepted the portal declaration")

        if lawyer.get("verification_status") == "verified":
            score += 8
            reasons.append("Profile is verified")

        score += min(lawyer["years_experience"], 15)

        ranked_matches.append(
            {
                "lawyer": lawyer,
                "score": score,
                "reasons": reasons,
            }
        )

    ranked_matches.sort(
        key=lambda item: (
            item["score"],
            item["lawyer"]["years_experience"],
            item["lawyer"]["full_name"].casefold(),
        ),
        reverse=True,
    )
    return ranked_matches
