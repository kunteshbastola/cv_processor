import re
from typing import Dict, List, Tuple, Optional

# Example JOB_KEYWORDS dictionary for reference
JOB_KEYWORDS = {
    'software engineer': ['python', 'java', 'git', 'sql', 'oop', 'algorithms'],
    'data analyst': ['excel', 'sql', 'python', 'statistics', 'visualization'],
    'machine learning engineer': ['python', 'tensorflow', 'pytorch', 'ml', 'data preprocessing']
}

class CVScorer:
    def __init__(self):
        self.max_score = 100
        self.weights = {
            'contact': 0.15,
            'experience': 0.35,
            'education': 0.25,
            'skills': 0.15,
            'format': 0.10
        }

    # ----------- CONTACT INFO SCORING -----------
    def score_contact_info(self, contact_info: str, raw_text: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []

        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\b(?:\+\d{1,3}\s?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        ]
        location_keywords = ['address', 'city', 'state', 'country', 'location']

        if re.search(email_pattern, contact_info):
            score += 40
        else:
            suggestions.append("Add a professional email address")

        if any(re.search(p, contact_info) for p in phone_patterns):
            score += 30
        else:
            suggestions.append("Include a phone number")

        if any(k in raw_text.lower() for k in location_keywords):
            score += 20
        else:
            suggestions.append("Consider adding your location or city")

        if 'linkedin' in raw_text.lower() or 'github' in raw_text.lower():
            score += 10
        else:
            suggestions.append("Add LinkedIn profile or other professional links")

        return min(score, 100), suggestions

    # ----------- EXPERIENCE SCORING -----------
    def score_experience(self, experience: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []

        if not experience.strip():
            return 0, ["Add work experience section with job titles, companies, and dates"]

        lines = [line.strip() for line in experience.split('\n') if line.strip()]
        if len(lines) >= 2:
            score += 30
        else:
            suggestions.append("Provide more detailed work experience")

        # Detect years (including ranges like 2022-2024)
        year_patterns = [r'\b\d{4}\b', r'\b\d{4}\s*-\s*\d{4}\b']
        if any(re.search(p, experience) for p in year_patterns):
            score += 25
        else:
            suggestions.append("Include employment dates (start/end dates)")

        action_verbs = ['managed', 'developed', 'implemented', 'created', 'led', 'improved',
                        'achieved', 'increased', 'decreased', 'streamlined', 'coordinated']
        if any(verb in experience.lower() for verb in action_verbs):
            score += 25
        else:
            suggestions.append("Use strong action verbs to describe your accomplishments")

        number_patterns = [r'\b\d+%\b', r'\b\$\d+\b', r'\b\d+\s*(million|thousand|k)\b']
        if any(re.search(p, experience, re.IGNORECASE) for p in number_patterns):
            score += 20
        else:
            suggestions.append("Include quantifiable achievements and results")

        return min(score, 100), suggestions

    # ----------- EDUCATION SCORING -----------
    def score_education(self, education: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []

        if not education.strip():
            return 0, ["Add education section with degree, institution, and graduation date"]

        degree_keywords = ['bachelor', 'master', 'phd', 'doctorate', 'diploma', 'certificate',
                           'degree', 'bs', 'ba', 'ms', 'ma', 'mba']
        if any(k in education.lower() for k in degree_keywords):
            score += 40
        else:
            suggestions.append("Specify your degree type (Bachelor's, Master's, etc.)")

        if len(education.split('\n')) >= 2:
            score += 30
        else:
            suggestions.append("Include the name of your educational institution")

        if re.search(r'\b\d{4}\b', education):
            score += 20
        else:
            suggestions.append("Add graduation year or expected graduation date")

        gpa_patterns = [r'\bgpa\s*:?\s*\d+\.\d+\b', r'\b\d+\.\d+\s*gpa\b']
        honors_keywords = ['magna cum laude', 'summa cum laude', 'cum laude', 'honors', 'dean\'s list']
        if any(re.search(p, education, re.IGNORECASE) for p in gpa_patterns) or \
           any(k in education.lower() for k in honors_keywords):
            score += 10
        else:
            suggestions.append("Consider adding GPA (if 3.5+) or academic honors")

        return min(score, 100), suggestions

    # ----------- SKILLS SCORING -----------
    def score_skills(self, skills: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []

        if not skills.strip():
            return 0, ["Add a skills section with relevant technical and soft skills"]

        skill_count = len(re.findall(r'[,\n•\-\*]', skills)) + 1
        if skill_count >= 8:
            score += 40
        elif skill_count >= 5:
            score += 30
        elif skill_count >= 3:
            score += 20
        else:
            suggestions.append("List more relevant skills (aim for 5-10 skills)")

        tech_keywords = ['python', 'java', 'javascript', 'sql', 'html', 'css', 'react',
                         'programming', 'software', 'database', 'cloud', 'aws', 'azure']
        if any(k in skills.lower() for k in tech_keywords):
            score += 30
        else:
            suggestions.append("Include relevant technical skills for your field")

        soft_keywords = ['communication', 'leadership', 'teamwork', 'problem solving',
                         'analytical', 'creative', 'organized', 'detail-oriented']
        if any(k in skills.lower() for k in soft_keywords):
            score += 20
        else:
            suggestions.append("Add important soft skills like communication and teamwork")

        if 'technical' in skills.lower() or 'soft' in skills.lower() or ':' in skills:
            score += 10
        else:
            suggestions.append("Consider organizing skills into categories (Technical, Soft Skills, etc.)")

        return min(score, 100), suggestions

    # ----------- FORMAT SCORING -----------
    def score_format(self, raw_text: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []

        word_count = len(raw_text.split())
        if 200 <= word_count <= 800:
            score += 30
        elif word_count < 200:
            suggestions.append("CV seems too short - aim for 1-2 pages")
        else:
            suggestions.append("CV might be too long - keep it concise (1-2 pages)")

        section_keywords = ['experience', 'education', 'skills', 'summary', 'objective']
        section_count = sum(1 for k in section_keywords if k in raw_text.lower())
        if section_count >= 4:
            score += 25
        else:
            suggestions.append("Organize CV with clear section headers")

        lines = raw_text.split('\n')
        non_empty_lines = [l for l in lines if l.strip()]
        if len(non_empty_lines) > 10:
            score += 25
        else:
            suggestions.append("Ensure proper formatting with clear structure")

        if any(c in raw_text for c in ['•', '-', '*', '|']):
            score += 20
        else:
            suggestions.append("Use bullet points to improve readability")

        return min(score, 100), suggestions

    # ----------- OVERALL SCORE -----------
    def calculate_overall_score(self, scores: Dict[str, float]) -> float:
        overall = sum(scores[key] * self.weights[key] for key in self.weights.keys())
        return round(overall, 1)

    # ----------- JOB-SPECIFIC SUGGESTIONS -----------
    @staticmethod
    def generate_resume_suggestions(resume_text: str, job_name: str) -> str:
        suggestions = []
        job_name_lower = job_name.lower()
        relevant_skills = []
        for key in JOB_KEYWORDS:
            if key.lower() in job_name_lower:
                relevant_skills = JOB_KEYWORDS[key]
                break

        resume_text_lower = resume_text.lower()
        missing_skills = [s for s in relevant_skills if s.lower() not in resume_text_lower]
        if missing_skills:
            suggestions.append(f"Consider adding these relevant skills for {job_name}: {', '.join(missing_skills)}.")

        if "project" not in resume_text_lower:
            suggestions.append("Include details about projects you have worked on to demonstrate practical experience.")
        if "experience" not in resume_text_lower:
            suggestions.append("Add your work experience relevant to the job role.")

        if not suggestions:
            suggestions.append("Your CV looks good for this job role, but always double-check keywords and achievements.")

        return "\n".join(suggestions)

    # ----------- FINAL CV SCORING -----------
    def score_cv(self, parsed_data: Dict, job_name: Optional[str] = "") -> Dict:
        scores = {}
        all_suggestions = {}

        scores['contact'], all_suggestions['contact'] = self.score_contact_info(
            parsed_data.get('contact_info', '') or '', parsed_data.get('raw_text', '') or ''
        )
        scores['experience'], all_suggestions['experience'] = self.score_experience(
            parsed_data.get('experience', '') or ''
        )
        scores['education'], all_suggestions['education'] = self.score_education(
            parsed_data.get('education', '') or ''
        )
        scores['skills'], all_suggestions['skills'] = self.score_skills(
            parsed_data.get('skills', '') or ''
        )
        scores['format'], all_suggestions['format'] = self.score_format(
            parsed_data.get('raw_text', '') or ''
        )

        overall_score = self.calculate_overall_score(scores)

        # Merge section suggestions
        merged_suggestions = []
        for section in all_suggestions:
            merged_suggestions.extend(all_suggestions[section])

        # Add job-specific suggestions if job_name provided
        if job_name:
            merged_suggestions.append(self.generate_resume_suggestions(parsed_data.get('raw_text', ''), job_name))

        return {
            'overall_score': overall_score,
            'scores': scores,
            'suggestions': merged_suggestions
        }
