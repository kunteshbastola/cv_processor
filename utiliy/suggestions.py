import re
from collections import Counter
from utiliy.keyword import KEYWORDS



def clean_text(text):
    """
    Lowercase text and remove all non-alphabetic characters (keep spaces).
    """
    return re.sub(r'[^a-zA-Z ]', '', text.lower())

def normalize_job_name(name):
    """Lowercase, remove non-alphanumeric characters."""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def generate_resume_suggestions(cv_text, job_name):
    normalized_job = normalize_job_name(job_name)
    
    # Match against normalized keys in KEYWORDS
    expected_keywords = []
    for k, v in KEYWORDS.items():
        if normalize_job_name(k) == normalized_job:
            expected_keywords = v
            break

    if not expected_keywords:
        return "No specific suggestions available for this job role."

    cleaned_cv_text = clean_text(cv_text)
    cv_words = Counter(cleaned_cv_text.split())

    missing_keywords = [kw for kw in expected_keywords if kw.lower() not in cv_words]
    present_keywords = [kw for kw in expected_keywords if kw.lower() in cv_words]

    suggestions = []
    if missing_keywords:
        suggestions.extend([f"Consider including experience or knowledge in: '{kw}'." for kw in missing_keywords])
    if present_keywords:
        suggestions.append(f"Good job! Your resume already mentions: {', '.join(present_keywords)}.")

    if not suggestions:
        suggestions.append("Your resume contains most essential keywords!")

    return "\n".join(suggestions)


