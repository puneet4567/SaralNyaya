from __future__ import annotations

import random
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal import auth, database
from portal.features import (
    build_case_feature_graph,
    build_lawyer_feature_graph,
    extract_document_text,
    infer_legal_tags,
)
from portal.options import (
    BAR_COUNCIL_OPTIONS,
    CASE_CATEGORIES,
    COURT_LEVEL_OPTIONS,
    FEE_MODELS,
    LANGUAGE_OPTIONS,
    STATES_AND_UTS,
)
from portal.server import ensure_default_admin, upload_root

DB_PATH = BASE_DIR / "data" / "portal.db"
RANDOM = random.Random(42)

FIRST_NAMES = [
    "Aarav",
    "Aditi",
    "Akash",
    "Ananya",
    "Arjun",
    "Asha",
    "Dev",
    "Farah",
    "Harsh",
    "Ishita",
    "Kabir",
    "Karan",
    "Kavya",
    "Meera",
    "Neha",
    "Nikhil",
    "Priya",
    "Rahul",
    "Rhea",
    "Saanvi",
    "Sahil",
    "Sana",
    "Tanya",
    "Varun",
    "Vidya",
    "Yash",
    "Zoya",
]

LAST_NAMES = [
    "Agarwal",
    "Ansari",
    "Banerjee",
    "Bhat",
    "Chauhan",
    "Desai",
    "Gupta",
    "Iyer",
    "Jain",
    "Joshi",
    "Kapoor",
    "Khanna",
    "Kulkarni",
    "Malhotra",
    "Menon",
    "Mishra",
    "Nair",
    "Pandey",
    "Patel",
    "Rao",
    "Reddy",
    "Shah",
    "Sharma",
    "Singh",
    "Srinivasan",
    "Verma",
]

STATE_LANGUAGE_MAP = {
    "Andhra Pradesh": ["Telugu", "English", "Hindi"],
    "Arunachal Pradesh": ["English", "Hindi"],
    "Assam": ["English", "Hindi", "Bengali"],
    "Bihar": ["Hindi", "English", "Urdu"],
    "Chhattisgarh": ["Hindi", "English"],
    "Goa": ["English", "Hindi", "Marathi"],
    "Gujarat": ["Gujarati", "Hindi", "English"],
    "Haryana": ["Hindi", "English", "Punjabi"],
    "Himachal Pradesh": ["Hindi", "English"],
    "Jharkhand": ["Hindi", "English"],
    "Karnataka": ["Kannada", "English", "Hindi"],
    "Kerala": ["Malayalam", "English", "Hindi"],
    "Madhya Pradesh": ["Hindi", "English"],
    "Maharashtra": ["Marathi", "Hindi", "English"],
    "Manipur": ["English", "Hindi"],
    "Meghalaya": ["English", "Hindi"],
    "Mizoram": ["English", "Hindi"],
    "Nagaland": ["English", "Hindi"],
    "Odisha": ["Odia", "Hindi", "English"],
    "Punjab": ["Punjabi", "Hindi", "English"],
    "Rajasthan": ["Hindi", "English"],
    "Sikkim": ["English", "Hindi"],
    "Tamil Nadu": ["Tamil", "English", "Hindi"],
    "Telangana": ["Telugu", "Hindi", "English"],
    "Tripura": ["Bengali", "English", "Hindi"],
    "Uttar Pradesh": ["Hindi", "Urdu", "English"],
    "Uttarakhand": ["Hindi", "English"],
    "West Bengal": ["Bengali", "Hindi", "English"],
    "Andaman and Nicobar Islands": ["English", "Hindi", "Bengali"],
    "Chandigarh": ["Hindi", "English", "Punjabi"],
    "Dadra and Nagar Haveli and Daman and Diu": ["English", "Hindi", "Gujarati"],
    "Delhi": ["Hindi", "English", "Urdu"],
    "Jammu and Kashmir": ["Urdu", "Hindi", "English"],
    "Ladakh": ["Hindi", "English"],
    "Lakshadweep": ["Malayalam", "English"],
    "Puducherry": ["Tamil", "English"],
}

STATE_TO_BAR_COUNCIL = {
    "Andhra Pradesh": "Andhra Pradesh",
    "Arunachal Pradesh": "Assam, Nagaland, Mizoram, Arunachal Pradesh, Sikkim",
    "Assam": "Assam, Nagaland, Mizoram, Arunachal Pradesh, Sikkim",
    "Bihar": "Bihar",
    "Chhattisgarh": "Chhattisgarh",
    "Goa": "Maharashtra and Goa",
    "Gujarat": "Gujarat",
    "Haryana": "Punjab and Haryana",
    "Himachal Pradesh": "Himachal Pradesh",
    "Jharkhand": "Jharkhand",
    "Karnataka": "Karnataka",
    "Kerala": "Kerala",
    "Madhya Pradesh": "Madhya Pradesh",
    "Maharashtra": "Maharashtra and Goa",
    "Manipur": "Manipur",
    "Meghalaya": "Meghalaya",
    "Mizoram": "Assam, Nagaland, Mizoram, Arunachal Pradesh, Sikkim",
    "Nagaland": "Assam, Nagaland, Mizoram, Arunachal Pradesh, Sikkim",
    "Odisha": "Odisha",
    "Punjab": "Punjab and Haryana",
    "Rajasthan": "Rajasthan",
    "Sikkim": "Assam, Nagaland, Mizoram, Arunachal Pradesh, Sikkim",
    "Tamil Nadu": "Tamil Nadu",
    "Telangana": "Telangana",
    "Tripura": "Tripura",
    "Uttar Pradesh": "Uttar Pradesh",
    "Uttarakhand": "Uttarakhand",
    "West Bengal": "West Bengal",
    "Andaman and Nicobar Islands": "Other",
    "Chandigarh": "Punjab and Haryana",
    "Dadra and Nagar Haveli and Daman and Diu": "Other",
    "Delhi": "Delhi",
    "Jammu and Kashmir": "Jammu and Kashmir",
    "Ladakh": "Jammu and Kashmir",
    "Lakshadweep": "Other",
    "Puducherry": "Other",
}

COURT_CODES = [value for value, _label in COURT_LEVEL_OPTIONS]
FEE_CODES = [value for value, _label in FEE_MODELS]


def reset_storage() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    root = upload_root()
    root.mkdir(parents=True, exist_ok=True)
    for item in root.iterdir():
        if item.is_file():
            item.unlink()


def create_user(full_name: str, email: str, role: str, password: str) -> dict[str, object]:
    user_id = database.create_user(
        {
            "full_name": full_name,
            "email": email,
            "password_hash": auth.hash_password(password),
            "role": role,
        }
    )
    return database.get_user_by_id(user_id)


def save_document(case_id: int, filename: str, content: bytes) -> None:
    extracted_text = extract_document_text(filename, "text/plain", content)
    stored_filename = f"{case_id}-{filename}"
    (upload_root() / stored_filename).write_bytes(content)
    database.create_case_document(
        {
            "case_id": case_id,
            "original_filename": filename,
            "stored_filename": stored_filename,
            "content_type": "text/plain",
            "extracted_text": extracted_text,
            "feature_tags": infer_legal_tags(f"{filename} {extracted_text}"),
        }
    )


def pick_languages_for_state(state: str) -> list[str]:
    languages = list(STATE_LANGUAGE_MAP.get(state, ["Hindi", "English"]))
    RANDOM.shuffle(languages)
    count = 2 if len(languages) > 1 else 1
    return languages[:count]


def build_bulk_lawyer_payload(index: int) -> dict[str, object]:
    primary_state = STATES_AND_UTS[index % len(STATES_AND_UTS)]
    extra_states = []
    if index % 5 == 0:
        extra_states.append(STATES_AND_UTS[(index + 7) % len(STATES_AND_UTS)])
    states_served = [primary_state, *extra_states]
    specialties = RANDOM.sample(CASE_CATEGORIES, k=2 + (index % 2))
    courts = RANDOM.sample(COURT_CODES, k=1 + (index % 3 > 0) + (index % 7 == 0))
    languages = pick_languages_for_state(primary_state)
    if "English" not in languages and index % 3 == 0:
        languages.append("English")

    first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
    last_name = LAST_NAMES[(index * 3) % len(LAST_NAMES)]
    full_name = f"Adv. {first_name} {last_name}"
    email = f"lawyer{index:04d}@saralnyaya.demo"
    years_experience = 2 + (index % 18)
    fee_model = FEE_CODES[index % len(FEE_CODES)]
    bar_council_state = STATE_TO_BAR_COUNCIL.get(primary_state, "Other")
    enrollment_prefix = "".join(part[0] for part in primary_state.split()[:2]).upper()
    issue_summary = ", ".join(specialties[:2]).lower()
    court_summary = ", ".join(courts[:2]).replace("_", " ")

    payload = {
        "full_name": full_name,
        "bar_council_id": f"{enrollment_prefix}/{1000 + index}/201{index % 10}",
        "bar_council_state": bar_council_state if bar_council_state in BAR_COUNCIL_OPTIONS else "Other",
        "email": email,
        "phone": f"98{(10000000 + index):08d}"[-10:],
        "states_served": states_served,
        "specialties": specialties,
        "languages": languages,
        "courts_of_practice": courts,
        "years_experience": years_experience,
        "fee_model": fee_model,
        "bio": (
            f"Supports clients in {primary_state} across {issue_summary} matters, "
            f"with regular appearances in {court_summary}."
        ),
        "past_case_history": (
            f"Handled {issue_summary} cases from intake through hearings in {primary_state}, "
            f"including drafting, document review, and forum appearances."
        ),
        "verification_status": "self_attested",
        "declaration_accepted": True,
        "is_accepting": index % 13 != 0,
    }
    payload["feature_graph"] = build_lawyer_feature_graph(payload)
    return payload


def seed_bulk_lawyers(total_lawyers: int, password: str) -> None:
    existing_demo_count = 2
    synthetic_count = max(0, total_lawyers - existing_demo_count)
    for index in range(synthetic_count):
        payload = build_bulk_lawyer_payload(index)
        user = create_user(
            payload["full_name"],
            payload["email"],
            "lawyer",
            password,
        )
        payload["user_id"] = user["id"]
        database.save_lawyer_profile(payload)


def main() -> None:
    reset_storage()
    database.init_db()
    ensure_default_admin()

    lawyer_password = "password123"
    applicant_password = "password123"
    total_lawyers = 1000

    kavya = create_user("Adv. Kavya Menon", "kavya.demo@saralnyaya.local", "lawyer", lawyer_password)
    arjun = create_user("Adv. Arjun Verma", "arjun.demo@saralnyaya.local", "lawyer", lawyer_password)
    rekha = create_user("Rekha Devi", "rekha.demo@saralnyaya.local", "applicant", applicant_password)
    salim = create_user("Salim Ansari", "salim.demo@saralnyaya.local", "applicant", applicant_password)

    kavya_payload = {
        "user_id": kavya["id"],
        "full_name": "Adv. Kavya Menon",
        "bar_council_id": "D/4521/2018",
        "bar_council_state": "Delhi",
        "email": "kavya.demo@saralnyaya.local",
        "phone": "9876500001",
        "states_served": ["Delhi"],
        "specialties": ["Labour / wage issue"],
        "languages": ["Hindi", "English"],
        "courts_of_practice": ["tribunal", "district_court"],
        "years_experience": 6,
        "fee_model": "pro_bono",
        "bio": "Works with workers facing salary delays, wrongful termination, and labour record disputes.",
        "past_case_history": "Handled wage recovery matters, termination disputes, and labour tribunal hearings in Delhi.",
        "verification_status": "self_attested",
        "declaration_accepted": True,
        "is_accepting": True,
    }
    kavya_payload["feature_graph"] = build_lawyer_feature_graph(kavya_payload)
    kavya_id = database.save_lawyer_profile(kavya_payload)

    arjun_payload = {
        "user_id": arjun["id"],
        "full_name": "Adv. Arjun Verma",
        "bar_council_id": "D/3188/2016",
        "bar_council_state": "Delhi",
        "email": "arjun.demo@saralnyaya.local",
        "phone": "9876500002",
        "states_served": ["Delhi", "Uttar Pradesh"],
        "specialties": ["Documentation / identity issue", "Consumer grievance"],
        "languages": ["Hindi", "English"],
        "courts_of_practice": ["pre_litigation", "district_court"],
        "years_experience": 8,
        "fee_model": "low_bono",
        "bio": "Supports public documentation problems, service deficiency complaints, and consumer notices.",
        "past_case_history": "Worked on Aadhaar correction, pension paperwork, and consumer refund complaints.",
        "verification_status": "self_attested",
        "declaration_accepted": True,
        "is_accepting": True,
    }
    arjun_payload["feature_graph"] = build_lawyer_feature_graph(arjun_payload)
    arjun_id = database.save_lawyer_profile(arjun_payload)

    seed_bulk_lawyers(total_lawyers=total_lawyers, password=lawyer_password)

    rekha_case_payload = {
        "applicant_user_id": rekha["id"],
        "full_name": "Rekha Devi",
        "contact_phone": "9876543210",
        "whatsapp_number": "9876543210",
        "state": "Delhi",
        "district": "North Delhi",
        "applicant_category": "low_income",
        "case_category": "Labour / wage issue",
        "court_level": "tribunal",
        "preferred_language": "Hindi",
        "urgency": "high",
        "income_band": "Below Rs. 1.5 lakh / year",
        "preferred_channel": "whatsapp",
        "summary": "Employer has not paid salary for three months after termination and a notice has already been issued.",
        "permission_to_share": True,
        "status": "lawyer_assigned",
        "case_stage": "lawyer_matched",
        "next_hearing_date": "2026-04-25",
        "assigned_lawyer_id": kavya_id,
    }
    rekha_case_payload["feature_graph"] = build_case_feature_graph(
        rekha_case_payload,
        [
            "Salary not paid for 3 months. Termination notice issued. Labour dispute pending before tribunal."
        ],
    )
    rekha_case_id = database.create_case(rekha_case_payload, source="web")
    database.assign_lawyer(rekha_case_id, kavya_id)
    database.update_case_progress(rekha_case_id, "lawyer_matched", "2026-04-25")
    save_document(
        rekha_case_id,
        "termination-notice.txt",
        b"Salary not paid for 3 months. Termination notice issued. Labour dispute pending before tribunal.",
    )

    salim_case_payload = {
        "applicant_user_id": salim["id"],
        "full_name": "Salim Ansari",
        "contact_phone": "9876543201",
        "whatsapp_number": "9876543201",
        "state": "Delhi",
        "district": "East Delhi",
        "applicant_category": "low_income",
        "case_category": "Documentation / identity issue",
        "court_level": "pre_litigation",
        "preferred_language": "Hindi",
        "urgency": "medium",
        "income_band": "Below Rs. 1.5 lakh / year",
        "preferred_channel": "phone",
        "summary": "Aadhaar spelling mismatch is blocking pension and ration access, and multiple correction requests have failed.",
        "permission_to_share": True,
        "status": "lawyer_assigned",
        "case_stage": "documents_review",
        "next_hearing_date": "",
        "assigned_lawyer_id": arjun_id,
    }
    salim_case_payload["feature_graph"] = build_case_feature_graph(
        salim_case_payload,
        [
            "Aadhaar spelling mismatch affecting pension and ration card verification. Prior correction forms submitted."
        ],
    )
    salim_case_id = database.create_case(salim_case_payload, source="whatsapp")
    database.assign_lawyer(salim_case_id, arjun_id)
    database.update_case_progress(salim_case_id, "documents_review", "")
    save_document(
        salim_case_id,
        "aadhaar-correction-request.txt",
        b"Aadhaar spelling mismatch affecting pension and ration card verification. Prior correction forms submitted.",
    )

    print("Seeded SaralNyaya demo data.")
    print(f"Total lawyer profiles: {len(database.list_lawyers())}")
    print("Admin: admin@saralnyaya.local / admin1234")
    print("Lawyer: kavya.demo@saralnyaya.local / password123")
    print("Lawyer: arjun.demo@saralnyaya.local / password123")
    print("Applicant: rekha.demo@saralnyaya.local / password123")
    print("Applicant: salim.demo@saralnyaya.local / password123")


if __name__ == "__main__":
    main()
