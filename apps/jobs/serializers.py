from rest_framework import serializers
from .models import JobPosting, Department, Status

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'budget_code', 'head']


class JobPostingListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    applicant_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = JobPosting
        fields = ['id', 'title', 'department_name', 'status', 'deadline', 'applicant_count']


class JobPostingDetailSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True) 
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='department', write_only=True
    )

    class Meta:
        model = JobPosting
        fields = ['id', 'title', 'department', 'department_id', 'location', 'employment_type', 'description', 'requirements', 'salary_min', 'salary_max', 'status', 'created_by', 'deadline', 'created_at', 'updated_at']
        # read_only_fields = ['created_by', 'created_at', 'updated_at', 'status']


class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = ['id', 'title', 'department', 'department_id', 'location', 'employment_type', 'description', 'requirements', 'salary_min', 'salary_max', 'status', 'created_by', 'deadline', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class BulkJobStatusUpdateSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    status = serializers.ChoiceField(choices=Status.choices)

    def validate_ids(self, value):
        return list(dict.fromkeys(value))