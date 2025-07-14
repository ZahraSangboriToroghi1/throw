from rest_framework import serializers
from .models import User, Hospital, Patient, Report, Appointment, Modality, ReportMessage, PACS, EHR, FieldMapping, ReportTemplate, UserActivity, Image, Permission, HospitalHeader, DemoRequest
from django.utils import timezone
from datetime import date, datetime
import json
import re

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    hospital = serializers.PrimaryKeyRelatedField(queryset=Hospital.objects.all(), required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'preferred_name', 'email', 'phone', 'role', 'hospital',
            'department', 'is_active', 'is_staff', 'is_admin', 'is_superuser', 'password'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }

    def validate_username(self, value):
        if User.objects.filter(username=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("نام کاربری قبلاً استفاده شده است.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("ایمیل قبلاً استفاده شده است.")
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("شماره تلفن قبلاً استفاده شده است.")
        return value

    def validate_role(self, value):
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if value not in valid_roles:
            raise serializers.ValidationError(f"نقش باید یکی از این مقادیر باشد: {valid_roles}")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            # Ensure password is properly hashed
            user.set_password(password)
        else:
            # Generate a temporary password if none provided
            import secrets
            import string
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            user.set_password(temp_password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            # Ensure password is properly hashed when updating
            instance.set_password(password)
        instance.save()
        return instance

class DoctorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'preferred_name']

class SimplePatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'first_name', 'last_name', 'national_id']

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'user', 'permission', 'hospital']

class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = ['id', 'name', 'address', 'phone']

    def validate_phone(self, value):
        if value and not re.match(r'^\d{10,15}$', value):
            raise serializers.ValidationError("شماره تلفن باید بین ۱۰ تا ۱۵ رقم باشد.")
        return value

class HospitalHeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalHeader
        fields = [
            'id', 'hospital', 'department', 'address', 'phone', 'fax_number',
            'email_address', 'website_url', 'department_name', 'emergency_contact',
            'accreditation', 'paper_size', 'font_family', 'heading_color', 'text_color',
            'logo_position', 'name_position', 'department_position', 'address_position',
            'phone_position', 'email_position', 'fax_position', 'website_position',
            'emergency_contact_position', 'accreditations_position', 'qr_code_position',
            'qr_code_link', 'image', 'header'
        ]

    def validate_phone(self, value):
        if value and not re.match(r'^\d{10,15}$', value):
            raise serializers.ValidationError("شماره تلفن باید بین ۱۰ تا ۱۵ رقم باشد.")
        return value

    def validate_email_address(self, value):
        if value and not re.match(r'^[^@]+@[^@]+\.[^@]+$', value):
            raise serializers.ValidationError("فرمت ایمیل نامعتبر است.")
        return value

    def validate_paper_size(self, value):
        valid_sizes = ['A4', 'Letter', 'Legal']
        if value and value not in valid_sizes:
            raise serializers.ValidationError(f"اندازه کاغذ باید یکی از: {valid_sizes} باشد.")
        return value

    def validate_font_family(self, value):
        valid_fonts = ['Helvetica', 'Times-Roman', 'Courier']
        if value and value not in valid_fonts:
            raise serializers.ValidationError(f"فونت باید یکی از: {valid_fonts} باشد.")
        return value

    def validate_logo_position(self, value):
        valid_positions = ['left', 'right']
        if value and value not in valid_positions:
            raise serializers.ValidationError(f"موقعیت لوگو باید یکی از: {valid_positions} باشد.")
        return value

    def validate(self, data):
        if data.get('qr_code_link') and not data['qr_code_link'].startswith(('http://', 'https://')):
            raise serializers.ValidationError("لینک QR Code باید با http:// یا https:// شروع شود.")
        return data

class AppointmentSerializer(serializers.ModelSerializer):
    doctor = DoctorListSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(), write_only=True
    )
    doctor_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='doctor'), source='doctor', write_only=True
    )
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    national_id = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    time = serializers.TimeField(format='%H:%M:%S', input_formats=['%H:%M:%S'], required=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'doctor', 'date', 'time', 'status',
            'patient_id', 'doctor_id', 'first_name', 'last_name', 'national_id', 'doctor_name'
        ]

    def get_first_name(self, obj):
        return obj.patient.first_name if obj.patient else ''

    def get_last_name(self, obj):
        return obj.patient.last_name if obj.patient else ''

    def get_national_id(self, obj):
        return obj.patient.national_id if obj.patient else ''

    def get_doctor_name(self, obj):
        return obj.doctor.preferred_name or obj.doctor.username if obj.doctor else ''

    def validate_time(self, value):
        if value.hour < 8 or value.hour > 18:
            raise serializers.ValidationError("زمان قرار ملاقات باید بین ساعت ۸ تا ۱۸ باشد.")
        return value

    def validate_date(self, value):
        if value < date.today():
            raise serializers.ValidationError("تاریخ قرار ملاقات نمی‌تواند در گذشته باشد.")
        return value

    def validate_status(self, value):
        valid_statuses = ['scheduled', 'completed', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"وضعیت باید یکی از: {valid_statuses} باشد.")
        return value

    def validate(self, data):
        patient_id = data.get('patient_id')
        doctor = data.get('doctor')
        date_val = data.get('date')
        time_val = data.get('time')

        if patient_id and doctor and date_val and time_val:
            existing = Appointment.objects.filter(
                patient=patient_id,
                doctor=doctor,
                date=date_val,
                time=time_val
            ).exclude(id=self.instance.id if self.instance else None)
            
            if existing.exists():
                raise serializers.ValidationError("این قرار ملاقات قبلاً ثبت شده است.")
        
        return data

    def create(self, validated_data):
        patient_id = validated_data.pop('patient_id')
        validated_data['patient'] = patient_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        patient_id = validated_data.pop('patient_id', None)
        if patient_id:
            validated_data['patient'] = patient_id
        return super().update(instance, validated_data)

class PatientSerializer(serializers.ModelSerializer):
    doctor = DoctorListSerializer(read_only=True, source='reference_doctor')
    hospital = serializers.PrimaryKeyRelatedField(queryset=Hospital.objects.all())
    reference_doctor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='doctor'), allow_null=True, required=False
    )
    related_doctor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='doctor'), allow_null=True, required=False
    )
    reference_doctor_data = DoctorListSerializer(read_only=True, source='reference_doctor')

    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'national_id', 'birth_date', 'age',
            'gender', 'phone', 'modality', 'status', 'hospital', 'reference_doctor',
            'created_at', 'has_report', 'visit_date', 'doctor', 'related_doctor', 'reference_doctor_data'
        ]

    def validate_national_id(self, value):
        if not re.match(r'^\d{10}$', value):
            raise serializers.ValidationError("کد ملی باید ۱۰ رقم باشد.")
        if Patient.objects.filter(national_id=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("بیمار با این کد ملی قبلاً ثبت شده است.")
        return value

    def validate_phone(self, value):
        if not re.match(r'^\d{10,11}$', value):
            raise serializers.ValidationError("شماره تلفن باید ۱۰ یا ۱۱ رقم باشد.")
        return value

    def validate_birth_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("تاریخ تولد نمی‌تواند در آینده باشد.")
        return value

    def validate_age(self, value):
        if value is not None and (value < 0 or value > 150):
            raise serializers.ValidationError("سن باید بین ۰ تا ۱۵۰ سال باشد.")
        return value

    def validate_modality(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("نوع تصویربرداری الزامی است.")
        return value

    def validate_status(self, value):
        valid_statuses = ['pending', 'completed', 'cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"وضعیت باید یکی از: {valid_statuses} باشد.")
        return value

    def validate(self, data):
        if data.get('birth_date') and data.get('age'):
            calculated_age = timezone.now().year - data['birth_date'].year
            if abs(calculated_age - data['age']) > 1:
                raise serializers.ValidationError("سن و تاریخ تولد مطابقت ندارند.")
        return data

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'patient', 'doctor', 'content', 'created_at', 'signature', 'token', 'status', 'audio_file', 'default_actions']

    def validate(self, data):
        if not data.get('content', '').strip():
            raise serializers.ValidationError("محتوای گزارش نمی‌تواند خالی باشد.")
        return data

class ModalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Modality
        fields = ['id', 'name']

class ReportMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportMessage
        fields = ['id', 'report', 'sender', 'receiver', 'message', 'created_at']

class PACSSerializer(serializers.ModelSerializer):
    class Meta:
        model = PACS
        fields = ['id', 'name', 'server_address', 'port', 'ae_title_local', 'ae_title_remote', 'hospital', 'patient', 'image_url', 'created_at']

    def validate_server_address(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("آدرس سرور الزامی است.")
        return value

    def validate_port(self, value):
        if value < 1 or value > 65535:
            raise serializers.ValidationError("پورت باید بین ۱ تا ۶۵۵۳۵ باشد.")
        return value

    def validate_ae_title_local(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("عنوان AE محلی الزامی است.")
        return value

    def validate_ae_title_remote(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("عنوان AE راه دور الزامی است.")
        return value

class EHRSerializer(serializers.ModelSerializer):
    class Meta:
        model = EHR
        fields = ['id', 'name', 'protocol', 'endpoint', 'auth_token', 'hospital', 'patient', 'data', 'created_at']

    def validate_endpoint(self, value):
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("آدرس نقطه پایانی باید با http:// یا https:// شروع شود.")
        return value

class FieldMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldMapping
        fields = ['id', 'system_field', 'external_field', 'type', 'description', 'hospital']

class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = ['id', 'modality', 'structure', 'hospital']

    def validate_structure(self, value):
        try:
            json.loads(value)
        except json.JSONDecodeError:
            raise serializers.ValidationError("ساختار قالب باید یک JSON معتبر باشد.")
        return value

class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = ['id', 'user', 'action', 'details', 'timestamp']

class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['id', 'patient', 'report', 'file', 'created_at']

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'user', 'permission', 'hospital']

    def validate_permission(self, value):
        valid_permissions = [
            'view_all', 'edit_all', 'delete_all',
            'view_hospital', 'edit_hospital', 'manage_users',
            'view_patients', 'edit_patients', 'manage_patients',
            'view_reports', 'edit_reports', 'sign_reports'
        ]
        if value not in valid_permissions:
            raise serializers.ValidationError(f"مجوز باید یکی از: {valid_permissions} باشد.")
        return value

class DemoRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemoRequest
        fields = ['id', 'name', 'email', 'phone', 'company', 'message', 'created_at']

    def validate_email(self, value):
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', value):
            raise serializers.ValidationError("فرمت ایمیل نامعتبر است.")
        return value

    def validate_phone(self, value):
        if not re.match(r'^\d{10,15}$', value):
            raise serializers.ValidationError("شماره تلفن باید بین ۱۰ تا ۱۵ رقم باشد.")
        return value