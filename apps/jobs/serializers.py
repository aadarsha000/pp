from re import S
from rest_framework import serializers
from .models import JobPosting, Department

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
        fields = '__all__'


class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = '__all__'