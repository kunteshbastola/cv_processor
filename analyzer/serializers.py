from rest_framework import serializers
from .models import CVUpload

class CVUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CVUpload
        fields = [
            'id',
            'user',
            'file',
            'uploaded_at',
            'processed',
            'raw_text',
            'overall_score',
            'contact_score',
            'experience_score',
            'education_score',
            'skills_score',
            'format_score',
            'target_job_role',
            'contact_info',
            'experience',
            'education',
            'skills',
            'suggestions'
        ]
        read_only_fields = [
            'id',
            'user',  # Set in view, not from client
            'uploaded_at',
            'processed',
            'raw_text',
            'overall_score',
            'contact_score',
            'experience_score',
            'education_score',
            'skills_score',
            'format_score',
            'suggestions'
        ]

    def validate_file(self, value):
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']
        max_size = 5 * 1024 * 1024  # 5 MB

        ext = value.name.lower().rsplit('.', 1)[-1]
        ext = f'.{ext}'

        if ext not in allowed_extensions:
            raise serializers.ValidationError(f"Unsupported file type: {ext}")

        if value.size > max_size:
            raise serializers.ValidationError("File exceeds 5MB size limit")

        return value
