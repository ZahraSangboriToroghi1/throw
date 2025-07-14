from django.contrib import admin
from .models import User, Hospital, Patient, Appointment, Report, Modality, ReportMessage, PACS, EHR, FieldMapping, ReportTemplate, UserActivity, Permission, HospitalHeader, Image

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'hospital', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email')

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone')
    search_fields = ('name',)

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'national_id', 'hospital')
    list_filter = ('hospital', 'status')
    search_fields = ('first_name', 'last_name', 'national_id')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date', 'status')
    list_filter = ('status',)
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__username')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('patient__first_name', 'patient__last_name')

@admin.register(Modality)
class ModalityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ReportMessage)
class ReportMessageAdmin(admin.ModelAdmin):
    list_display = ('report', 'sender', 'created_at')
    search_fields = ('message',)

@admin.register(PACS)
class PACSAdmin(admin.ModelAdmin):
    list_display = ('get_patient_name', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name')

    def get_patient_name(self, obj):
        return str(obj.patient) if obj.patient else 'No Patient'
    get_patient_name.short_description = 'Patient'

@admin.register(EHR)
class EHRAdmin(admin.ModelAdmin):
    list_display = ('patient', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name')

@admin.register(FieldMapping)
class FieldMappingAdmin(admin.ModelAdmin):
    list_display = ('system_field',)
    search_fields = ('system_field', 'external_field')

@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('modality', 'hospital')
    search_fields = ('modality',)
    list_filter = ('hospital',)

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'action')

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'permission')
    search_fields = ('user__username', 'permission')

@admin.register(HospitalHeader)
class HospitalHeaderAdmin(admin.ModelAdmin):
    list_display = ('hospital', 'department', 'paper_size')
    search_fields = ('hospital__name', 'department')
    list_filter = ('hospital', 'department')

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('patient', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name')