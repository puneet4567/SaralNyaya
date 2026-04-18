STATES_AND_UTS = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
]

LAWYER_STATE_OPTIONS = ["Pan-India", *STATES_AND_UTS]

BAR_COUNCIL_OPTIONS = [
    "Andhra Pradesh",
    "Assam, Nagaland, Mizoram, Arunachal Pradesh, Sikkim",
    "Bihar",
    "Chhattisgarh",
    "Delhi",
    "Gujarat",
    "Himachal Pradesh",
    "Jammu and Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra and Goa",
    "Manipur",
    "Meghalaya",
    "Odisha",
    "Punjab and Haryana",
    "Rajasthan",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Other",
]

CASE_CATEGORIES = [
    "Domestic violence / women's safety",
    "Family / marriage / maintenance",
    "Property / land dispute",
    "Labour / wage issue",
    "Police complaint / FIR",
    "Consumer grievance",
    "Housing / tenant issue",
    "Documentation / identity issue",
    "SC/ST Atrocities Act support",
    "Senior citizen support",
    "Child protection",
    "Other",
]

LANGUAGE_OPTIONS = [
    "Hindi",
    "English",
    "Bengali",
    "Gujarati",
    "Kannada",
    "Malayalam",
    "Marathi",
    "Odia",
    "Punjabi",
    "Tamil",
    "Telugu",
    "Urdu",
]

URGENCY_OPTIONS = [
    ("critical", "Critical: hearing, threat, violence, detention, or eviction soon"),
    ("high", "High: legal help needed within a few days"),
    ("medium", "Medium: issue is active but not immediate"),
    ("low", "Low: guidance is needed, no urgent deadline"),
]

INCOME_BANDS = [
    "Below Rs. 1.5 lakh / year",
    "Rs. 1.5-3 lakh / year",
    "Rs. 3-5 lakh / year",
    "Above Rs. 5 lakh / year",
    "Prefer not to say",
]

PREFERRED_CHANNELS = [
    ("phone", "Phone call"),
    ("whatsapp", "WhatsApp"),
    ("email", "Email"),
]

FEE_MODELS = [
    ("pro_bono", "Pro bono"),
    ("low_bono", "Low bono / nominal fee"),
    ("mixed", "Depends on the matter"),
]

COURT_LEVEL_OPTIONS = [
    ("pre_litigation", "Pre-litigation / advice only"),
    ("police_admin", "Police / authority / documentation issue"),
    ("district_court", "District / trial court"),
    ("family_court", "Family court"),
    ("tribunal", "Tribunal / labour / consumer forum"),
    ("high_court", "High Court"),
    ("supreme_court", "Supreme Court"),
]

CASE_STAGE_OPTIONS = [
    ("intake_received", "Intake received"),
    ("eligibility_review", "Eligibility / facts review"),
    ("lawyer_matched", "Lawyer matched"),
    ("advice_in_progress", "Advice / drafting in progress"),
    ("hearing_scheduled", "Hearing scheduled"),
    ("closed", "Closed"),
]

ELIGIBILITY_OPTIONS = [
    ("scheduled_caste", "Scheduled Caste"),
    ("scheduled_tribe", "Scheduled Tribe"),
    ("trafficking_or_begar", "Victim of trafficking or begar"),
    ("woman_or_child", "Woman or child"),
    ("person_with_disability", "Person with disability"),
    ("person_in_custody", "Person in custody"),
    ("industrial_workman", "Industrial workman"),
    ("disaster_or_caste_atrocity", "Victim of disaster, ethnic violence, or caste atrocity"),
    ("low_income", "Low income / BPL / income certificate"),
    ("senior_citizen_or_other", "Senior citizen or other eligible group"),
    ("not_sure", "Not sure, need help checking eligibility"),
]

ELIGIBILITY_PROOF_HINTS = {
    "scheduled_caste": "Scheduled Caste certificate",
    "scheduled_tribe": "Scheduled Tribe certificate",
    "trafficking_or_begar": "Court, police, or legal document showing this status",
    "woman_or_child": "Government ID showing age or gender where relevant",
    "person_with_disability": "Disability certificate",
    "person_in_custody": "Court order or custody documents",
    "industrial_workman": "Employment ID or work certificate",
    "disaster_or_caste_atrocity": "Government or legal document showing the incident/status",
    "low_income": "Income certificate or BPL card",
    "senior_citizen_or_other": "Government ID or other supporting document",
    "not_sure": "No proof needed right now; the platform can help screen eligibility later",
}
