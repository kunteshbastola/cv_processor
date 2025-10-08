import PyPDF2
import docx
import re
from typing import Dict, List, Optional
import nltk
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Download NLTK punkt tokenizer if not already available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt')
    except Exception as e:
        logger.warning(f"Could not download NLTK punkt data: {e}")


class CVParser:
    def __init__(self):
        self.contact_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone (US format)
            r'\b(?:\+\d{1,3}\s?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # International phone
            r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # Flexible international
            r'\b\d{10,15}\b'  # Digit-only phone numbers
        ]

        # Keywords for section detection
        self.experience_keywords = [
            'experience', 'work history', 'employment', 'career', 'work experience',
            'professional experience', 'employment history', 'professional background',
            'work', 'job', 'position', 'role'
        ]
        self.education_keywords = [
            'education', 'academic', 'qualification', 'degree', 'university', 'college',
            'school', 'certification', 'academic background', 'learning', 'studies'
        ]
        self.skills_keywords = [
            'skills', 'technical skills', 'competencies', 'abilities', 'technologies',
            'tools', 'expertise', 'proficiencies', 'technical competencies',
            'programming', 'software', 'languages'
        ]

    # ------------ TEXT EXTRACTION ------------ #

    def extract_text_from_pdf(self, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""

                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                    except:
                        return "Error: PDF is password protected"

                for page_num, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text += page_text + "\n"
                    except Exception as e:
                        logger.warning(f"Error reading page {page_num}: {e}")
                        continue

                return text.strip() if text.strip() else "No readable text found in PDF"
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {e}")
            return f"Error reading PDF: {str(e)}"

    def extract_text_from_docx(self, file_path: str) -> str:
        try:
            doc = docx.Document(file_path)
            text = ""

            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text += cell.text + "\n"

            return text.strip() if text.strip() else "No readable text found in document"
        except Exception as e:
            logger.error(f"Error reading DOCX {file_path}: {e}")
            return f"Error reading DOCX: {str(e)}"

    def extract_text_from_txt(self, file_path: str) -> str:
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                    return content.strip() if content.strip() else "Empty text file"
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading TXT {file_path} with {encoding}: {e}")
                continue
        return "Error: Could not decode text file with any supported encoding"

    def extract_text(self, file_path: str, file_extension: str) -> str:
        file_extension = file_extension.lower()
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_extension in ['.doc', '.docx']:
            return self.extract_text_from_docx(file_path)
        elif file_extension == '.txt':
            return self.extract_text_from_txt(file_path)
        else:
            return f"Unsupported file format: {file_extension}"

    # ------------ SECTION EXTRACTION ------------ #

    def extract_contact_info(self, text: str) -> str:
        contacts = []
        for pattern in self.contact_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            contacts.extend(matches)
        unique_contacts = list(set(contacts))
        filtered_contacts = [c.strip() for c in unique_contacts if 3 <= len(c.strip()) <= 50]
        return "; ".join(filtered_contacts) if filtered_contacts else "No contact information found"

    def extract_section(self, text: str, keywords: List[str], section_name: str, max_lines: int = 10) -> str:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        section_lines, capture, keywords_found = [], False, False

        stop_keywords = {
            'experience': ['education', 'skills', 'awards', 'certifications', 'references'],
            'education': ['experience', 'skills', 'awards', 'work', 'employment'],
            'skills': ['experience', 'education', 'awards', 'work', 'employment']
        }
        current_stop_words = stop_keywords.get(section_name.lower(), [])

        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in keywords):
                capture, keywords_found = True, True
                section_lines.append(line)
                continue
            if capture and any(stop_word in line_lower for stop_word in current_stop_words):
                if len(line) < 50 and (line.isupper() or line.istitle()):
                    break
            if capture and line and len(line) > 2:
                section_lines.append(line)
                if len(section_lines) >= max_lines:
                    break

        if not keywords_found:
            return f"No {section_name.lower()} section found"
        return '\n'.join(section_lines) if section_lines else f"No {section_name.lower()} content found"

    def extract_experience(self, text: str) -> str:
        return self.extract_section(text, self.experience_keywords, 'Experience', max_lines=15)

    def extract_education(self, text: str) -> str:
        return self.extract_section(text, self.education_keywords, 'Education', max_lines=10)

    def extract_skills(self, text: str) -> str:
        return self.extract_section(text, self.skills_keywords, 'Skills', max_lines=8)

    # ------------ MAIN PARSER ------------ #

    def parse_cv(self, file_path: str, file_extension: str) -> Dict:
        try:
            raw_text = self.extract_text(file_path, file_extension)
            if raw_text.startswith("Error:") or "Error reading" in raw_text:
                return {
                    'raw_text': raw_text,
                    'contact_info': 'Could not extract',
                    'experience': 'Could not extract',
                    'education': 'Could not extract',
                    'skills': 'Could not extract'
                }
            return {
                'raw_text': raw_text,
                'contact_info': self.extract_contact_info(raw_text),
                'experience': self.extract_experience(raw_text),
                'education': self.extract_education(raw_text),
                'skills': self.extract_skills(raw_text)
            }
        except Exception as e:
            logger.error(f"Unexpected error parsing CV {file_path}: {e}")
            return {
                'raw_text': f'Unexpected error: {str(e)}',
                'contact_info': 'Error during parsing',
                'experience': 'Error during parsing',
                'education': 'Error during parsing',
                'skills': 'Error during parsing'
            }

    # ------------ MATCHING FUNCTION ------------ #

    def match_with_criteria(self, parsed_cv: Dict, job_name: str = "",
                        required_experience: Optional[int] = None,
                        required_education: str = "",
                        required_skills: Optional[List[str]] = None) -> Dict:
        """
        Matches a parsed CV against job criteria and returns a score and details.
        """
        score, details = 0, []

        raw_text = parsed_cv.get('raw_text', '').lower()
        exp_text = parsed_cv.get('experience', '').lower()
        edu_text = parsed_cv.get('education', '').lower()
        skills_text = parsed_cv.get('skills', '').lower()

    # --------- Job Name Matching ---------
        if job_name:
            job_words = [w.strip() for w in job_name.lower().split() if w.strip()]
            if all(word in raw_text for word in job_words):
                score += 20
                details.append("Job title matched")
            else:
                details.append("Job title not fully matched")

    # --------- Experience Matching ---------
        if required_experience:
            years = []

        # Match "X years", "X-Y yrs", "X+ yrs"
            duration_matches = re.findall(r'(\d+)\s*(?:\+)?(?:-|to)?\s*(\d+)?\s*(?:years|yrs|year)', exp_text)
            for y1, y2 in duration_matches:
                if y1 and y1.isdigit(): years.append(int(y1))
                if y2 and y2.isdigit(): years.append(int(y2))

            # Match year ranges like 2020-2023 or 2019 - 2021
            year_ranges = re.findall(r'\b(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}\b', exp_text)
            for start, end in year_ranges:
                start_year = int(start)
                end_year = int(end)
                if end_year >= start_year:
                    years.append(end_year - start_year)  # Difference is experience

            max_years = max(years) if years else 0

            if max_years >= required_experience:
                score += 20
                details.append(f"Experience OK ({max_years} yrs found)")
            else:
                details.append(f"Experience insufficient ({max_years} yrs found)")

    # --------- Education Matching ---------
        if required_education:
            education_map = {
                "bachelor": ["bachelor", "b.sc", "bsc", "undergraduate"],
                "master": ["master", "m.sc", "msc", "graduate"],
                "phd": ["phd", "doctorate", "doctoral"]
            }
            req_lower = required_education.lower()
            matched = False
            for key, synonyms in education_map.items():
                if req_lower in synonyms:
                    if any(s in edu_text for s in synonyms):
                        matched = True
                        break
            if matched:
                score += 20
                details.append("Education matched")
            else:
                details.append("Education not matched")

    # --------- Skills Matching ---------
        if required_skills:
            # Normalize skills: split by comma, semicolon, or new line
            cv_skills = re.split(r',|;|\n', skills_text)
            cv_skills = [s.strip() for s in cv_skills if s.strip()]

            matched_skills = [s for s in required_skills if s.lower() in cv_skills]
            score += len(matched_skills) * 10
            if matched_skills:
                details.append(f"Skills matched: {', '.join(matched_skills)}")
            else:
                details.append("No skills matched")

        return {"score": score, "details": details}

