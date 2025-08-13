from django.contrib import admin
from rest_framework.authtoken.models import Token
# Register your models here.
from django.contrib import admin
from .models import CVUpload

@admin.register(CVUpload)
class CVUploadAdmin(admin.ModelAdmin):
    list_display = ('filename', 'uploaded_at', 'processed', 'job_name', 'overall_score')
    search_fields = ('filename', 'job_name')
    list_filter = ('processed', 'uploaded_at')

# Register Token model to view tokens in admin
admin.site.register(Token)