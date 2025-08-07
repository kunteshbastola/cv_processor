from rest_framework import serializers
from .models import CVUpload

class CVUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CVUpload
        fields = [
            'id', 'user', 'file', 'filename', 'uploaded_at', 'processed',
            'raw_text', 'overall_score', 'contact_score', 'experience_score',
            'education_score', 'skills_score', 'format_score',
            'job_name', 'contact_info', 'experience', 'education', 'skills',
            'suggestions'
        ]
        read_only_fields = ['uploaded_at', 'processed', 'raw_text', 'overall_score',
                            'contact_score', 'experience_score', 'education_score',
                            'skills_score', 'format_score', 'suggestions']
