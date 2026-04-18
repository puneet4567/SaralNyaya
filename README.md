# NyayaSetu MVP

NyayaSetu is a simple, India-focused legal support portal for underserved communities. It borrows the useful ideas from the Department of Justice pro bono flow, but keeps the product much lighter: fewer steps, plain-language forms, document-aware auto-matching, and a public lawyer directory.

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

1. Use the existing virtual environment or any Python 3.14+ environment.
2. Start the app:

```bash
./.venv/bin/python app.py
```

3. Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

The SQLite database is created automatically at `data/portal.db`.
Uploaded files are stored in `uploads/`.

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

## Product assumptions in this MVP

- Lawyer verification is self-attested by default
- Matching uses heuristics plus extracted document text, not external LLM calls
- WhatsApp intake is API-ready but not connected to an actual provider yet
- Automatic routing currently assigns the single best lawyer match; a lawyer acceptance or rejection queue is a good next step

## Local admin account

On local startup, the app creates a default admin if one does not already exist:

- Email: `admin@nyayasetu.local`
- Password: `admin1234`

You can override those with `LAW_PORTAL_ADMIN_EMAIL`, `LAW_PORTAL_ADMIN_PASSWORD`, and `LAW_PORTAL_ADMIN_NAME`.

## Next good iterations

1. Add lawyer accept/reject flows after automatic routing.
2. Add verified lawyer approval workflows and audit trails.
3. Replace heuristic feature graphs with embeddings or model-based ranking.
4. Add notifications, reminders, and district-level routing.
5. Add WhatsApp provider integration and applicant account linking from chat.
