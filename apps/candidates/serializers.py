from rest_framework import serializers

from jobs.models import JobPosting
from .models import Application, Stage, ApplicationStageLog, Candidate, Document
from .validators import FileValidator


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['id', 'full_name', 'email', 'phone', 'linkedin_url', 'source']


class ApplicationSerializer(serializers.ModelSerializer):
    candidate = CandidateSerializer()
    # job = JobPostingSerializer()
    class Meta:
        model = Application
        fields = ['id', 'candidate', 'job', 'stage', 'rejection_reason']


class ApplicationCreateSerializer(serializers.ModelSerializer):
    candidate = serializers.PrimaryKeyRelatedField(queryset=Candidate.objects.all())
    job = serializers.PrimaryKeyRelatedField(queryset=JobPosting.objects.all())

    class Meta:
        model = Application
        fields = ['candidate', 'job']

    def validate_candidate(self, value):
        if Candidate.objects.filter(id=value.id).exists():
            return value
        raise serializers.ValidationError("Candidate not found.")

    def validate_job(self, value):
        if JobPosting.objects.filter(id=value.id).exists():
            return value
        raise serializers.ValidationError("Job not found.")



class ApplicationStageUpdateSerializer(serializers.ModelSerializer):
    note = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = Application
        fields = ['stage', 'rejection_reason', 'note']

    def validate_stage(self, value):
        current_stage = self.instance.stage
        allowed_order = [Stage.APPLIED, Stage.SCREENING, Stage.TECHNICAL, Stage.HR, Stage.OFFER, Stage.HIRED]
        
        if value == Stage.REJECTED:
            return value
            
        try:
            current_idx = allowed_order.index(current_stage)
            new_idx = allowed_order.index(value)
            # Cannot skip or go back
            if new_idx != current_idx + 1:
                raise serializers.ValidationError("Stages must advance sequentially (e.g. Applied -> Screening).")
        except ValueError:
             raise serializers.ValidationError("Invalid stage transition.")
        return value

    def update(self, instance, validated_data):
        from_stage = instance.stage
        note = validated_data.pop('note', '')
        instance = super().update(instance, validated_data)
        
        ApplicationStageLog.objects.create(
            application=instance,
            from_stage=from_stage,
            to_stage=instance.stage,
            changed_by=self.context['request'].user,
            note=note
        )
        return instance



class DocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(
        validators=[
            FileValidator(
                allowed_mime_types=[
                    "application/pdf",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "image/png",
                    "image/jpeg",
                ],
                max_size_mb=8,
            )
        ]
    )

    class Meta:
        model = Document
        fields = ['id', 'application', 'document_type', 'file', 'uploaded_by', 'uploaded_at']
        read_only_fields = ['id', 'application', 'uploaded_by', 'uploaded_at']

    def validate(self, attrs):
        application = self.context.get('application')
        if not application:
            raise serializers.ValidationError("Application context is required.")

        current_count = application.documents.count()
        if current_count >= 3:
            raise serializers.ValidationError(
                {"non_field_errors": ["Maximum 3 documents are allowed per application."]}
            )
        return attrs