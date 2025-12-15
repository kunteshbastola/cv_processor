import re
from collections import Counter
from utiliy.keyword import KEYWORDS


def clean_text(text):
    """Lowercase text and remove non-alphabetic characters (keep spaces)."""
    return re.sub(r'[^a-z ]', '', text.lower())  # Keep only lowercase letters and spaces

def normalize_job_name(name):
    """Normalize job name for comparison."""
    if not name:
        return ""
    # Convert to lowercase, remove punctuation, normalize spaces
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)  # Remove punctuation
    name = re.sub(r'\s+', ' ', name)     # Normalize multiple spaces
    return name

def find_matching_job_title(user_job_title, keyword_dict):
    """
    Find the best matching job title from keywords dictionary.
    Returns the normalized key from KEYWORDS dict.
    """
    user_normalized = normalize_job_name(user_job_title)
    
    # First try exact match
    for job_title in keyword_dict.keys():
        if normalize_job_name(job_title) == user_normalized:
            return job_title
    
    # Try partial match (user input might be longer)
    for job_title in keyword_dict.keys():
        job_normalized = normalize_job_name(job_title)
        # Check if job title contains user input or vice versa
        if job_normalized in user_normalized or user_normalized in job_normalized:
            return job_title
    
    # Try word overlap
    user_words = set(user_normalized.split())
    best_match = None
    best_score = 0
    
    for job_title in keyword_dict.keys():
        job_normalized = normalize_job_name(job_title)
        job_words = set(job_normalized.split())
        
        # Calculate overlap
        common_words = user_words.intersection(job_words)
        if common_words:
            score = len(common_words) / max(len(user_words), len(job_words))
            if score > best_score:
                best_score = score
                best_match = job_title
    
    # Return if reasonable match found
    if best_score >= 0.3:  # At least 30% word overlap
        return best_match
    
    return None

def generate_resume_suggestions(cv_text, job_name):
    """Generate suggestions based on missing keywords for a job role."""
    if not cv_text or not cv_text.strip():
        return "The CV text is empty. Please provide a resume for analysis."
    
    if not job_name or not job_name.strip():
        return "Please specify a job title for targeted suggestions."
    
    # Step 1: Find matching job title in KEYWORDS
    matched_job_title = find_matching_job_title(job_name, KEYWORDS)
    
    if not matched_job_title:
        # Get list of available job titles
        available_jobs = list(KEYWORDS.keys())
        return f"No keyword data found for '{job_name}'. Available job roles: {', '.join(available_jobs)}"
    
    # Step 2: Get expected keywords for this job
    expected_keywords = KEYWORDS[matched_job_title]
    
    # Step 3: Clean CV text for keyword search
    cleaned_cv_text = clean_text(cv_text)
    
    # Step 4: Check which keywords are present/missing
    present_keywords = []
    missing_keywords = []
    
    for keyword in expected_keywords:
        # Clean keyword and check
        keyword_clean = clean_text(keyword)
        # Search for the keyword in CV
        if keyword_clean in cleaned_cv_text:
            present_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)
    
    # Step 5: Generate suggestions
    suggestions = []
    
    # Header
    suggestions.append(f"📊 Resume Analysis for {job_name} → Matched to: {matched_job_title}")
    suggestions.append("=" * 50)
    
    # Present keywords
    if present_keywords:
        suggestions.append("\n✅ STRENGTHS - Keywords found in your resume:")
        for i, keyword in enumerate(present_keywords[:8], 1):  # Show top 8
            suggestions.append(f"   {i}. {keyword}")
        if len(present_keywords) > 8:
            suggestions.append(f"   ... and {len(present_keywords) - 8} more")
    
    # Missing keywords
    if missing_keywords:
        suggestions.append(f"\n📝 IMPROVEMENTS - Add these {matched_job_title} keywords:")
        
        # Group by priority (common keywords first)
        priority_keywords = missing_keywords[:10]  # Top 10 most important
        
        for i, keyword in enumerate(priority_keywords, 1):
            suggestions.append(f"   {i}. {keyword}")
        
        if len(missing_keywords) > 10:
            suggestions.append(f"   ... and {len(missing_keywords) - 10} more")
        
        # Actionable advice
        suggestions.append("\n💡 HOW TO INCORPORATE:")
        suggestions.append("   1. Add skills section with these keywords")
        suggestions.append("   2. Mention in project descriptions")
        suggestions.append("   3. Include in experience bullet points")
        suggestions.append("   4. Add to summary/objective statement")
    
    # Score calculation
    match_percentage = (len(present_keywords) / len(expected_keywords)) * 100
    suggestions.append(f"\n📈 KEYWORD MATCH SCORE: {match_percentage:.1f}%")
    suggestions.append(f"   ({len(present_keywords)} of {len(expected_keywords)} keywords found)")
    
    # Rating
    if match_percentage >= 80:
        suggestions.append("🎯 EXCELLENT MATCH! Your resume is well-optimized.")
    elif match_percentage >= 60:
        suggestions.append("👍 GOOD MATCH! Consider adding a few more keywords.")
    elif match_percentage >= 40:
        suggestions.append("⚠️ FAIR MATCH! Significant improvements needed.")
    else:
        suggestions.append("🚨 POOR MATCH! Major optimization required.")
    
    return "\n".join(suggestions)

# ==================== TESTING FUNCTION ====================
def test_job_matching():
    """Test the job matching with various inputs."""
    test_cases = [
        ("DATA ANALYST", "data analyst"),
        ("Data Analyst", "data analyst"),
        ("data analyst", "data analyst"),
        ("Senior Data Analyst", "data analyst"),
        ("WEB DEVELOPER", "web developer"),
        ("Web Developer", "web developer"),
        ("Frontend Web Developer", "web developer"),
        ("SOFTWARE ENGINEER", "software engineer"),
        ("Software Engineer", "software engineer"),
        ("Java Software Engineer", "software engineer"),
        ("MOBILE DEVELOPER", "mobile developer"),
        ("iOS Mobile Developer", "mobile developer"),
        ("DEVOPS ENGINEER", "devops engineer"),
        ("Cloud DevOps Engineer", "devops engineer"),
        ("Invalid Job", None),  # Should return None
    ]
    
    print("Testing Job Title Matching:")
    print("=" * 50)
    
    for input_job, expected_match in test_cases:
        result = find_matching_job_title(input_job, KEYWORDS)
        status = "✅ PASS" if result == expected_match else "❌ FAIL"
        print(f"{status} | Input: '{input_job:25}' → Matched: '{result}'")
    
    print("\n" + "=" * 50)
    
    # Test suggestions
    sample_cv = """
    I am a data analyst with 3 years of experience.
    I use SQL for data querying and Excel for analysis.
    I have basic knowledge of Python and statistics.
    I've worked with data visualization tools.
    """
    
    print("\nTesting Suggestions Generation:")
    print("=" * 50)
    suggestions = generate_resume_suggestions(sample_cv, "DATA ANALYST")
    print(suggestions)

# Run tests if this file is executed directly
if __name__ == "__main__":
    test_job_matching()