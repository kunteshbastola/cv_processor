from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User  # 👈 Add this
import os

def cv_upload_path(instance, filename):
    return f'cvs/{timezone.now().strftime("%Y/%m/%d")}/{filename}'

class CVUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True,blank=True)  # 👈 Add this line

    file = models.FileField(upload_to=cv_upload_path)
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    
    # Extracted content
    raw_text = models.TextField(blank=True)
    
    # Analysis results
    overall_score = models.FloatField(null=True, blank=True)
    contact_score = models.FloatField(null=True, blank=True)    
    experience_score = models.FloatField(null=True, blank=True)
    education_score = models.FloatField(null=True, blank=True)
    skills_score = models.FloatField(null=True, blank=True)
    matching_score = models.FloatField(null=True, blank=True)
    format_score = models.FloatField(null=True, blank=True)
    
    # Extracted sections
    job_name = models.CharField(max_length=255, blank=True)
    contact_info = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    education = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    
    # Suggestions
    suggestions = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.filename} - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"
    
    def get_file_extension(self):
        return os.path.splitext(self.filename)[1].lower()
