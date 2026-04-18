from __future__ import annotations

import re
import sys
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any


BUNDLED_PYTHON_PACKAGES = (
    Path.home()
    / ".cache"
    / "codex-runtimes"
    / "codex-primary-runtime"
    / "dependencies"
    / "python"
)

if BUNDLED_PYTHON_PACKAGES.exists():
    bundled_path = str(BUNDLED_PYTHON_PACKAGES)
    if bundled_path not in sys.path:
        sys.path.append(bundled_path)

try:  # pragma: no cover - optional dependency
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional dependency
    PdfReader = None

try:  # pragma: no cover - optional dependency
    from docx import Document as DocxDocument
except ImportError:  # pragma: no cover - optional dependency
    DocxDocument = None


STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "been",
    "before",
    "between",
    "could",
    "from",
    "have",
    "having",
    "into",
    "need",
    "needs",
    "only",
    "other",
    "people",
    "person",
    "please",
    "portal",
    "regarding",
    "should",
    "their",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "under",
    "very",
    "want",
    "with",
    "would",
    "your",
}

TOKEN_ALIASES = {
    "salaries": "wage",
    "salary": "wage",
    "wages": "wage",
    "employees": "employee",
    "employers": "employer",
    "terminations": "termination",
    "terminated": "termination",
    "tribunals": "tribunal",
    "hearings": "hearing",
    "matters": "matter",
    "benefits": "benefit",
    "documents": "document",
    "orders": "order",
    "notices": "notice",
    "petitions": "petition",
    "agreements": "agreement",
    "landlords": "landlord",
    "tenants": "tenant",
    "children": "child",
}

LEGAL_TAG_SIGNALS = {
    "labour": ["salary", "wage", "wages", "termination", "employee", "employer", "labour", "bonus", "gratuity"],
    "domestic_violence": ["domestic violence", "dowry", "cruelty", "abuse", "protection officer"],
    "family": ["maintenance", "divorce", "custody", "marriage", "alimony"],
    "property": ["property", "land", "mutation", "registry", "partition", "encroachment"],
    "police": ["fir", "police", "complaint", "chargesheet", "arrest", "bail"],
    "consumer": ["consumer", "refund", "defect", "warranty", "service deficiency"],
    "housing": ["rent", "tenant", "landlord", "eviction", "lease"],
    "identity_documents": ["aadhaar", "ration card", "pension", "certificate", "passport", "id proof"],
    "scst": ["atrocity", "sc/st", "scheduled caste", "scheduled tribe"],
    "child": ["child", "juvenile", "school", "minor", "adoption"],
    "senior_citizen": ["senior citizen", "pension", "maintenance tribunal"],
}


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(normalized)
    return values


def safe_decode(content: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_token(token: str) -> str:
    normalized = token.strip().lower()
    if not normalized:
        return ""
    if normalized in TOKEN_ALIASES:
        return TOKEN_ALIASES[normalized]
    if normalized.endswith("ies") and len(normalized) > 4:
        normalized = normalized[:-3] + "y"
    elif normalized.endswith("ing") and len(normalized) > 5:
        normalized = normalized[:-3]
    elif normalized.endswith("ed") and len(normalized) > 4:
        normalized = normalized[:-2]
    elif normalized.endswith("s") and len(normalized) > 4:
        normalized = normalized[:-1]
    return TOKEN_ALIASES.get(normalized, normalized)


def extract_document_text(filename: str, content_type: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix in {".txt", ".md", ".csv", ".json"}:
            return normalize_whitespace(safe_decode(content))
        if suffix == ".pdf" and PdfReader is not None:
            reader = PdfReader(BytesIO(content))
            pages = [
                normalize_whitespace(page.extract_text() or "")
                for page in reader.pages[:10]
            ]
            return normalize_whitespace(" ".join(pages))
        if suffix == ".docx" and DocxDocument is not None:
            document = DocxDocument(BytesIO(content))
            paragraphs = [paragraph.text for paragraph in document.paragraphs]
            return normalize_whitespace(" ".join(paragraphs))
    except Exception:
        return ""

    if content_type.startswith("text/"):
        return normalize_whitespace(safe_decode(content))
    return ""


def tokenize_text(value: str, limit: int = 16) -> list[str]:
    tokens = re.findall(r"[a-zA-Z]{3,}", value.lower())
    filtered = [
        normalize_token(token)
        for token in tokens
        if token not in STOPWORDS and len(token) > 2 and not token.isdigit()
    ]
    filtered = [
        token
        for token in filtered
        if token and token not in STOPWORDS and len(token) > 2
    ]
    ranked = Counter(filtered).most_common(limit)
    return [token for token, _count in ranked]


def infer_legal_tags(value: str) -> list[str]:
    lower_value = value.lower()
    tags = [
        tag
        for tag, signals in LEGAL_TAG_SIGNALS.items()
        if any(signal in lower_value for signal in signals)
    ]
    return dedupe(tags)


def build_case_feature_graph(
    payload: dict[str, Any], extracted_texts: list[str] | None = None
) -> dict[str, Any]:
    extracted_texts = extracted_texts or []
    combined_text = " ".join(
        [
            str(payload.get("summary", "")),
            str(payload.get("case_category", "")),
            str(payload.get("court_level", "")),
            " ".join(extracted_texts),
        ]
    )
    return {
        "tags": dedupe(
            infer_legal_tags(combined_text)
            + [str(payload.get("case_category", "")).strip().lower().replace(" ", "_")]
        ),
        "keywords": tokenize_text(combined_text),
        "practice_areas": dedupe([str(payload.get("case_category", "")).strip()]),
        "courts": dedupe([str(payload.get("court_level", "")).strip()]),
        "states": dedupe([str(payload.get("state", "")).strip()]),
        "languages": dedupe([str(payload.get("preferred_language", "")).strip()]),
        "eligibility": dedupe([str(payload.get("applicant_category", "")).strip()]),
    }


def build_lawyer_feature_graph(payload: dict[str, Any]) -> dict[str, Any]:
    states_served = [str(value) for value in payload.get("states_served", [])]
    specialties = [str(value) for value in payload.get("specialties", [])]
    courts_of_practice = [str(value) for value in payload.get("courts_of_practice", [])]
    languages = [str(value) for value in payload.get("languages", [])]
    past_case_history = str(payload.get("past_case_history", ""))
    combined_text = " ".join(
        specialties
        + courts_of_practice
        + languages
        + states_served
        + [str(payload.get("bio", "")), past_case_history]
    )
    return {
        "tags": dedupe(
            infer_legal_tags(combined_text)
            + [specialty.strip().lower().replace(" ", "_") for specialty in specialties]
        ),
        "keywords": tokenize_text(combined_text),
        "practice_areas": dedupe(specialties),
        "courts": dedupe(courts_of_practice),
        "states": dedupe(states_served),
        "languages": dedupe(languages),
        "past_case_keywords": tokenize_text(past_case_history, limit=12),
        "fee_model": str(payload.get("fee_model", "")).strip(),
    }


def score_feature_graph_overlap(
    case_graph: dict[str, Any], lawyer_graph: dict[str, Any]
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    case_tags = set(case_graph.get("tags", []))
    lawyer_tags = set(lawyer_graph.get("tags", []))
    shared_tags = sorted(case_tags & lawyer_tags)
    if shared_tags:
        score += min(24, 8 * len(shared_tags))
        reasons.append("Shared issue signals: " + ", ".join(shared_tags[:3]))

    case_keywords = set(case_graph.get("keywords", []))
    lawyer_keywords = set(lawyer_graph.get("keywords", []))
    shared_keywords = sorted(case_keywords & lawyer_keywords)
    if shared_keywords:
        score += min(12, 4 * len(shared_keywords[:3]))
        reasons.append("Text overlap: " + ", ".join(shared_keywords[:3]))

    past_case_keywords = set(lawyer_graph.get("past_case_keywords", []))
    shared_history = sorted(case_keywords & past_case_keywords)
    if shared_history:
        score += min(15, 5 * len(shared_history[:3]))
        reasons.append("Past case history overlap: " + ", ".join(shared_history[:3]))

    return score, reasons
