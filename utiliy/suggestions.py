import re
from collections import Counter
from utiliy.keyword import KEYWORDS


def clean_text(text):
    """Lowercase text and remove non-alphabetic characters (keep spaces)."""
    return re.sub(r'[^a-zA-Z ]', '', text.lower())


def normalize_job_name(name):
    """Lowercase, remove non-alphanumeric characters."""
    return re.sub(r'[^a-z0-9]', '', name.lower())


def generate_resume_suggestions(cv_text, job_name):
    if not cv_text.strip():
        return "The CV text is empty. Please provide a resume for analysis."

    normalized_job = normalize_job_name(job_name)
    
    # Find expected keywords for this job
    expected_keywords = []
    for k, v in KEYWORDS.items():
        if normalize_job_name(k) == normalized_job:
            expected_keywords = v
            break

    if not expected_keywords:
        return "No specific suggestions available for this job role."

    cleaned_cv_text = clean_text(cv_text)

    missing_keywords = [kw for kw in expected_keywords if clean_text(kw) not in cleaned_cv_text]
    present_keywords = [kw for kw in expected_keywords if clean_text(kw) in cleaned_cv_text]

    suggestions = []

    if missing_keywords:
        suggestions.extend([f"Consider including experience or knowledge in: '{kw}'." for kw in missing_keywords])
    if present_keywords:
        suggestions.append(f"Good job! Your resume mentions: {', '.join(present_keywords)}.")

    if not suggestions:
        suggestions.append("Your resume contains most essential keywords!")

    return "\n".join(suggestions)
