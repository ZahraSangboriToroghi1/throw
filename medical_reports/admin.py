from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Hospital, Patient, Appointment, Report, Modality, ReportMessage, PACS, EHR, FieldMapping, ReportTemplate, UserActivity, Permission, HospitalHeader, Image
from .admin_forms import CustomUserCreationForm, CustomUserChangeForm

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = ('username', 'email', 'role', 'hospital', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'hospital')
    search_fields = ('username', 'email', 'phone')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('preferred_name', 'email', 'phone')}),
        ('Permissions', {'fields': ('role', 'hospital', 'department', 'is_active', 'is_staff', 'is_admin', 'is_superuser')}),
        ('Important dates', {'fields': ('date_joined',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'role', 'hospital', 'password1', 'password2'),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Ensure password is properly hashed when saved through admin"""
        if not change:  # Creating new user
            # Password is already handled by CustomUserCreationForm
            pass
        else:  # Updating existing user
            # Only hash password if it was changed
            if form.cleaned_data.get('password'):
                obj.set_password(form.cleaned_data['password'])
        super().save_model(request, obj, form, change)

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