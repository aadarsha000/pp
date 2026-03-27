from rest_framework import serializers


class FileValidator:
    def __init__(self, allowed_mime_types=None, max_size_mb=8):
        self.allowed_mime_types = allowed_mime_types or []
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def __call__(self, uploaded_file):
        content_type = getattr(uploaded_file, "content_type", None)
        if content_type not in self.allowed_mime_types:
            raise serializers.ValidationError(
                "Unsupported file type. Allowed: PDF, DOCX, PNG, JPG."
            )

        if uploaded_file.size > self.max_size_bytes:
            raise serializers.ValidationError("File too large. Max allowed size is 8 MB.")

