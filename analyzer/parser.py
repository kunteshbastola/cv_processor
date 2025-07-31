import PyPDF2
import docx
import re
from typing import Dict, List, Optional
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Download required NLTK data (run once)
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
            r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # More flexible international
            r'\b\d{10,15}\b'  # Simple digit sequences (phone numbers)
        ]
        
        # Enhanced keywords for better section detection
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
        
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file with better error handling."""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                # Check if PDF is encrypted
                if reader.is_encrypted:
                    logger.warning("PDF is encrypted, attempting to decrypt")
                    try:
                        reader.decrypt("")  # Try empty password
                    except:
                        return "Error: PDF is password protected"
                
                for page_num, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():  # Only add non-empty pages
                            text += page_text + "\n"
                    except Exception as e:
                        logger.warning(f"Error reading page {page_num}: {e}")
                        continue
                
                return text.strip() if text.strip() else "No readable text found in PDF"
                
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {e}")
            return f"Error reading PDF: {str(e)}"
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file with better error handling."""
        try:
            doc = docx.Document(file_path)
            text = ""
            
            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
            
            # Extract text from tables
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
        """Extract text from TXT file with multiple encoding attempts."""
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
        """Extract text based on file extension."""
        file_extension = file_extension.lower()
        
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_extension in ['.doc', '.docx']:
            return self.extract_text_from_docx(file_path)
        elif file_extension == '.txt':
            return self.extract_text_from_txt(file_path)
        else:
            return f"Unsupported file format: {file_extension}"
    
    def extract_contact_info(self, text: str) -> str:
        """Extract contact information using regex patterns."""
        contacts = []
        
        for pattern in self.contact_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            contacts.extend(matches)
        
        # Remove duplicates and clean up
        unique_contacts = list(set(contacts))
        
        # Filter out obvious false positives
        filtered_contacts = []
        for contact in unique_contacts:
            # Skip very short or very long matches
            if 3 <= len(contact.strip()) <= 50:
                filtered_contacts.append(contact.strip())
        
        return "; ".join(filtered_contacts) if filtered_contacts else "No contact information found"
    
    def extract_section(self, text: str, keywords: List[str], section_name: str, max_lines: int = 10) -> str:
        """Generic method to extract sections based on keywords."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        section_lines = []
        capture = False
        keywords_found = False
        
        # Stop words that indicate end of section
        stop_keywords = {
            'experience': ['education', 'skills', 'awards', 'certifications', 'references'],
            'education': ['experience', 'skills', 'awards', 'work', 'employment'],
            'skills': ['experience', 'education', 'awards', 'work', 'employment']
        }
        
        current_stop_words = stop_keywords.get(section_name.lower(), [])
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check if this line contains section keywords
            if any(keyword in line_lower for keyword in keywords):
                capture = True
                keywords_found = True
                section_lines.append(line)
                continue
            
            # If we're capturing and find a stop word, break
            if capture and any(stop_word in line_lower for stop_word in current_stop_words):
                # Check if it's actually a header (short line, often capitalized)
                if len(line) < 50 and (line.isupper() or line.istitle()):
                    break
            
            # Continue capturing relevant content
            if capture and line:
                # Skip very short lines that might be formatting artifacts
                if len(line) > 2:
                    section_lines.append(line)
                    
                # Stop if we've captured enough lines
                if len(section_lines) >= max_lines:
                    break
        
        if not keywords_found:
            return f"No {section_name.lower()} section found"
        
        return '\n'.join(section_lines) if section_lines else f"No {section_name.lower()} content found"
    
    def extract_experience(self, text: str) -> str:
        """Extract work experience section."""
        return self.extract_section(text, self.experience_keywords, 'Experience', max_lines=15)
    
    def extract_education(self, text: str) -> str:
        """Extract education section."""
        return self.extract_section(text, self.education_keywords, 'Education', max_lines=10)
    
    def extract_skills(self, text: str) -> str:
        """Extract skills section."""
        return self.extract_section(text, self.skills_keywords, 'Skills', max_lines=8)
    
    def parse_cv(self, file_path: str, file_extension: str) -> Dict:
        """Parse CV and extract all sections."""
        try:
            raw_text = self.extract_text(file_path, file_extension)
            
            # If text extraction failed, return error information
            if raw_text.startswith("Error:") or "Error reading" in raw_text:
                return {
                    'raw_text': raw_text,
                    'contact_info': 'Could not extract due to file reading error',
                    'experience': 'Could not extract due to file reading error',
                    'education': 'Could not extract due to file reading error',
                    'skills': 'Could not extract due to file reading error'
                }
            
            # Extract all sections
            result = {
                'raw_text': raw_text,
                'contact_info': self.extract_contact_info(raw_text),
                'experience': self.extract_experience(raw_text),
                'education': self.extract_education(raw_text),
                'skills': self.extract_skills(raw_text)
            }
            
            logger.info(f"Successfully parsed CV from {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error parsing CV {file_path}: {e}")
            return {
                'raw_text': f'Unexpected error during parsing: {str(e)}',
                'contact_info': 'Error during parsing',
                'experience': 'Error during parsing',
                'education': 'Error during parsing',
                'skills': 'Error during parsing'
            }