from django_filters import rest_framework as filters
from .models import Patient

class PatientFilter(filters.FilterSet):
    min_age = filters.NumberFilter(field_name='age', lookup_expr='gte')
    max_age = filters.NumberFilter(field_name='age', lookup_expr='lte')
    start_date = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Patient
        fields = ['min_age', 'max_age', 'start_date', 'end_date']