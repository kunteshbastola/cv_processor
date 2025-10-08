import re
from typing import Dict, List, Tuple

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
    
    def score_contact_info(self, contact_info: str, raw_text: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []
        
        # Check for email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, contact_info):
            score += 40
        else:
            suggestions.append("Add a professional email address")
        
        # Check for phone number
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\b(?:\+\d{1,3}\s?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        ]
        if any(re.search(pattern, contact_info) for pattern in phone_patterns):
            score += 30
        else:
            suggestions.append("Include a phone number")
        
        # Check for location/address
        location_keywords = ['address', 'city', 'state', 'country', 'location']
        if any(keyword in raw_text.lower() for keyword in location_keywords):
            score += 20
        else:
            suggestions.append("Consider adding your location or city")
        
        # Check for LinkedIn or professional profiles
        if 'linkedin' in raw_text.lower() or 'github' in raw_text.lower():
            score += 10
        else:
            suggestions.append("Add LinkedIn profile or other professional links")
        
        return min(score, 100), suggestions
    
    def score_experience(self, experience: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []
        
        if not experience.strip():
            return 0, ["Add work experience section with job titles, companies, and dates"]
        
        # Check for job titles and companies
        lines = [line.strip() for line in experience.split('\n') if line.strip()]
        
        if len(lines) >= 2:
            score += 30
        else:
            suggestions.append("Provide more detailed work experience")
        
        # Check for dates
        date_patterns = [
            r'\b\d{4}\b',  # Year
            r'\b\d{1,2}/\d{4}\b',  # Month/Year
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}\b'  # Month Year
        ]
        if any(re.search(pattern, experience) for pattern in date_patterns):
            score += 25
        else:
            suggestions.append("Include employment dates (start/end dates)")
        
        # Check for action verbs and achievements
        action_verbs = ['managed', 'developed', 'implemented', 'created', 'led', 'improved', 
                       'achieved', 'increased', 'decreased', 'streamlined', 'coordinated']
        if any(verb in experience.lower() for verb in action_verbs):
            score += 25
        else:
            suggestions.append("Use strong action verbs to describe your accomplishments")
        
        # Check for quantifiable results
        number_patterns = [r'\b\d+%\b', r'\b\$\d+\b', r'\b\d+\s*(million|thousand|k)\b']
        if any(re.search(pattern, experience, re.IGNORECASE) for pattern in number_patterns):
            score += 20
        else:
            suggestions.append("Include quantifiable achievements and results")
        
        return min(score, 100), suggestions
    
    def score_education(self, education: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []
        
        if not education.strip():
            return 0, ["Add education section with degree, institution, and graduation date"]
        
        # Check for degree keywords
        degree_keywords = ['bachelor', 'master', 'phd', 'doctorate', 'diploma', 'certificate',
                          'degree', 'bs', 'ba', 'ms', 'ma', 'mba']
        if any(keyword in education.lower() for keyword in degree_keywords):
            score += 40
        else:
            suggestions.append("Specify your degree type (Bachelor's, Master's, etc.)")
        
        # Check for institution name
        if len(education.split('\n')) >= 2:
            score += 30
        else:
            suggestions.append("Include the name of your educational institution")
        
        # Check for graduation date/year
        if re.search(r'\b\d{4}\b', education):
            score += 20
        else:
            suggestions.append("Add graduation year or expected graduation date")
        
        # Check for GPA or honors
        gpa_patterns = [r'\bgpa\s*:?\s*\d+\.\d+\b', r'\b\d+\.\d+\s*gpa\b']
        honors_keywords = ['magna cum laude', 'summa cum laude', 'cum laude', 'honors', 'dean\'s list']
        if any(re.search(pattern, education, re.IGNORECASE) for pattern in gpa_patterns) or \
           any(keyword in education.lower() for keyword in honors_keywords):
            score += 10
        else:
            suggestions.append("Consider adding GPA (if 3.5+) or academic honors")
        
        return min(score, 100), suggestions
    
    def score_skills(self, skills: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []
        
        if not skills.strip():
            return 0, ["Add a skills section with relevant technical and soft skills"]
        
        # Count number of skills (rough estimate by commas, bullets, or new lines)
        skill_count = len(re.findall(r'[,\n•\-\*]', skills)) + 1
        
        if skill_count >= 8:
            score += 40
        elif skill_count >= 5:
            score += 30
        elif skill_count >= 3:
            score += 20
        else:
            suggestions.append("List more relevant skills (aim for 5-10 skills)")
        
        # Check for technical skills
        tech_keywords = ['python', 'java', 'javascript', 'sql', 'html', 'css', 'react',
                        'programming', 'software', 'database', 'cloud', 'aws', 'azure']
        if any(keyword in skills.lower() for keyword in tech_keywords):
            score += 30
        else:
            suggestions.append("Include relevant technical skills for your field")
        
        # Check for soft skills
        soft_keywords = ['communication', 'leadership', 'teamwork', 'problem solving',
                        'analytical', 'creative', 'organized', 'detail-oriented']
        if any(keyword in skills.lower() for keyword in soft_keywords):
            score += 20
        else:
            suggestions.append("Add important soft skills like communication and teamwork")
        
        # Check for categorization
        if 'technical' in skills.lower() or 'soft' in skills.lower() or ':' in skills:
            score += 10
        else:
            suggestions.append("Consider organizing skills into categories (Technical, Soft Skills, etc.)")
        
        return min(score, 100), suggestions
    
    def score_format(self, raw_text: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []
        
        # Check document length
        word_count = len(raw_text.split())
        if 200 <= word_count <= 800:
            score += 30
        elif word_count < 200:
            suggestions.append("CV seems too short - aim for 1-2 pages")
        else:
            suggestions.append("CV might be too long - keep it concise (1-2 pages)")
        
        # Check for section headers
        section_keywords = ['experience', 'education', 'skills', 'summary', 'objective']
        section_count = sum(1 for keyword in section_keywords if keyword in raw_text.lower())
        if section_count >= 4:
            score += 25
        else:
            suggestions.append("Organize CV with clear section headers")
        
        # Check for consistent formatting (basic check)
        lines = raw_text.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        if len(non_empty_lines) > 10:
            score += 25
        else:
            suggestions.append("Ensure proper formatting with clear structure")
        
        # Check for special characters that might indicate formatting
        if any(char in raw_text for char in ['•', '-', '*', '|']):
            score += 20
        else:
            suggestions.append("Use bullet points to improve readability")
        
        return min(score, 100), suggestions
    
    def calculate_overall_score(self, scores: Dict[str, float]) -> float:
        overall = sum(scores[key] * self.weights[key] for key in self.weights.keys())
        return round(overall, 1)
    
    def generate_suggestions(self, all_suggestions: Dict[str, List[str]]) -> str:
        suggestion_text = "## Improvement Suggestions\n\n"
        
        for section, suggestions in all_suggestions.items():
            if suggestions:
                suggestion_text += f"### {section.title()} Section:\n"
                for suggestion in suggestions:
                    suggestion_text += f"- {suggestion}\n"
                suggestion_text += "\n"
        
        # Add general tips
        suggestion_text += "### General Tips:\n"
        suggestion_text += "- Tailor your CV to the specific job you're applying for\n"
        suggestion_text += "- Use a clean, professional font and consistent formatting\n"
        suggestion_text += "- Proofread carefully for spelling and grammar errors\n"
        suggestion_text += "- Keep your CV to 1-2 pages maximum\n"
        
        return suggestion_text
    
    def score_cv(self, parsed_data: Dict) -> Dict:
        scores = {}
        all_suggestions = {}
        
        # Score each section
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

        
        # Calculate overall score
        overall_score = self.calculate_overall_score(scores)
        
        # Generate suggestions
        suggestions = self.generate_suggestions(all_suggestions)
        
        return {
            'overall_score': overall_score,
            'scores': scores,
            'suggestions': suggestions
        }