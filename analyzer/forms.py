from django import forms
import os

EDUCATION_CHOICES = [
    ('High School', 'High School'),
    ('Diploma', 'Diploma'),
    ('Bachelors', 'Bachelors'),
    ('Masters', 'Masters'),
    ('PhD', 'PhD'),
]

class CVUploadForm(forms.Form):
    job_name = forms.CharField(
        max_length=100,
        required=True,
        label="Job Role",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Data Analyst"
        })
    )

    required_experience = forms.IntegerField(
        required=False,
        min_value=0,
        label="Minimum Years of Experience",
        widget=forms.TextInput(attrs={
        "class": "form-control",
        "placeholder": "e.g., Bachelor's in Computer Science"
        })
    )

    required_education = forms.ChoiceField(
        required=False,
        label="Required Education Level",
        choices=EDUCATION_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"})
    )

    required_skills = forms.CharField(
        required=False,
        label="Required Skills (comma-separated)",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Python, Excel, SQL"
        })
    )

    # ---------------- CLEAN METHODS ----------------

    def clean_required_skills(self):
        skills = self.cleaned_data.get("required_skills", "")
        if not skills:
            return []

        return [
            s.strip().lower()
            for s in skills.split(",")
            if s.strip()
        ]

    # ---------------- FILE VALIDATION ----------------

    def validate_multiple_files(self, files):
        """
        Call in the view:
        form.validate_multiple_files(request.FILES.getlist("cv_files"))
        """
        if not files:
            raise forms.ValidationError("Please upload at least one CV.")

        allowed_extensions = {".pdf", ".doc", ".docx", ".txt"}
        max_size = 5 * 1024 * 1024  # 5MB

        errors = []

        for file in files:
            ext = os.path.splitext(file.name)[1].lower()

            if ext not in allowed_extensions:
                errors.append(f"{file.name}: unsupported file format.")

            if file.size <= 0:
                errors.append(f"{file.name}: file is empty.")

            if file.size > max_size:
                errors.append(f"{file.name}: exceeds 5MB limit.")

        if errors:
            raise forms.ValidationError(errors)

        return files
