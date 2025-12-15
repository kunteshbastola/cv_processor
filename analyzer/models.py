from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import os

def cv_upload_path(instance, filename):
    return f"cvs/{timezone.now().strftime('%Y/%m/%d')}/{filename}"

class CVUpload(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cv_uploads"
    )

    file = models.FileField(upload_to=cv_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    # ---------------- RAW CONTENT ----------------
    raw_text = models.TextField(blank=True)

    # ---------------- CONTEXT ----------------
    target_job_role = models.CharField(
        max_length=255,
        blank=True,
        help_text="Job role this CV was evaluated against"
    )

    # ---------------- SECTION DATA ----------------
    contact_info = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    education = models.TextField(blank=True)
    skills = models.TextField(blank=True)

    # ---------------- SCORES ----------------
    overall_score = models.FloatField(null=True, blank=True)
    contact_score = models.FloatField(null=True, blank=True)
    experience_score = models.FloatField(null=True, blank=True)
    education_score = models.FloatField(null=True, blank=True)
    skills_score = models.FloatField(null=True, blank=True)
    format_score = models.FloatField(null=True, blank=True)
    job_match_score = models.FloatField(null=True, blank=True)

    # ---------------- FEEDBACK ----------------
    suggestions = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["uploaded_at"]),
            models.Index(fields=["processed"]),
            models.Index(fields=["target_job_role"]),
        ]

    def __str__(self):
        return f"{os.path.basename(self.file.name)} - {self.uploaded_at:%Y-%m-%d %H:%M}"

    @property
    def file_extension(self):
        return os.path.splitext(self.file.name)[1].lower()
