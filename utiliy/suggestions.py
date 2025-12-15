import re
from utiliy.keyword import KEYWORDS

def normalize_text(text: str) -> str:
    """Lowercase and remove non-alphabetic characters for comparison."""
    return re.sub(r'[^a-z\s]', '', text.lower())

def find_matching_job_title(user_job_title: str) -> str:
    """Return the best matching job title from KEYWORDS."""
    if not user_job_title:
        return ""
    user_norm = normalize_text(user_job_title)
    best_match = None
    best_score = 0
    user_words = set(user_norm.split())
    
    for job_title in KEYWORDS.keys():
        job_words = set(normalize_text(job_title).split())
        overlap = len(user_words & job_words) / max(len(user_words), len(job_words))
        if overlap > best_score:
            best_score = overlap
            best_match = job_title
    if best_score >= 0.3:  # minimum 30% overlap
        return best_match
    return None

def generate_job_keyword_suggestions(resume_text: str, job_name: str) -> list:
    """Return a list of targeted keyword suggestions."""
    suggestions = []
    if not resume_text or not job_name:
        return suggestions
    
    matched_job = find_matching_job_title(job_name)
    if not matched_job:
        return [f"No keyword data available for '{job_name}'. Available jobs: {', '.join(KEYWORDS.keys())}"]
    
    expected_keywords = KEYWORDS[matched_job]
    resume_norm = normalize_text(resume_text)
    
    present = [k for k in expected_keywords if normalize_text(k) in resume_norm]
    missing = [k for k in expected_keywords if k not in present]
    
    if present:
        suggestions.append(f"Found keywords for {matched_job}: {', '.join(present[:8])}{'...' if len(present) > 8 else ''}")
    if missing:
        suggestions.append(f"Add missing keywords for {matched_job}: {', '.join(missing[:10])}{'...' if len(missing) > 10 else ''}")
        suggestions.append("Incorporate these in skills, experience, projects, or summary/objective sections.")
    
    match_percentage = len(present) / max(len(expected_keywords), 1) * 100
    suggestions.append(f"Keyword match: {match_percentage:.1f}%")
    
    return suggestions
