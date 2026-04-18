from __future__ import annotations

import json
from html import escape
from typing import Any

from portal.options import (
    BAR_COUNCIL_OPTIONS,
    CASE_CATEGORIES,
    CASE_STAGE_OPTIONS,
    COURT_LEVEL_OPTIONS,
    ELIGIBILITY_OPTIONS,
    ELIGIBILITY_PROOF_HINTS,
    FEE_MODELS,
    INCOME_BANDS,
    LANGUAGE_OPTIONS,
    LAWYER_STATE_OPTIONS,
    PREFERRED_CHANNELS,
    STATES_AND_UTS,
    URGENCY_OPTIONS,
)


COURT_LEVEL_LABELS = dict(COURT_LEVEL_OPTIONS)
CASE_STAGE_LABELS = dict(CASE_STAGE_OPTIONS)
ELIGIBILITY_LABELS = dict(ELIGIBILITY_OPTIONS)


def text(value: Any) -> str:
    return escape("" if value is None else str(value))


def normalize_selected(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def option_pairs(options: list[Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for option in options:
        if isinstance(option, tuple):
            pairs.append((str(option[0]), str(option[1])))
        else:
            pairs.append((str(option), str(option)))
    return pairs


def render_select_options(
    options: list[Any],
    selected: Any = None,
    include_blank: bool = False,
    blank_label: str = "Choose one",
) -> str:
    selected_values = set(normalize_selected(selected))
    rendered: list[str] = []
    if include_blank:
        rendered.append(f'<option value="">{text(blank_label)}</option>')
    for value, label in option_pairs(options):
        is_selected = ' selected="selected"' if value in selected_values else ""
        rendered.append(
            f'<option value="{text(value)}"{is_selected}>{text(label)}</option>'
        )
    return "".join(rendered)


def render_badges(items: list[str], empty_label: str = "Not provided") -> str:
    if not items:
        return f'<span class="tag muted">{text(empty_label)}</span>'
    return "".join(f'<span class="tag">{text(item)}</span>' for item in items)


def render_messages(messages: list[str] | None, kind: str) -> str:
    if not messages:
        return ""
    content = "".join(f"<li>{text(message)}</li>" for message in messages)
    return f'<div class="message {text(kind)}"><ul>{content}</ul></div>'


def render_label_list(title: str, items: list[str], empty_label: str = "Not provided") -> str:
    return f"""
    <div class="label-stack">
      <strong>{text(title)}</strong>
      <div>{render_badges(items, empty_label=empty_label)}</div>
    </div>
    """


def render_illustration_card(
    image_path: str,
    title: str,
    caption: str,
    tone: str = "sage",
) -> str:
    return f"""
    <aside class="illustration-card tone-{text(tone)}">
      <img class="illustration-image" src="{text(image_path)}" alt="{text(title)}">
      <div class="illustration-copy">
        <p class="eyebrow">Portal flow</p>
        <h3>{text(title)}</h3>
        <p>{text(caption)}</p>
      </div>
    </aside>
    """


def nav_links_for_user(user: dict[str, Any] | None) -> list[tuple[str, str]]:
    if not user:
        return [
            ("/", "Home"),
            ("/eligibility", "Check eligibility"),
            ("/lawyers", "Find lawyers"),
            ("/register?role=applicant", "Applicant signup"),
            ("/register?role=lawyer", "Lawyer signup"),
            ("/login", "Login"),
        ]
    role = user.get("role")
    if role == "applicant":
        return [
            ("/", "Home"),
            ("/eligibility", "Check eligibility"),
            ("/intake", "Submit a case"),
            ("/my-cases", "My cases"),
            ("/lawyers", "Find lawyers"),
            ("/logout", "Logout"),
        ]
    if role == "lawyer":
        return [
            ("/", "Home"),
            ("/lawyers/onboard", "Lawyer profile"),
            ("/my-assignments", "My assignments"),
            ("/lawyers", "Find lawyers"),
            ("/logout", "Logout"),
        ]
    return [
        ("/", "Home"),
        ("/dashboard", "Dashboard"),
        ("/lawyers", "Find lawyers"),
        ("/logout", "Logout"),
    ]


def current_path_matches(current_path: str, href: str) -> bool:
    if href == "/":
        return current_path == "/"
    return current_path.startswith(href.split("?", 1)[0])


def layout(
    title: str,
    body: str,
    current_path: str,
    user: dict[str, Any] | None = None,
) -> str:
    nav_links = nav_links_for_user(user)
    nav = "".join(
        f'<a class="nav-link{" active" if current_path_matches(current_path, href) else ""}" href="{href}">{label}</a>'
        for href, label in nav_links
    )
    account_chip = (
        f'<div class="account-chip"><strong>{text(user["full_name"])}</strong><span>{text(user["role"])}</span></div>'
        if user
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{text(title)}</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <div class="page-shell">
    <header class="site-header">
      <a class="brand" href="/">
        <span class="brand-mark">SaralNyaya</span>
        <span class="brand-copy">Faster legal access for underserved communities</span>
      </a>
      <div class="site-nav-wrap">
        <nav class="site-nav">{nav}</nav>
        {account_chip}
      </div>
    </header>
    <main>{body}</main>
  </div>
</body>
</html>
"""


def render_auth_page(
    mode: str,
    role: str,
    next_path: str = "",
    values: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    user: dict[str, Any] | None = None,
) -> str:
    values = values or {}
    is_register = mode == "register"
    title = "Create account" if is_register else "Login"
    subtitle = (
        "Create a secure account so case documents and assignments stay role-restricted."
        if is_register
        else "Log in to access applicant cases, lawyer assignments, or the admin dashboard."
    )
    role_field = (
        f"""
        <label>
          Role
          <select name="role">
            {render_select_options([("applicant", "Applicant"), ("lawyer", "Lawyer")], role or "applicant")}
          </select>
        </label>
        """
        if is_register
        else ""
    )
    name_field = (
        f"""
        <label>
          Full name
          <input type="text" name="full_name" value="{text(values.get("full_name", ""))}" placeholder="Your name">
        </label>
        """
        if is_register
        else ""
    )
    confirm_field = (
        f"""
        <label>
          Confirm password
          <input type="password" name="confirm_password" value="" placeholder="Re-enter password">
        </label>
        """
        if is_register
        else ""
    )
    alternate_link = (
        f'<a class="button secondary" href="/login?next={text(next_path)}">Already have an account?</a>'
        if is_register
        else f'<a class="button secondary" href="/register?role=applicant&next={text(next_path)}">Create applicant account</a>'
    )
    body = f"""
    <section class="auth-shell">
      <div class="auth-copy">
        <p class="eyebrow">Secure access</p>
        <h1>{text(title)}</h1>
        <p class="lead">{text(subtitle)}</p>
        <ul class="plain-list">
          <li>Applicants can see only their own cases and documents.</li>
          <li>Lawyers can see only assigned matters and approved files.</li>
          <li>Admins can manage the full matching workflow.</li>
        </ul>
        {render_illustration_card(
            "/static/lawyer-network.svg",
            "Separate workspaces, shared legal mission",
            "The portal stays simple for people using it while still protecting documents and assignments by role.",
            tone="sage",
        )}
      </div>
      <div>
        {render_messages(errors, "error")}
        <form class="form-card" method="post" action="/{text(mode)}">
          <input type="hidden" name="next" value="{text(next_path)}">
          {role_field}
          {name_field}
          <label>
            Email
            <input type="email" name="email" value="{text(values.get("email", ""))}" placeholder="name@example.com">
          </label>
          <label>
            Password
            <input type="password" name="password" value="" placeholder="Password">
          </label>
          {confirm_field}
          <div class="form-actions">
            <button class="button primary" type="submit">{text("Create account" if is_register else "Login")}</button>
            {alternate_link}
          </div>
        </form>
      </div>
    </section>
    """
    return layout(title, body, f"/{mode}", user=user)


def render_access_denied(
    title: str,
    message: str,
    user: dict[str, Any] | None = None,
) -> str:
    body = f"""
    <section class="form-header">
      <p class="eyebrow">Access restricted</p>
      <h1>{text(title)}</h1>
      <p class="lead">{text(message)}</p>
    </section>
    """
    return layout(title, body, "/", user=user)


def render_home(stats: dict[str, int], user: dict[str, Any] | None = None) -> str:
    primary_cta = (
        '<a class="button primary" href="/intake">Submit a case</a>'
        if user and user.get("role") == "applicant"
        else '<a class="button primary" href="/register?role=applicant&next=/intake">Submit a case</a>'
    )
    lawyer_cta = (
        '<a class="button secondary" href="/lawyers/onboard">Complete lawyer profile</a>'
        if user and user.get("role") == "lawyer"
        else '<a class="button secondary" href="/register?role=lawyer&next=/lawyers/onboard">Join as a lawyer</a>'
    )
    body = f"""
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">India-focused legal aid portal</p>
        <h1>Securely match applicants and lawyers using issue text, prior documents, and practice history.</h1>
        <p class="lead">
          Applicants can upload past case papers. Lawyers can add their profile and past case history.
          Access to those documents is then restricted by role, ownership, and assignment.
        </p>
        <div class="hero-actions">
          {primary_cta}
          {lawyer_cta}
          <a class="button secondary" href="/lawyers">Find lawyers</a>
        </div>
        <div class="info-strip">
          This keeps the product simple for users while adding the security layer needed for real document sharing.
        </div>
      </div>
      <aside class="hero-panel">
        {render_illustration_card(
            "/static/community-justice.svg",
            "People, advocates, and the system connected in one place",
            "A warmer first screen for applicants, lawyers, and admins handling sensitive court matters.",
            tone="terracotta",
        )}
        <div class="stat-card">
          <span class="stat-value">{stats["total_cases"]}</span>
          <span class="stat-label">cases submitted</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{stats["total_lawyers"]}</span>
          <span class="stat-label">lawyer profiles</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{stats["total_documents"]}</span>
          <span class="stat-label">documents stored</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{stats["assigned_cases"]}</span>
          <span class="stat-label">assigned matters</span>
        </div>
      </aside>
    </section>

    <section class="spotlight-grid">
      <article class="card">
        <h2>Applicants</h2>
        <ul class="plain-list">
          <li>Create an account and keep your case papers private.</li>
          <li>Submit the issue and upload previous case documents.</li>
          <li>Track your case stage in one simple workspace.</li>
        </ul>
      </article>
      <article class="card">
        <h2>Lawyers</h2>
        <ul class="plain-list">
          <li>Build a feature-rich profile with courts, specialties, and past case history.</li>
          <li>See only the matters assigned to you.</li>
          <li>Download only the documents you are authorized to access.</li>
        </ul>
      </article>
      <article class="card">
        <h2>Admins</h2>
        <ul class="plain-list">
          <li>Review the full queue and matching reasons.</li>
          <li>Assign lawyers and monitor progress.</li>
          <li>Control document visibility through assignment.</li>
        </ul>
      </article>
    </section>
    """
    return layout("SaralNyaya", body, "/", user=user)


def render_eligibility_guide(user: dict[str, Any] | None = None) -> str:
    eligibility_cards = "".join(
        f"""
        <article class="card eligibility-card">
          <h3>{text(label)}</h3>
          <p>{text(ELIGIBILITY_PROOF_HINTS.get(value, "Supporting proof can be added later if available."))}</p>
        </article>
        """
        for value, label in ELIGIBILITY_OPTIONS
    )
    body = f"""
    <section class="form-header">
      <p class="eyebrow">Eligibility guide</p>
      <h1>Check whether the applicant may qualify for legal aid support.</h1>
      <p class="lead">
        This keeps the legal-aid screening logic visible without turning the submission into a government-style maze.
      </p>
    </section>
    <section class="two-column">
      {render_illustration_card(
          "/static/document-match.svg",
          "Documents and issue summaries make triage simpler",
          "Even a notice, FIR copy, order sheet, or agreement can improve matching without making the process feel bureaucratic.",
          tone="sand",
      )}
      <article class="card">
        <h2>Use it as guidance</h2>
        <ul class="plain-list">
          <li>Select the closest eligibility group while submitting the case.</li>
          <li>If unsure, choose not sure and let the admin review it later.</li>
          <li>Past case papers can still be uploaded even if proof is not ready yet.</li>
        </ul>
      </article>
      <article class="card">
        <h2>What helps matching</h2>
        <ul class="plain-list">
          <li>The issue summary in plain language</li>
          <li>Past orders, notices, FIR copies, petitions, or agreements</li>
          <li>Region, court/forum level, urgency, and language</li>
        </ul>
      </article>
    </section>
    <section class="spotlight-grid">{eligibility_cards}</section>
    """
    return layout("Check eligibility", body, "/eligibility", user=user)


def render_case_form(
    values: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    submitted_case_id: int | None = None,
    auto_matched: bool = False,
    user: dict[str, Any] | None = None,
) -> str:
    values = values or {}
    selected_permission = str(values.get("permission_to_share", "yes"))
    success_message = (
        [
            (
                f"Case #{submitted_case_id} was submitted successfully. It has already been routed to the best available lawyer using your issue summary, documents, state, court, and language."
                if auto_matched
                else f"Case #{submitted_case_id} was submitted successfully. It is now private to you, the assigned lawyer, and admins."
            )
        ]
        if submitted_case_id
        else None
    )
    body = f"""
    <section class="form-header">
      <p class="eyebrow">Applicant case intake</p>
      <h1>Submit your issue and any past case documents.</h1>
      <p class="lead">
        Because you are signed in, the documents you upload can be protected and shown only to the right people.
      </p>
    </section>
    {render_messages(success_message, "success")}
    {render_messages(errors, "error")}
    <section class="two-column media-section">
      {render_illustration_card(
          "/static/document-match.svg",
          "Upload papers that explain the dispute",
          "Past notices, orders, salary records, petitions, rent papers, or FIR copies help the matcher understand the case faster.",
          tone="sand",
      )}
      <article class="card">
        <h2>What the matcher looks at</h2>
        <ul class="plain-list">
          <li>The issue summary in plain language</li>
          <li>The state, court, language, and urgency</li>
          <li>The text extracted from uploaded documents</li>
          <li>Lawyer practice history on similar matters</li>
        </ul>
      </article>
    </section>
    <form class="form-card" method="post" action="/intake" enctype="multipart/form-data">
      <div class="form-grid">
        <label>
          Full name
          <input type="text" name="full_name" value="{text(values.get("full_name", user.get("full_name") if user else ""))}" placeholder="Name of the person seeking help">
        </label>
        <label>
          Contact phone
          <input type="text" name="contact_phone" value="{text(values.get("contact_phone", ""))}" placeholder="10-digit mobile number">
        </label>
        <label>
          WhatsApp number
          <input type="text" name="whatsapp_number" value="{text(values.get("whatsapp_number", ""))}" placeholder="Optional if different from phone">
        </label>
        <label>
          State / Union Territory
          <select name="state">
            {render_select_options(STATES_AND_UTS, values.get("state"), include_blank=True, blank_label="Select a state")}
          </select>
        </label>
        <label>
          District
          <input type="text" name="district" value="{text(values.get("district", ""))}" placeholder="Optional district or city">
        </label>
        <label>
          Applicant eligibility group
          <select name="applicant_category">
            {render_select_options(ELIGIBILITY_OPTIONS, values.get("applicant_category"), include_blank=True, blank_label="Select eligibility or choose not sure")}
          </select>
        </label>
        <label>
          Legal issue type
          <select name="case_category">
            {render_select_options(CASE_CATEGORIES, values.get("case_category"), include_blank=True, blank_label="Select a category")}
          </select>
        </label>
        <label>
          Where is the matter currently?
          <select name="court_level">
            {render_select_options(COURT_LEVEL_OPTIONS, values.get("court_level"), include_blank=True, blank_label="Select court or forum")}
          </select>
        </label>
        <label>
          Preferred language
          <select name="preferred_language">
            {render_select_options(LANGUAGE_OPTIONS, values.get("preferred_language"), include_blank=True, blank_label="Choose a language")}
          </select>
        </label>
        <label>
          Urgency
          <select name="urgency">
            {render_select_options(URGENCY_OPTIONS, values.get("urgency", "medium"))}
          </select>
        </label>
        <label>
          Income band
          <select name="income_band">
            {render_select_options(INCOME_BANDS, values.get("income_band"), include_blank=True, blank_label="Select income band")}
          </select>
        </label>
        <label>
          Preferred contact channel
          <select name="preferred_channel">
            {render_select_options(PREFERRED_CHANNELS, values.get("preferred_channel", "phone"))}
          </select>
        </label>
        <label>
          Next hearing date
          <input type="date" name="next_hearing_date" value="{text(values.get("next_hearing_date", ""))}">
        </label>
      </div>
      <label>
        Short summary of the issue
        <textarea name="summary" rows="6" placeholder="Explain what happened, the other party involved, and what has already happened in the case">{text(values.get("summary", ""))}</textarea>
      </label>
      <label>
        Upload past case documents
        <input type="file" name="documents" multiple accept=".pdf,.docx,.txt,.md,.csv,.json">
        <span class="field-help">Helpful examples: prior orders, notices, rent agreements, petitions, salary records, FIR copies, or court filings.</span>
      </label>
      <fieldset class="radio-group">
        <legend>Can this case be shared with lawyers on the platform?</legend>
        <label class="radio-card">
          <input type="radio" name="permission_to_share" value="yes"{" checked" if selected_permission == "yes" else ""}>
          <span>Yes, share with matched lawyers.</span>
        </label>
        <label class="radio-card">
          <input type="radio" name="permission_to_share" value="no"{" checked" if selected_permission == "no" else ""}>
          <span>No, ask me before sharing personal case details.</span>
        </label>
      </fieldset>
      <div class="form-actions">
        <button class="button primary" type="submit">Submit case</button>
        <a class="button secondary" href="/my-cases">My cases</a>
      </div>
    </form>
    """
    return layout("Submit a case", body, "/intake", user=user)


def render_lawyer_form(
    values: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    submitted_lawyer_id: int | None = None,
    user: dict[str, Any] | None = None,
) -> str:
    values = values or {}
    success_message = (
        [
            f"Lawyer profile #{submitted_lawyer_id} was saved. Your past case history now contributes to matching."
        ]
        if submitted_lawyer_id
        else None
    )
    states_selected = normalize_selected(values.get("states_served"))
    categories_selected = normalize_selected(values.get("specialties"))
    languages_selected = normalize_selected(values.get("languages"))
    courts_selected = normalize_selected(values.get("courts_of_practice"))
    is_accepting = str(values.get("is_accepting", "yes")) != "no"
    declaration_checked = str(values.get("declaration_accepted", "yes")).lower() in {
        "yes",
        "true",
        "1",
        "on",
    }
    body = f"""
    <section class="form-header">
      <p class="eyebrow">Lawyer profile</p>
      <h1>Submit your profile and past case history for better matchmaking.</h1>
      <p class="lead">
        The platform turns your region, courts, specialties, profile text, and past-case history into a richer feature graph.
      </p>
    </section>
    {render_messages(success_message, "success")}
    {render_messages(errors, "error")}
    <section class="two-column media-section">
      <article class="card">
        <h2>What improves your match score</h2>
        <ul class="plain-list">
          <li>Courts and states you actively serve</li>
          <li>Clear specialties and working languages</li>
          <li>Anonymized past matter summaries</li>
          <li>Whether you are open to low-bono or pro bono work</li>
        </ul>
      </article>
      {render_illustration_card(
          "/static/lawyer-network.svg",
          "Your experience becomes structured matching data",
          "The platform converts practice areas, courts, profile copy, and case history into a feature graph for routing.",
          tone="sage",
      )}
    </section>
    <form class="form-card" method="post" action="/lawyers/onboard">
      <div class="form-grid">
        <label>
          Full name
          <input type="text" name="full_name" value="{text(values.get("full_name", user.get("full_name") if user else ""))}" placeholder="Advocate name">
        </label>
        <label>
          Enrollment number
          <input type="text" name="bar_council_id" value="{text(values.get("bar_council_id", ""))}" placeholder="Bar Council enrollment number">
        </label>
        <label>
          State Bar Council
          <select name="bar_council_state">
            {render_select_options(BAR_COUNCIL_OPTIONS, values.get("bar_council_state"), include_blank=True, blank_label="Select bar council")}
          </select>
        </label>
        <label>
          Email
          <input type="email" name="email" value="{text(values.get("email", user.get("email") if user else ""))}" placeholder="Email address">
        </label>
        <label>
          Phone
          <input type="text" name="phone" value="{text(values.get("phone", ""))}" placeholder="Mobile number">
        </label>
        <label>
          Years of experience
          <input type="number" min="0" name="years_experience" value="{text(values.get("years_experience", ""))}" placeholder="0">
        </label>
        <label>
          Fee model
          <select name="fee_model">
            {render_select_options(FEE_MODELS, values.get("fee_model", "pro_bono"))}
          </select>
        </label>
      </div>
      <div class="form-grid">
        <label>
          States served
          <select name="states_served" multiple size="8">
            {render_select_options(LAWYER_STATE_OPTIONS, states_selected)}
          </select>
        </label>
        <label>
          Specialties
          <select name="specialties" multiple size="8">
            {render_select_options(CASE_CATEGORIES, categories_selected)}
          </select>
        </label>
        <label>
          Courts / forums of practice
          <select name="courts_of_practice" multiple size="8">
            {render_select_options(COURT_LEVEL_OPTIONS, courts_selected)}
          </select>
        </label>
        <label>
          Languages
          <select name="languages" multiple size="8">
            {render_select_options(LANGUAGE_OPTIONS, languages_selected)}
          </select>
        </label>
      </div>
      <label>
        Short profile
        <textarea name="bio" rows="4" placeholder="Describe the type of clients and legal problems you regularly work with">{text(values.get("bio", ""))}</textarea>
      </label>
      <label>
        Past case history
        <textarea name="past_case_history" rows="6" placeholder="Add anonymized history of the kinds of matters you have handled, the courts involved, and the outcomes or procedural stages you know well">{text(values.get("past_case_history", ""))}</textarea>
        <span class="field-help">Use summaries, not confidential client details.</span>
      </label>
      <fieldset class="radio-group">
        <legend>Availability</legend>
        <label class="radio-card">
          <input type="radio" name="is_accepting" value="yes"{" checked" if is_accepting else ""}>
          <span>Currently accepting new matters.</span>
        </label>
        <label class="radio-card">
          <input type="radio" name="is_accepting" value="no"{" checked" if not is_accepting else ""}>
          <span>Keep profile active but pause new assignments.</span>
        </label>
      </fieldset>
      <label class="checkbox-card">
        <input type="checkbox" name="declaration_accepted" value="yes"{" checked" if declaration_checked else ""}>
        <span>I confirm that my profile and history are accurate and may be used for matching.</span>
      </label>
      <div class="form-actions">
        <button class="button primary" type="submit">Save lawyer profile</button>
        <a class="button secondary" href="/my-assignments">My assignments</a>
      </div>
    </form>
    """
    return layout("Lawyer profile", body, "/lawyers/onboard", user=user)


def render_lawyer_card(lawyer: dict[str, Any], show_private_history: bool = False) -> str:
    tags = lawyer.get("feature_graph", {}).get("tags", [])[:6]
    history_preview = lawyer.get("past_case_history", "")
    history_block = (
        f'<p class="history-copy">{text(history_preview)}</p>'
        if show_private_history and history_preview
        else ""
    )
    return f"""
    <article class="lawyer-card">
      <div class="card-head">
        <div>
          <p class="eyebrow">Lawyer #{text(lawyer["id"])}</p>
          <h3>{text(lawyer["full_name"])}</h3>
        </div>
        <div class="status-stack">
          <span class="status-pill{" muted" if not lawyer["is_accepting"] else ""}">
            {text("accepting" if lawyer["is_accepting"] else "paused")}
          </span>
          <span class="mini-pill">{text(lawyer.get("verification_status", "self_attested").replace("_", " "))}</span>
        </div>
      </div>
      <p>{text(lawyer["bio"] or "No profile summary added yet.")}</p>
      {history_block}
      <div class="meta-grid">
        <span>Bar Council: {text(lawyer.get("bar_council_state") or "Not set")}</span>
        <span>Enrollment: {text(lawyer["bar_council_id"])}</span>
        <span>{text(lawyer["years_experience"])} years</span>
        <span>{text(lawyer["fee_model"].replace("_", " "))}</span>
      </div>
      {render_label_list("States served", lawyer["states_served"])}
      {render_label_list("Specialties", lawyer["specialties"])}
      {render_label_list("Courts of practice", [COURT_LEVEL_LABELS.get(item, item) for item in lawyer["courts_of_practice"]])}
      {render_label_list("Languages", lawyer["languages"])}
      {render_label_list("Feature tags", tags, empty_label="Generated after onboarding")}
    </article>
    """


def render_lawyer_directory(
    lawyers: list[dict[str, Any]],
    selected_state: str = "",
    selected_bar_council_state: str = "",
    selected_category: str = "",
    selected_court_level: str = "",
    query: str = "",
    user: dict[str, Any] | None = None,
) -> str:
    body = f"""
    <section class="form-header">
      <p class="eyebrow">Lawyer directory</p>
      <h1>Browse lawyers by region, bar council, issue type, and court of practice.</h1>
      <p class="lead">
        Public discovery stays open, but confidential case documents remain protected behind account and role checks.
      </p>
    </section>
    <section class="two-column media-section">
      {render_illustration_card(
          "/static/community-justice.svg",
          "Regional discovery without the portal feeling heavy",
          "People can browse by state, bar council, issue type, and court before the platform handles deeper matching.",
          tone="terracotta",
      )}
      <article class="card">
        <h2>Directory filters that matter</h2>
        <ul class="plain-list">
          <li>State served and bar council registration</li>
          <li>Practice area and court/forum level</li>
          <li>Public profile summary and availability</li>
        </ul>
      </article>
    </section>
    <section class="filter-card">
      <form class="filter-grid" method="get" action="/lawyers">
        <label>
          Search
          <input type="text" name="q" value="{text(query)}" placeholder="Name, enrollment number, or keyword">
        </label>
        <label>
          State served
          <select name="state">
            {render_select_options(STATES_AND_UTS, selected_state, include_blank=True, blank_label="All states")}
          </select>
        </label>
        <label>
          State Bar Council
          <select name="bar_council_state">
            {render_select_options(BAR_COUNCIL_OPTIONS, selected_bar_council_state, include_blank=True, blank_label="All bar councils")}
          </select>
        </label>
        <label>
          Legal issue type
          <select name="case_category">
            {render_select_options(CASE_CATEGORIES, selected_category, include_blank=True, blank_label="All categories")}
          </select>
        </label>
        <label>
          Court / forum
          <select name="court_level">
            {render_select_options(COURT_LEVEL_OPTIONS, selected_court_level, include_blank=True, blank_label="All courts")}
          </select>
        </label>
        <div class="filter-actions">
          <button class="button primary" type="submit">Apply filters</button>
          <a class="button secondary" href="/lawyers">Reset</a>
        </div>
      </form>
    </section>
    <section class="directory-grid">
      {"".join(render_lawyer_card(lawyer) for lawyer in lawyers) if lawyers else '<article class="empty-card">No lawyers match the current filters yet.</article>'}
    </section>
    """
    return layout("Find lawyers", body, "/lawyers", user=user)


def render_document_links(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return '<li class="helper-text">No documents uploaded.</li>'
    return "".join(
        f"""
        <li class="doc-item">
          <div class="doc-head">
            <strong>{text(document["original_filename"])}</strong>
            <a class="doc-link" href="/documents/{text(document["id"])}">Download</a>
          </div>
          <div>{render_badges(document.get("feature_tags", []), empty_label="No tags extracted")}</div>
        </li>
        """
        for document in documents
    )


def render_case_overview_card(
    case: dict[str, Any],
    user: dict[str, Any] | None = None,
    show_assignment: bool = False,
    show_progress_form: bool = False,
    selected_state: str = "",
    selected_category: str = "",
    selected_court_level: str = "",
    progress_origin: str = "dashboard",
) -> str:
    match_blocks = []
    for match in case.get("matches", [])[:3]:
        lawyer = match["lawyer"]
        reasons = ", ".join(match["reasons"]) if match["reasons"] else "General availability"
        match_blocks.append(
            f"""
            <li class="match-item">
              <div class="match-heading">
                <strong>{text(lawyer["full_name"])}</strong>
                <span class="score-pill">{text(match["score"])} pts</span>
              </div>
              <p>{text(reasons)}</p>
            </li>
            """
        )

    assignment_candidates = case.get("matches", [])
    assignment_select = render_select_options(
        [
            (
                str(match["lawyer"]["id"]),
                f'{match["lawyer"]["full_name"]} ({match["score"]} pts)',
            )
            for match in assignment_candidates
        ],
        selected=str(case.get("assigned_lawyer_id") or ""),
        include_blank=True,
        blank_label="Choose a lawyer",
    )
    assignment_ui = (
        f"""
        <form class="assign-form" method="post" action="/assign">
          <input type="hidden" name="case_id" value="{text(case['id'])}">
          <input type="hidden" name="state" value="{text(selected_state)}">
          <input type="hidden" name="case_category" value="{text(selected_category)}">
          <input type="hidden" name="court_level" value="{text(selected_court_level)}">
          <select name="lawyer_id">{assignment_select}</select>
          <button class="button primary small" type="submit">Assign</button>
        </form>
        """
        if show_assignment and case["permission_to_share"] and assignment_candidates
        else ""
    )
    progress_form = (
        f"""
        <form class="assign-form" method="post" action="/progress">
          <input type="hidden" name="case_id" value="{text(case['id'])}">
          <input type="hidden" name="origin" value="{text(progress_origin)}">
          <input type="hidden" name="state" value="{text(selected_state)}">
          <input type="hidden" name="case_category" value="{text(selected_category)}">
          <input type="hidden" name="court_level" value="{text(selected_court_level)}">
          <select name="case_stage">
            {render_select_options(CASE_STAGE_OPTIONS, case.get("case_stage", "intake_received"))}
          </select>
          <input type="date" name="next_hearing_date" value="{text(case.get("next_hearing_date", ""))}">
          <button class="button secondary small" type="submit">Update</button>
        </form>
        """
        if show_progress_form
        else ""
    )
    case_tags = case.get("feature_graph", {}).get("tags", [])[:6]
    return f"""
    <article class="case-card">
      <div class="card-head">
        <div>
          <p class="eyebrow">Case #{text(case["id"])} · {text(case["source"].upper())}</p>
          <h2>{text(case["full_name"])}</h2>
        </div>
        <span class="status-pill">{text(CASE_STAGE_LABELS.get(case.get("case_stage", ""), case.get("case_stage", "")).lower())}</span>
      </div>
      <div class="meta-grid">
        <span>{text(case["state"])}</span>
        <span>{text(case["case_category"])}</span>
        <span>{text(COURT_LEVEL_LABELS.get(case.get("court_level", ""), case.get("court_level", "") or "Not set"))}</span>
        <span>{text(case["preferred_language"] or "Language not set")}</span>
      </div>
      <p class="case-summary">{text(case["summary"])}</p>
      <div class="meta-grid">
        <span>Phone: {text(case["contact_phone"])}</span>
        <span>Eligibility: {text(ELIGIBILITY_LABELS.get(case.get("applicant_category", ""), case.get("applicant_category", "") or "Not set"))}</span>
        <span>Next hearing: {text(case.get("next_hearing_date") or "Not set")}</span>
        <span>Assigned lawyer: {text(case.get("assigned_lawyer_name") or "Not assigned yet")}</span>
      </div>
      {render_label_list("Auto tags", case_tags, empty_label="Generated from issue text")}
      <div class="label-stack">
        <strong>Documents</strong>
        <ul class="doc-list">{render_document_links(case.get("documents", []))}</ul>
      </div>
      <div class="split-section">
        <div>
          <h3>Suggested lawyers</h3>
          <ul class="match-list">
            {"".join(match_blocks) if match_blocks else '<li class="helper-text">No strong match yet for this case.</li>'}
          </ul>
        </div>
        <div class="action-column">
          {assignment_ui}
          {progress_form}
        </div>
      </div>
    </article>
    """


def render_dashboard(
    stats: dict[str, int],
    cases: list[dict[str, Any]],
    lawyers: list[dict[str, Any]],
    selected_state: str = "",
    selected_category: str = "",
    selected_court_level: str = "",
    success_messages: list[str] | None = None,
    user: dict[str, Any] | None = None,
) -> str:
    case_cards = "".join(
        render_case_overview_card(
            case,
            user=user,
            show_assignment=True,
            show_progress_form=True,
            selected_state=selected_state,
            selected_category=selected_category,
            selected_court_level=selected_court_level,
            progress_origin="dashboard",
        )
        for case in cases
    )
    body = f"""
    <section class="form-header">
      <p class="eyebrow">Admin dashboard</p>
      <h1>Match cases, assign lawyers, and manage secure access to documents.</h1>
      <p class="lead">
        Admins see the full queue. Lawyers only see assigned matters. Applicants only see their own submissions.
      </p>
    </section>
    {render_messages(success_messages, "success")}
    <section class="stats-grid">
      <article class="stat-card"><span class="stat-value">{stats["total_cases"]}</span><span class="stat-label">total cases</span></article>
      <article class="stat-card"><span class="stat-value">{stats["consented_cases"]}</span><span class="stat-label">cases with consent</span></article>
      <article class="stat-card"><span class="stat-value">{stats["total_lawyers"]}</span><span class="stat-label">lawyer profiles</span></article>
      <article class="stat-card"><span class="stat-value">{stats["total_documents"]}</span><span class="stat-label">documents stored</span></article>
    </section>
    <section class="filter-card">
      <form class="filter-grid" method="get" action="/dashboard">
        <label>
          Filter by state
          <select name="state">
            {render_select_options(STATES_AND_UTS, selected_state, include_blank=True, blank_label="All states")}
          </select>
        </label>
        <label>
          Filter by category
          <select name="case_category">
            {render_select_options(CASE_CATEGORIES, selected_category, include_blank=True, blank_label="All categories")}
          </select>
        </label>
        <label>
          Filter by court
          <select name="court_level">
            {render_select_options(COURT_LEVEL_OPTIONS, selected_court_level, include_blank=True, blank_label="All courts")}
          </select>
        </label>
        <div class="filter-actions">
          <button class="button primary" type="submit">Apply filters</button>
          <a class="button secondary" href="/dashboard">Reset</a>
        </div>
      </form>
    </section>
    <section class="dashboard-layout">
      <div class="case-list">
        <h2>Case queue</h2>
        {case_cards if case_cards else '<article class="empty-card">No cases match the current filters yet.</article>'}
      </div>
      <aside class="directory-column">
        <h2>Lawyer directory</h2>
        {"".join(render_lawyer_card(lawyer, show_private_history=True) for lawyer in lawyers) if lawyers else '<article class="empty-card">No lawyers have been onboarded yet.</article>'}
      </aside>
    </section>
    """
    return layout("Dashboard", body, "/dashboard", user=user)


def render_my_cases(
    cases: list[dict[str, Any]],
    user: dict[str, Any],
    success_messages: list[str] | None = None,
) -> str:
    body = f"""
    <section class="form-header">
      <p class="eyebrow">Applicant workspace</p>
      <h1>My cases</h1>
      <p class="lead">Only you, the assigned lawyer, and admins can access your uploaded documents.</p>
    </section>
    {render_messages(success_messages, "success")}
    <section class="case-list">
      {"".join(render_case_overview_card(case, user=user) for case in cases) if cases else '<article class="empty-card">You have not submitted any cases yet.</article>'}
    </section>
    """
    return layout("My cases", body, "/my-cases", user=user)


def render_my_assignments(
    cases: list[dict[str, Any]],
    user: dict[str, Any],
    lawyer_profile: dict[str, Any] | None,
    success_messages: list[str] | None = None,
) -> str:
    if not lawyer_profile:
        body = """
        <section class="form-header">
          <p class="eyebrow">Lawyer workspace</p>
          <h1>Complete your lawyer profile first.</h1>
          <p class="lead">Assignments and secure document access appear here after your profile is saved and a case is assigned to you.</p>
          <div class="form-actions">
            <a class="button primary" href="/lawyers/onboard">Complete lawyer profile</a>
          </div>
        </section>
        """
        return layout("My assignments", body, "/my-assignments", user=user)

    body = f"""
    <section class="form-header">
      <p class="eyebrow">Lawyer workspace</p>
      <h1>My assignments</h1>
      <p class="lead">Only cases assigned to you appear here, along with their protected document downloads.</p>
    </section>
    {render_messages(success_messages, "success")}
    <section class="case-list">
      {"".join(render_case_overview_card(case, user=user, show_progress_form=True, progress_origin='assignments') for case in cases) if cases else '<article class="empty-card">No cases are assigned to you yet.</article>'}
    </section>
    """
    return layout("My assignments", body, "/my-assignments", user=user)


def render_whatsapp_guide(user: dict[str, Any] | None = None) -> str:
    sample_payload = json.dumps(
        {
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
            "next_hearing_date": "",
            "permission_to_share": True,
        },
        indent=2,
    )
    body = f"""
    <section class="form-header">
      <p class="eyebrow">WhatsApp intake path</p>
      <h1>Use the same matching and security pipeline for chat-based intake.</h1>
      <p class="lead">
        A WhatsApp bot can feed the same structured case flow, while document access still stays account- and role-restricted inside the portal.
      </p>
    </section>
    <section class="two-column">
      <article class="card">
        <h2>Suggested user journey</h2>
        <ol class="plain-list">
          <li>The person sends a message like "Need legal help".</li>
          <li>The bot asks for state, issue type, court level, summary, consent, and optionally eligibility group.</li>
          <li>The bot posts the structured payload to <code>/api/whatsapp/intake</code>.</li>
          <li>The case appears in the dashboard and the applicant can later view it securely after account linking.</li>
        </ol>
      </article>
      <article class="card">
        <h2>Example payload</h2>
        <pre><code>{text(sample_payload)}</code></pre>
      </article>
    </section>
    """
    return layout("WhatsApp flow", body, "/whatsapp", user=user)
