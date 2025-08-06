from django import forms
import os

class CVUploadForm(forms.Form):
    job_name = forms.CharField(
        max_length=100,
        required=True,
        label="Job Role",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Data Analyst'
        })
    )

    dummy = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    def validate_multiple_files(self, files):
        """
        Call this in your view using:
        form.validate_multiple_files(request.FILES.getlist('cv_files'))
        """
        if not files:
            raise forms.ValidationError('Please select at least one file.')

        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']
        max_size = 5 * 1024 * 1024  # 5MB
        errors = []

        for file in files:
            file_ext = os.path.splitext(file.name)[1].lower()
            if file_ext not in allowed_extensions:
                errors.append(f'File {file.name} has an unsupported format.')
            if file.size == 0:
                errors.append(f'File {file.name} is empty.')
            if file.size > max_size:
                errors.append(f'File {file.name} exceeds the 5MB limit.')

        if errors:
            raise forms.ValidationError(errors)

        return files
