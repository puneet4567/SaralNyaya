# SaralNyaya MVP

SaralNyaya is a simple, India-focused legal support portal for people who can’t afford legal aid. It borrows useful ideas from the Department of Justice pro bono flow, but keeps the product much lighter: fewer steps, plain-language forms, document-aware auto-matching, and a public lawyer directory.

This repository is a lightweight demo intended for quick iteration and a vanilla browser walkthrough.


<img width="1089" height="976" alt="Screenshot 2026-04-18 at 3 47 42 PM" src="https://github.com/user-attachments/assets/cbbf2854-196b-4b5e-95a1-cb032891d2dc" />

## What this version includes

- Eligibility guide inspired by legal-aid screening
- Account-based intake for applicants, lawyers, and admins
- Case intake with optional past-document upload
- Document text extraction for `.pdf`, `.docx`, `.txt`, `.md`, `.csv`, and `.json` when supported locally
- Lawyer onboarding with states served, courts of practice, specialties, bar council details, and past case history
- Stored lawyer and case feature graphs for smarter matching
- Auto-routing to the best available lawyer when the applicant consents to sharing
- Matching based on region, court level, issue category, document text, lawyer profile fit, and past case history overlap
- Public lawyer directory with filters
- Secure document downloads restricted to the applicant, assigned lawyer, and admins
- Matching dashboard with progress updates and next hearing date
- Lawyer and applicant workspaces
- A simple `/api/whatsapp/intake` endpoint for future chatbot or WhatsApp automation
- SQLite persistence with local file storage for uploads

## Why this structure stays simple

- Applicants do not need to understand a government-style workflow before asking for help
- Documents are optional, but if submitted they improve matching immediately
- Lawyers do not have to manually browse a pending queue to find relevant matters
- Matching reasons stay visible in the dashboard, so the system is not a black box
- Secure sharing is enforced by role, not by a separate heavy case-management flow

## Run locally

### 1) Start the server (empty DB)

Use the existing virtual environment (recommended) or any Python 3.14+ environment.

Start the app:

```bash
./.venv/bin/python app.py
```

Open `http://127.0.0.1:8000`

The SQLite database is created automatically at `data/portal.db`.
Uploaded files are stored in `uploads/`.

### 2) Seed demo data (recommended for demo / video)

This creates a realistic demo dataset:

- 1000 lawyer profiles across Indian states/UTs
- 100 cases submitted
- 150 documents stored
- 50 assigned matters (auto-assigned using the built-in matching logic)

Run:

```bash
./.venv/bin/python scripts/seed_demo.py
./.venv/bin/python app.py
```

Demo accounts:

- Admin: `admin@saralnyaya.local` / `admin1234`
- Lawyer: `kavya.demo@saralnyaya.local` / `password123`
- Lawyer: `arjun.demo@saralnyaya.local` / `password123`
- Applicant: `rekha.demo@saralnyaya.local` / `password123`
- Applicant: `salim.demo@saralnyaya.local` / `password123`

## Pages

- `/` home and product overview
- `/register` applicant/lawyer account creation
- `/login` sign in
- `/eligibility` legal-aid screening guide
- `/intake` case submission with document upload
- `/my-cases` applicant workspace
- `/lawyers` public lawyer directory
- `/lawyers/onboard` lawyer registration
- `/my-assignments` lawyer workspace
- `/dashboard` auto-matching and progress dashboard
- `/documents/<id>` secure file download endpoint
- `/whatsapp` WhatsApp workflow guide
- `/api/whatsapp/intake` programmatic intake endpoint

## Vanilla flow (quick demo script)

1. Home: confirm the platform overview and the stats row (cases / lawyers / documents / assigned).
2. Find lawyers: filter by State + Category, expand a lawyer card, and open their profile.
3. Applicant signup: create an applicant account.
4. Submit a case: fill the intake form, upload a document, and consent to share with a lawyer.
5. Dashboard: see the auto-match result and the reasons.
6. Lawyer login: review assigned matters and download shared documents (permissioned access).

## How AI-inspired matching works

This portal currently uses an AI-inspired heuristic matching layer rather than an external LLM or embeddings API.

For each applicant case, the system stores and scores:

- issue summary
- state / region
- case category
- court level
- preferred language
- uploaded document text

For each lawyer, the system stores and scores:

- states served
- specialties
- courts of practice
- languages
- fee model
- profile bio
- past case history

The portal builds simple feature graphs and keyword signals for both sides, then ranks lawyers using overlap and rule-based scoring. Key signals include:

- same state or service region
- matching issue category
- matching court / forum
- preferred language match
- overlap between applicant summary/documents and lawyer bio/past case history
- pro bono / low bono preference
- accepting status, declaration, and verification signals

If the applicant has given permission to share the matter, the system can automatically assign the highest-ranked lawyer match. Admins can also review suggested lawyers and see the reasons behind the match.

### Current approach vs future AI upgrade

Current approach:

- Uses rule-based scoring plus extracted keywords from the case summary, uploaded documents, lawyer bio, and lawyer past case history
- Works well when the applicant and lawyer use similar terms such as "wage issue", "consumer grievance", or "documentation problem"
- Keeps the system simple, explainable, and inexpensive to run locally

Future AI upgrade:

- Replace or supplement keyword overlap with embeddings / semantic search and model-based ranking
- Understand similarity even when the applicant and lawyer use different wording for the same issue
- Improve ranking quality for longer documents, mixed-language descriptions, and more complex legal fact patterns

Example:

- Current system: an applicant writes "salary not paid after termination" and uploads a notice. A lawyer profile that mentions "wage recovery", "termination dispute", or "labour tribunal" gets a strong score because the keywords and feature tags overlap.
- Future AI system: an applicant writes "my company removed me and has not cleared dues" while the lawyer profile says "employment separation compensation disputes". Even without the same exact words, an embeddings-based matcher could understand that both refer to a similar labour recovery problem and rank that lawyer highly.

## Product assumptions in this MVP

- Lawyer verification is self-attested by default
- Matching uses heuristics plus extracted document text, not external LLM calls
- WhatsApp intake is API-ready but not connected to an actual provider yet
- Automatic routing currently assigns the single best lawyer match; a lawyer acceptance or rejection queue is a good next step

## Local admin account

On local startup, the app creates a default admin if one does not already exist:

- Email: `admin@saralnyaya.local`
- Password: `admin1234`

You can override those with `LAW_PORTAL_ADMIN_EMAIL`, `LAW_PORTAL_ADMIN_PASSWORD`, and `LAW_PORTAL_ADMIN_NAME`.

## Next good iterations

1. Add lawyer accept/reject flows after automatic routing.
2. Add verified lawyer approval workflows and audit trails.
3. Replace heuristic feature graphs with embeddings or model-based ranking.
4. Add notifications, reminders, and district-level routing.
5. Add WhatsApp provider integration and applicant account linking from chat.
