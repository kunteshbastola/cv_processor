from django.contrib import admin
from rest_framework.authtoken.models import Token
from .models import CVUpload
import os


@admin.register(CVUpload)
class CVUploadAdmin(admin.ModelAdmin):
    list_display = (
        "display_filename",
        "uploaded_at",
        "processed",
        "target_job_role",
        "overall_score",
    )

    search_fields = (
        "file",
        "target_job_role",
        "raw_text",
    )

    list_filter = (
        "processed",
        "target_job_role",
        "uploaded_at",
    )

    def display_filename(self, obj):
        return os.path.basename(obj.file.name)

    display_filename.short_description = "File Name"


# Register Token model to view tokens in admin
admin.site.register(Token)
