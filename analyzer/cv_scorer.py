import re
from typing import Dict, List, Tuple, Optional
from utiliy.keyword import KEYWORDS



# ------------------ SCORING CONSTANTS ------------------
CONTACT_EMAIL_SCORE = 40
CONTACT_PHONE_SCORE = 30
CONTACT_LOCATION_SCORE = 20
CONTACT_LINK_SCORE = 10

EXPERIENCE_DETAIL_SCORE = 30
EXPERIENCE_DATE_SCORE = 25
EXPERIENCE_ACTION_SCORE = 25
EXPERIENCE_METRIC_SCORE = 20

EDU_DEGREE_SCORE = 40
EDU_INSTITUTE_SCORE = 30
EDU_YEAR_SCORE = 20
EDU_HONORS_SCORE = 10

SKILL_COUNT_MAX_SCORE = 40
SKILL_TECH_SCORE = 30
SKILL_SOFT_SCORE = 20
SKILL_CATEGORY_SCORE = 10


class CVScorer:
    def __init__(self):
        self.weights = {
            "contact": 0.15,
            "experience": 0.35,
            "education": 0.25,
            "skills": 0.15,
            "format": 0.10
        }

    # --------------------------------------------------
    # CONTACT INFO
    # --------------------------------------------------
    def score_contact_info(self, contact_info: str, raw_text: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []

        text = f"{contact_info}\n{raw_text}".lower()

        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        phone_pattern = r"(?:\+\d{1,3}\s?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"

        if re.search(email_pattern, text):
            score += CONTACT_EMAIL_SCORE
        else:
            suggestions.append("Add a professional email address.")

        if re.search(phone_pattern, text):
            score += CONTACT_PHONE_SCORE
        else:
            suggestions.append("Include a phone number.")

        if any(k in text for k in ["city", "country", "location", "address"]):
            score += CONTACT_LOCATION_SCORE
        else:
            suggestions.append("Add your location (city/country).")

        if any(k in text for k in ["linkedin", "github", "portfolio"]):
            score += CONTACT_LINK_SCORE
        else:
            suggestions.append("Add LinkedIn, GitHub, or portfolio links.")

        return min(score, 100), suggestions

    # --------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------
    def score_experience(self, experience: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []

        if not experience.strip():
            return 0, ["Add a work experience section with roles and achievements."]

        lines = [l.strip() for l in experience.split("\n") if l.strip()]

        if len(lines) >= 3:
            score += EXPERIENCE_DETAIL_SCORE
        else:
            suggestions.append("Add more detailed bullet points to your experience.")

        year_pattern = r"\b(19|20)\d{2}\b"
        if any(re.search(year_pattern, line) for line in lines):
            score += EXPERIENCE_DATE_SCORE
        else:
            suggestions.append("Include employment dates for each role.")

        action_verbs = [
            "developed", "designed", "implemented", "managed",
            "led", "optimized", "improved", "built", "created"
        ]
        if any(v in experience.lower() for v in action_verbs):
            score += EXPERIENCE_ACTION_SCORE
        else:
            suggestions.append("Use strong action verbs to describe your work.")

        metric_pattern = r"\b\d+%|\$\d+|\b\d+\s?(k|m|million|thousand)\b"
        if re.search(metric_pattern, experience.lower()):
            score += EXPERIENCE_METRIC_SCORE
        else:
            suggestions.append("Add measurable results (numbers, %, impact).")

        return min(score, 100), suggestions

    # --------------------------------------------------
    # EDUCATION
    # --------------------------------------------------
    def score_education(self, education: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []

        if not education.strip():
            return 0, ["Add your education details."]

        text = education.lower()

        degree_keywords = [
            "bachelor", "master", "phd", "degree", "bs", "ba", "ms", "mba"
        ]
        if any(k in text for k in degree_keywords):
            score += EDU_DEGREE_SCORE
        else:
            suggestions.append("Specify your degree type.")

        if len(education.split("\n")) >= 2:
            score += EDU_INSTITUTE_SCORE
        else:
            suggestions.append("Include institution name.")

        if re.search(r"\b(19|20)\d{2}\b", text):
            score += EDU_YEAR_SCORE
        else:
            suggestions.append("Add graduation or expected graduation year.")

        if any(k in text for k in ["gpa", "honors", "cum laude", "dean"]):
            score += EDU_HONORS_SCORE
        else:
            suggestions.append("Add GPA or academic honors if strong.")

        return min(score, 100), suggestions

    # --------------------------------------------------
    # SKILLS
    # --------------------------------------------------
    def score_skills(self, skills: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []

        if not skills.strip():
            return 0, ["Add a skills section."]

        skill_list = re.split(r"[,\n•\-*]+", skills)
        skill_list = [s.strip().lower() for s in skill_list if s.strip()]
        count = len(skill_list)

        if count >= 8:
            score += SKILL_COUNT_MAX_SCORE
        elif count >= 5:
            score += 30
        elif count >= 3:
            score += 20
        else:
            suggestions.append("List at least 5–10 relevant skills.")

        tech_keywords = [
            "python", "java", "sql", "javascript", "tensorflow",
            "pytorch", "aws", "react", "database"
        ]
        if any(s in skill_list for s in tech_keywords):
            score += SKILL_TECH_SCORE
        else:
            suggestions.append("Add more technical skills relevant to your field.")

        soft_keywords = [
            "communication", "teamwork", "leadership",
            "problem solving", "analytical"
        ]
        if any(s in skill_list for s in soft_keywords):
            score += SKILL_SOFT_SCORE
        else:
            suggestions.append("Add key soft skills.")

        if ":" in skills or "technical" in skills.lower():
            score += SKILL_CATEGORY_SCORE
        else:
            suggestions.append("Group skills into categories (Technical / Soft).")

        return min(score, 100), suggestions

    # --------------------------------------------------
    # FORMAT
    # --------------------------------------------------
    def score_format(self, raw_text: str) -> Tuple[float, List[str]]:
        score = 0
        suggestions = []

        word_count = len(raw_text.split())
        if 200 <= word_count <= 800:
            score += 30
        else:
            suggestions.append("Keep CV length between 1–2 pages.")

        sections = ["experience", "education", "skills", "summary", "projects"]
        if sum(1 for s in sections if s in raw_text.lower()) >= 4:
            score += 25
        else:
            suggestions.append("Use clear section headers.")

        if len([l for l in raw_text.split("\n") if l.strip()]) > 12:
            score += 25
        else:
            suggestions.append("Improve spacing and structure.")

        if any(c in raw_text for c in ["•", "-", "*"]):
            score += 20
        else:
            suggestions.append("Use bullet points for readability.")

        return min(score, 100), suggestions

    # --------------------------------------------------
    # JOB MATCHING
    # --------------------------------------------------
    @staticmethod
    def job_match_suggestions(resume_text: str, job_name: str) -> List[str]:
        suggestions = []
        job_tokens = set(job_name.lower().split())
        resume_text = resume_text.lower()

        relevant_skills = []
        for key, skills in KEYWORDS.items():
            if job_tokens & set(key.split()):
                relevant_skills = skills
                break

        missing = [s for s in relevant_skills if s not in resume_text]
        if missing:
            suggestions.append(
                f"Add missing skills for {job_name}: {', '.join(missing)}."
            )

        if "project" not in resume_text:
            suggestions.append("Include relevant projects to show practical experience.")

        return suggestions

    # --------------------------------------------------
    # FINAL SCORING
    # --------------------------------------------------
    def score_cv(self, parsed_data: Dict, job_name: Optional[str] = "") -> Dict:
        scores = {}
        suggestions = []

        scores["contact"], s = self.score_contact_info(
            parsed_data.get("contact_info", ""),
            parsed_data.get("raw_text", "")
        )
        suggestions.extend(s)

        scores["experience"], s = self.score_experience(parsed_data.get("experience", ""))
        suggestions.extend(s)

        scores["education"], s = self.score_education(parsed_data.get("education", ""))
        suggestions.extend(s)

        scores["skills"], s = self.score_skills(parsed_data.get("skills", ""))
        suggestions.extend(s)

        scores["format"], s = self.score_format(parsed_data.get("raw_text", ""))
        suggestions.extend(s)

        overall_score = round(
            sum(scores[k] * self.weights[k] for k in self.weights), 1
        )

        if job_name:
            suggestions.extend(
                self.job_match_suggestions(parsed_data.get("raw_text", ""), job_name)
            )

        return {
            "overall_score": overall_score,
            "section_scores": scores,
            "suggestions": suggestions[:10]  # limit noise
        }