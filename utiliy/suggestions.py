# utils/nlp_suggestions.py
import re
from collections import Counter
from utiliy.keyword import KEYWORDS

def clean_text(text):
    return re.sub(r'[^a-zA-Z ]', '', text.lower())

def generate_resume_suggestions(cv_text, job_name):
    job = job_name.lower()
    expected_keywords = KEYWORDS.get(job, [])
    cleaned_cv_text = clean_text(cv_text)

    # Count frequency of each word
    cv_words = Counter(cleaned_cv_text.split())

    missing_keywords = [kw for kw in expected_keywords if kw not in cv_words]

    suggestions = []
    for kw in missing_keywords:
        suggestions.append(f"Consider including experience or knowledge in: '{kw}'.")

    if not suggestions:
        suggestions.append("Your resume contains most essential keywords!")

    return suggestions
