# from rest_framework import serializers
# from .models import User, Hospital, Patient, Report, Appointment, Modality, ReportMessage, PACS, EHR, FieldMapping, ReportTemplate, UserActivity, Image, Permission, HospitalHeader, DemoRequest
# from django.utils import timezone
# from datetime import date, datetime
# import json
# import re

# class UserSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, required=False, allow_blank=True)
#     hospital = serializers.PrimaryKeyRelatedField(queryset=Hospital.objects.all(), required=False, allow_null=True)

#     class Meta:
#         model = User
#         fields = [
#             'id', 'username', 'preferred_name', 'email', 'phone', 'role', 'hospital',
#             'department', 'is_active', 'is_staff', 'is_admin', 'is_superuser', 'password'
#         ]

#     def validate_username(self, value):
#         if User.objects.filter(username=value).exclude(id=self.instance.id if self.instance else None).exists():
#             raise serializers.ValidationError("نام کاربری قبلاً استفاده شده است.")
#         return value

#     def validate_email(self, value):
#         if User.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
#             raise serializers.ValidationError("ایمیل قبلاً استفاده شده است.")
#         return value

#     def validate_phone(self, value):
#         if User.objects.filter(phone=value).exclude(id=self.instance.id if self.instance else None).exists():
#             raise serializers.ValidationError("شماره تلفن قبلاً استفاده شده است.")
#         return value

#     def validate_role(self, value):
#         valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
#         if value not in valid_roles:
#             raise serializers.ValidationError(f"نقش باید یکی از این مقادیر باشد: {valid_roles}")
#         return value

#     def create(self, validated_data):
#         password = validated_data.pop('password', None)
#         user = User(**validated_data)
#         if password:
#             user.set_password(password)
#         user.save()
#         return user

#     def update(self, instance, validated_data):
#         password = validated_data.pop('password', None)
#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
#         if password:
#             instance.set_password(password)
#         instance.save()
#         return instance

# class DoctorListSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ['id', 'preferred_name']

# class SimplePatientSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Patient
#         fields = ['id', 'first_name', 'last_name', 'national_id']

# class PermissionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Permission
#         fields = ['id', 'user', 'permission', 'hospital']

# class HospitalSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Hospital
#         fields = ['id', 'name', 'address', 'phone', 'fax', 'header_color', 'header_font', 'logo_position', 'qr_code_position']

# class HospitalHeaderSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = HospitalHeader
#         fields = [
#             'id', 'hospital', 'department', 'address', 'phone', 'fax_number', 'email_address',
#             'website_url', 'department_name', 'emergency_contact', 'accreditation', 'paper_size',
#             'font_family', 'heading_color', 'text_color', 'logo_position', 'name_position',
#             'department_position', 'address_position', 'phone_position', 'email_position',
#             'fax_position', 'website_position', 'emergency_contact_position',
#             'accreditations_position', 'qr_code_position', 'qr_code_link', 'image', 'header'
#         ]

#     def validate_paper_size(self, value):
#         valid_sizes = ['A4', 'Letter', 'Legal']
#         if value and value not in valid_sizes:
#             raise serializers.ValidationError(f"سایز کاغذ باید یکی از این مقادیر باشد: {valid_sizes}")
#         return value

#     def validate_heading_color(self, value):
#         if value and not re.match(r'^#[0-9A-Fa-f]{6}$', value):
#             raise serializers.ValidationError("رنگ هدر باید در فرمت HEX باشد (مثل #FFFFFF).")
#         return value

#     def validate_text_color(self, value):
#         if value and not re.match(r'^#[0-9A-Fa-f]{6}$', value):
#             raise serializers.ValidationError("رنگ متن باید در فرمت HEX باشد (مثل #000000).")
#         return value

#     def validate_phone(self, value):
#         if value and not re.match(r'^\+?\d{10,15}$', value):
#             raise serializers.ValidationError("شماره تلفن باید معتبر باشد (10 تا 15 رقم).")
#         return value

#     def validate_fax_number(self, value):
#         if value and not re.match(r'^\+?\d{10,15}$', value):
#             raise serializers.ValidationError("شماره فکس باید معتبر باشد (10 تا 15 رقم).")
#         return value

#     def validate_email_address(self, value):
#         if value and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
#             raise serializers.ValidationError("ایمیل باید معتبر باشد.")
#         return value

#     def validate_website_url(self, value):
#         if value and not re.match(r'^(https?://)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$', value):
#             raise serializers.ValidationError("آدرس وب‌سایت باید معتبر باشد.")
#         return value

#     def validate_emergency_contact(self, value):
#         if value and not re.match(r'^\+?\d{10,15}$', value):
#             raise serializers.ValidationError("شماره تماس اضطراری باید معتبر باشد (10 تا 15 رقم).")
#         return value

#     def validate(self, data):
#         hospital = data.get('hospital')
#         department = data.get('department', '')
#         if self.instance is None:
#             if HospitalHeader.objects.filter(hospital=hospital, department=department).exists():
#                 raise serializers.ValidationError("سربرگ برای این بیمارستان و دپارتمان قبلاً وجود دارد.")
#         else:
#             if HospitalHeader.objects.filter(hospital=hospital, department=department).exclude(id=self.instance.id).exists():
#                 raise serializers.ValidationError("سربرگ برای این بیمارستان و دپارتمان قبلاً وجود دارد.")
#         return data

# class AppointmentSerializer(serializers.ModelSerializer):
#     doctor = DoctorListSerializer(read_only=True)
#     patient_id = serializers.PrimaryKeyRelatedField(
#         queryset=Patient.objects.all(), write_only=True
#     )
#     doctor_id = serializers.PrimaryKeyRelatedField(
#         queryset=User.objects.filter(role='doctor'), source='doctor', write_only=True
#     )
#     first_name = serializers.SerializerMethodField()
#     last_name = serializers.SerializerMethodField()
#     national_id = serializers.SerializerMethodField()
#     doctor_name = serializers.SerializerMethodField()
#     time = serializers.SerializerMethodField()

#     class Meta:
#         model = Appointment
#         fields = [
#             'id', 'patient_id', 'doctor', 'doctor_id',
#             'date', 'time', 'status',
#             'first_name', 'last_name', 'national_id', 'doctor_name'
#         ]

#     def get_first_name(self, obj):
#         return obj.patient.first_name

#     def get_last_name(self, obj):
#         return obj.patient.last_name

#     def get_national_id(self, obj):
#         return obj.patient.national_id

#     def get_doctor_name(self, obj):
#         return obj.doctor.preferred_name if obj.doctor else None

#     def get_time(self, obj):
#         return obj.time.strftime('%I:%M %p')

#     def validate_time(self, value):
#         if value.minute % 5 != 0:
#             raise serializers.ValidationError("زمان باید مضرب ۵ دقیقه باشد.")
#         return value

#     def create(self, validated_data):
#         patient_id = validated_data.pop('patient_id')  # دریافت شیء Patient
#         doctor = validated_data.pop('doctor', None)    # دریافت شیء User (پزشک)
#         appointment = Appointment.objects.create(
#             patient=patient_id,  # نگاشت به فیلد patient
#             doctor=doctor,      # نگاشت به فیلد doctor
#             date=validated_data.get('date'),
#             time=validated_data.get('time'),
#             status=validated_data.get('status')
#         )
#         return appointment

# class PatientSerializer(serializers.ModelSerializer):
#     first_name = serializers.CharField(required=True)
#     last_name = serializers.CharField(required=True)
#     national_id = serializers.CharField(required=True)
#     age = serializers.IntegerField(required=True)
#     gender = serializers.ChoiceField(choices=[('male', 'مرد'), ('female', 'زن')], required=True)
#     phone = serializers.CharField(required=True)
#     modality = serializers.CharField(required=True)
#     registration_date = serializers.DateTimeField(source='created_at', read_only=True)
#     reference_doctor = serializers.SerializerMethodField()
#     related_doctor = serializers.SerializerMethodField()
#     doctor = serializers.JSONField(write_only=True, required=True)
#     reference_doctor_data = serializers.SerializerMethodField(read_only=True)
#     visit_date = serializers.DateField(required=False, allow_null=True)  # فیلد جدید از مدل

#     class Meta:
#         model = Patient
#         fields = ['id', 'first_name', 'last_name', 'national_id', 'birth_date', 'age', 'gender', 'phone', 'modality', 'status', 'hospital', 'doctor', 'reference_doctor', 'related_doctor', 'reference_doctor_data', 'registration_date', 'visit_date']
#         extra_kwargs = {
#             'birth_date': {'required': False},
#             'status': {'required': False},
#             'hospital': {'required': False},
#         }

#     def get_reference_doctor(self, obj):
#         report = obj.report_set.first()
#         if report and report.doctor:
#             return DoctorListSerializer(report.doctor).data
#         return None

#     def get_related_doctor(self, obj):
#         appointment = obj.appointment_set.filter(status='scheduled').first()
#         if appointment and appointment.doctor:
#             return DoctorListSerializer(appointment.doctor).data
#         return None

#     def get_reference_doctor_data(self, obj):
#         if obj.reference_doctor:
#             return DoctorListSerializer(obj.reference_doctor).data
#         return None

#     def validate_national_id(self, value):
#         existing_patient = Patient.objects.filter(national_id=value).exclude(id=self.instance.id if self.instance else None).first()
#         if existing_patient:
#             raise serializers.ValidationError("بیمار با این کد ملی قبلاً ثبت شده است.")
#         return value

#     def validate_modality(self, value):
#         valid_modalities = ['CT Scan', 'MRI', 'X-Ray', 'Sonography', 'PET Scan', 'Angiography', 'Echocardiography']
#         if value not in valid_modalities:
#             raise serializers.ValidationError(f"مدالیتی باید یکی از این مقادیر باشد: {valid_modalities}")
#         return value

#     def validate_phone(self, value):
#         if not re.match(r'^\+?\d{10,15}$', value):
#             raise serializers.ValidationError("شماره تلفن باید معتبر باشد (10 تا 15 رقم).")
#         return value

#     def validate_doctor(self, value):
#         try:
#             doctor_id = value.get('id')
#             doctor_name = value.get('name')
#             if not doctor_id:
#                 raise serializers.ValidationError("فیلد 'id' برای پزشک الزامی است.")
#             doctor = User.objects.get(id=doctor_id, role='doctor')
#             if doctor_name and doctor_name != doctor.preferred_name:
#                 raise serializers.ValidationError("نام پزشک با ID مطابقت ندارد.")
#             return doctor
#         except User.DoesNotExist:
#             raise serializers.ValidationError("پزشک با این ID وجود ندارد یا نقش پزشک ندارد.")
#         except KeyError:
#             raise serializers.ValidationError("فیلد 'id' در داده‌های پزشک الزامی است.")

#     def create(self, validated_data):
#         patient_id = validated_data.pop('patient_id')
#         doctor = validated_data.pop('doctor', None)
#         time = validated_data.get('time')
#         if not time:
#             raise serializers.ValidationError("فیلد time الزامی است و نمی‌تواند خالی باشد.")
#         appointment = Appointment.objects.create(
#             patient=patient_id,
#             doctor=doctor,
#             date=validated_data.get('date'),
#             time=time,
#             status=validated_data.get('status')
#         )
#         return appointment

#     def update(self, instance, validated_data):
#         doctor = validated_data.pop('doctor', None)
#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
#         if doctor:
#             instance.reference_doctor = doctor
#         instance.save()
#         return patient

# class ImageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Image
#         fields = ['id', 'file']

# class ReportSerializer(serializers.ModelSerializer):
#     doctor = DoctorListSerializer(read_only=True)
#     patient = SimplePatientSerializer(read_only=True)
#     patient_id = serializers.PrimaryKeyRelatedField(
#         queryset=Patient.objects.all(), source='patient', write_only=True
#     )
#     images = ImageSerializer(many=True, read_only=True)

#     class Meta:
#         model = Report
#         fields = ['id', 'patient', 'patient_id', 'doctor', 'content', 'audio_file', 'signature', 'token', 'created_at', 'is_deleted', 'images']

#     def to_internal_value(self, data):
#         data = data.copy()
#         print("Raw input data for ReportSerializer:", data)
#         return super().to_internal_value(data)

#     def validate(self, data):
#         print("Received data in ReportSerializer:", data)
#         return data

# class ModalitySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Modality
#         fields = ['id', 'name']

# class ReportMessageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ReportMessage
#         fields = ['id', 'report', 'sender', 'receiver', 'message', 'created_at']

# class PACSSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PACS
#         fields = ['id', 'name', 'ip_address', 'port', 'ae_title_in', 'ae_title_out', 'hospital', 'patient', 'image_url', 'created_at']

#     def validate_ip_address(self, value):
#         parts = value.split('.')
#         if len(parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
#             raise serializers.ValidationError("آدرس IP معتبر نیست.")
#         return value

#     def validate_port(self, value):
#         if not (0 <= value <= 65535):
#             raise serializers.ValidationError("پورت باید بین 0 و 65535 باشد.")
#         return value

#     def validate_ae_title_in(self, value):
#         if not re.match(r'^[A-Z0-9_]{1,16}$', value):
#             raise serializers.ValidationError("AE Title ورودی باید حداکثر 16 کاراکتر و شامل حروف بزرگ، اعداد یا زیرخط باشد.")
#         return value

#     def validate_ae_title_out(self, value):
#         if not re.match(r'^[A-Z0-9_]{1,16}$', value):
#             raise serializers.ValidationError("AE Title خروجی باید حداکثر 16 کاراکتر و شامل حروف بزرگ، اعداد یا زیرخط باشد.")
#         return value

# class EHRSerializer(serializers.ModelSerializer):
#     protocol = serializers.ChoiceField(choices=['FHIR', 'HL7'], required=True)

#     class Meta:
#         model = EHR
#         fields = ['id', 'name', 'protocol', 'endpoint', 'auth_token', 'hospital', 'patient', 'data', 'created_at']

#     def validate_endpoint(self, value):
#         if not value.startswith(('http://', 'https://')):
#             raise serializers.ValidationError("آدرس endpoint باید با http:// یا https:// شروع شود.")
#         return value

#     def validate_auth_token(self, value):
#         if value and len(value) < 8:
#             raise serializers.ValidationError("توکن احراز هویت باید حداقل 8 کاراکتر باشد.")
#         return value

# class FieldMappingSerializer(serializers.ModelSerializer):
#     type = serializers.ChoiceField(choices=['string', 'integer', 'date', 'boolean'], required=True)

#     class Meta:
#         model = FieldMapping
#         fields = ['id', 'system_field', 'external_field', 'type', 'description', 'hospital']

#     def validate_system_field(self, value):
#         if not re.match(r'^[a-zA-Z0-9_]+$', value):
#             raise serializers.ValidationError("فیلد سیستم باید فقط شامل حروف، اعداد یا زیرخط باشد.")
#         return value

#     def validate_external_field(self, value):
#         if not re.match(r'^[a-zA-Z0-9_]+$', value):
#             raise serializers.ValidationError("فیلد خارجی باید فقط شامل حروف، اعداد یا زیرخط باشد.")
#         return value

# class ReportTemplateSerializer(serializers.ModelSerializer):
#     structure = serializers.JSONField()

#     class Meta:
#         model = ReportTemplate
#         fields = ['id', 'modality', 'structure', 'hospital']

#     def validate_modality(self, value):
#         valid_modalities = ['CT Scan', 'MRI', 'X-Ray', 'Sonography', 'PET Scan', 'Angiography', 'Echocardiography']
#         if value not in valid_modalities:
#             raise serializers.ValidationError(f"مدالیتی باید یکی از این مقادیر باشد: {valid_modalities}")
#         return value

#     def validate_structure(self, value):
#         try:
#             json.dumps(value)
#             if not isinstance(value, dict) or 'sections' not in value:
#                 raise serializers.ValidationError("ساختار باید یک JSON معتبر با کلید 'sections' باشد.")
#             for section in value.get('sections', []):
#                 if not all(key in section for key in ['key', 'title']):
#                     raise serializers.ValidationError("هر بخش باید دارای کلیدهای 'key' و 'title' باشد.")
#         except (TypeError, ValueError):
#             raise serializers.ValidationError("ساختار باید یک JSON معتبر باشد.")
#         return value

# class UserActivitySerializer(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True)

#     class Meta:
#         model = UserActivity
#         fields = ['id', 'user', 'action', 'details', 'timestamp']

# class DemoRequestSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DemoRequest
#         fields = ['id', 'name', 'email', 'phone', 'company', 'message', 'created_at']

#     def validate_email(self, value):
#         if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
#             raise serializers.ValidationError("ایمیل باید معتبر باشد.")
#         return value

#     def validate_phone(self, value):
#         if not re.match(r'^\+?\d{10,15}$', value):
#             raise serializers.ValidationError("شماره تلفن باید معتبر باشد (10 تا 15 رقم).")
#         return value



from rest_framework import serializers
from medical_reports.models import (
    User, Hospital, Patient, Report, Appointment, Modality, ReportMessage,
    PACS, EHR, FieldMapping, ReportTemplate, UserActivity, Image, Permission,
    HospitalHeader, DemoRequest
)
import re
from datetime import datetime, date
from django.utils import timezone

class DoctorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'preferred_name']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'role', 'hospital',
            'department', 'preferred_name', 'is_active'
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return value

    def validate_phone(self, value):
        if not re.match(r'^\+?\d{10,15}$', value):
            raise serializers.ValidationError("شماره تلفن باید معتبر باشد (10 تا 15 رقم).")
        return value

    def validate_role(self, value):
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if value not in valid_roles:
            raise serializers.ValidationError(f"نقش باید یکی از این‌ها باشد: {valid_roles}")
        return value

class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = ['id', 'name', 'address', 'phone']

    def validate_phone(self, value):
        if not re.match(r'^\+?\d{10,15}$', value):
            raise serializers.ValidationError("شماره تلفن بیمارستان باید معتبر باشد (10 تا 15 رقم).")
        return value

class PatientSerializer(serializers.ModelSerializer):
    doctor = DoctorListSerializer(read_only=True, source='reference_doctor')  # اصلاح: اشاره به reference_doctor
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
            'related_doctor', 'reference_doctor_data', 'registration_date', 'visit_date',
            'doctor'  # اضافه کردن فیلد doctor به fields
        ]

    def validate_national_id(self, value):
        if not re.match(r'^[0-9]+(_[0-9]+)?$', value):
            raise serializers.ValidationError("کد ملی باید فقط شامل اعداد و یا یک زیرخط باشد.")
        existing_patient = Patient.objects.filter(national_id=value).exclude(id=self.instance.id if self.instance else None).first()
        if existing_patient:
            raise serializers.ValidationError("این کد ملی قبلاً ثبت شده است.")
        return value

    def validate_phone(self, value):
        if not re.match(r'^\+?\d{10,15}$', value):
            raise serializers.ValidationError("شماره تلفن باید معتبر باشد (10 تا 15 رقم).")
        return value

    def validate_birth_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("تاریخ تولد نمی‌تواند در آینده باشد.")
        return value

    def validate_age(self, value):
        if value < 0 or value > 150:
            raise serializers.ValidationError("سن باید بین 0 تا 150 باشد.")
        return value

    def validate_modality(self, value):
        valid_modalities = ['CT Scan', 'MRI', 'X-Ray', 'Sonography', 'PET Scan', 'Angiography', 'Echocardiography']
        if value not in valid_modalities:
            raise serializers.ValidationError(f"مدالیتی باید یکی از این‌ها باشد: {valid_modalities}")
        return value

    def validate_status(self, value):
        valid_statuses = ['waiting', 'pending', 'completed']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"وضعیت باید یکی از این‌ها باشد: {valid_statuses}")
        return value

    def validate(self, data):
        birth_date = data.get('birth_date')
        age = data.get('age')
        if birth_date and age:
            calculated_age = (date.today() - birth_date).days // 365
            if abs(calculated_age - age) > 1:
                raise serializers.ValidationError("سن با تاریخ تولد همخوانی ندارد.")
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
            'id', 'patient_id', 'doctor', 'doctor_id',
            'date', 'time', 'status',
            'first_name', 'last_name', 'national_id', 'doctor_name'
        ]

    def get_first_name(self, obj):
        return obj.patient.first_name

    def get_last_name(self, obj):
        return obj.patient.last_name

    def get_national_id(self, obj):
        return obj.patient.national_id

    def get_doctor_name(self, obj):
        return obj.doctor.preferred_name if obj.doctor else None

    def validate_time(self, value):
        if not value:
            raise serializers.ValidationError("فیلد time الزامی است و نمی‌تواند خالی باشد.")
        if value.minute % 5 != 0:
            raise serializers.ValidationError("زمان باید مضرب ۵ دقیقه باشد.")
        return value

    def validate_date(self, value):
        if not value:
            raise serializers.ValidationError("فیلد date الزامی است.")
        if value < date.today():
            raise serializers.ValidationError("تاریخ نوبت نمی‌تواند در گذشته باشد.")
        return value

    def validate_status(self, value):
        valid_statuses = ['scheduled', 'cancelled', 'completed', 'pending']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"وضعیت باید یکی از این‌ها باشد: {valid_statuses}")
        return value

    def validate(self, data):
        patient_id = data.get('patient_id')
        doctor = data.get('doctor')
        date = data.get('date')
        time = data.get('time')
        
        if not patient_id:
            raise serializers.ValidationError("شناسه بیمار الزامی است.")
        if not doctor:
            raise serializers.ValidationError("شناسه پزشک الزامی است.")
        if not date:
            raise serializers.ValidationError("تاریخ نوبت الزامی است.")
        if not time:
            raise serializers.ValidationError("زمان نوبت الزامی است.")
        
        # چک کردن تداخل نوبت
        existing_appointment = Appointment.objects.filter(
            doctor=doctor,
            date=date,
            time=time
        ).exclude(id=self.instance.id if self.instance else None).exists()
        if existing_appointment:
            raise serializers.ValidationError("پزشک در این زمان نوبت دیگری دارد.")
        
        return data

    def create(self, validated_data):
        patient_id = validated_data.pop('patient_id')
        doctor = validated_data.pop('doctor')
        time = validated_data.get('time')
        date = validated_data.get('date')
        status = validated_data.get('status')
        
        if not time:
            raise serializers.ValidationError("فیلد time الزامی است و نمی‌تواند خالی باشد.")
        if not date:
            raise serializers.ValidationError("فیلد date الزامی است.")
        if not status:
            raise serializers.ValidationError("فیلد status الزامی است.")
        
        appointment = Appointment.objects.create(
            patient=patient_id,
            doctor=doctor,
            date=date,
            time=time,
            status=status
        )
        return appointment

    def update(self, instance, validated_data):
        patient_id = validated_data.pop('patient_id', instance.patient)
        doctor = validated_data.pop('doctor', instance.doctor)
        instance.patient = patient_id
        instance.doctor = doctor
        instance.date = validated_data.get('date', instance.date)
        instance.time = validated_data.get('time', instance.time)
        instance.status = validated_data.get('status', instance.status)
        instance.save()
        return instance

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'patient', 'doctor', 'content', 'created_at', 'signature', 'token', 'status', 'audio_file', 'default_actions']

    def validate(self, data):
        if not data.get('patient'):
            raise serializers.ValidationError("شناسه بیمار الزامی است.")
        if not data.get('doctor'):
            raise serializers.ValidationError("شناسه پزشک الزامی است.")
        return data

class ModalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Modality
        fields = ['id', 'name']

class ReportMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportMessage
        fields = ['id', 'report', 'sender', 'receiver', 'message', 'created_at']

# class PACSSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PACS
#         fields = ['id', 'hospital', 'server_address', 'server_port', 'ae_title_local', 'ae_title_remote']

#     def validate_server_port(self, value):
#         if value < 1 or value > 65535:
#             raise serializers.ValidationError("پورت سرور باید بین 1 تا 65535 باشد.")
#         return value

# class EHRSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = EHR
#         fields = ['id', 'hospital', 'endpoint', 'auth_token']

#     def validate_endpoint(self, value):
#         if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', value):
#             raise serializers.ValidationError("آدرس endpoint باید یک URL معتبر باشد.")
#         return value


# ... سایر سریالایزرها بدون تغییر ...

class PACSSerializer(serializers.ModelSerializer):
    class Meta:
        model = PACS
        fields = ['id', 'name', 'server_address', 'port', 'ae_title_local', 'ae_title_remote', 'hospital', 'patient', 'image_url', 'created_at']

    def validate_server_address(self, value):
        if not re.match(r'^(?:\d{1,3}\.){3}\d{1,3}$', value):
            raise serializers.ValidationError("آدرس سرور باید یک آدرس IP معتبر باشد (مثل 192.168.1.1).")
        return value

    def validate_port(self, value):
        if not (1 <= value <= 65535):
            raise serializers.ValidationError("پورت سرور باید بین 1 تا 65535 باشد.")
        return value

    def validate_ae_title_local(self, value):
        if not re.match(r'^[A-Z0-9_]{1,16}$', value):
            raise serializers.ValidationError("AE Title محلی باید حداکثر 16 کاراکتر و شامل حروف بزرگ، اعداد یا زیرخط باشد.")
        return value

    def validate_ae_title_remote(self, value):
        if not re.match(r'^[A-Z0-9_]{1,16}$', value):
            raise serializers.ValidationError("AE Title راه دور باید حداکثر 16 کاراکتر و شامل حروف بزرگ، اعداد یا زیرخط باشد.")
        return value

class EHRSerializer(serializers.ModelSerializer):
    class Meta:
        model = EHR
        fields = ['id', 'hospital', 'endpoint', 'auth_token']

    def validate_endpoint(self, value):
        if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', value):
            raise serializers.ValidationError("آدرس endpoint باید یک URL معتبر باشد.")
        return value

class FieldMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldMapping
        fields = ['id', 'hospital', 'field_name', 'mapped_field']

class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = ['id', 'hospital', 'modality', 'structure']

    def validate_structure(self, value):
        try:
            import json
            json.loads(value)
        except ValueError:
            raise serializers.ValidationError("ساختار باید یک JSON معتبر باشد.")
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
            'view_all', 'edit_all', 'delete_all', 'view_hospital', 'edit_hospital',
            'manage_users', 'view_patients', 'create_reports', 'sign_reports',
            'create_patients', 'manage_appointments'
        ]
        if value not in valid_permissions:
            raise serializers.ValidationError(f"پرمیشن باید یکی از این‌ها باشد: {valid_permissions}")
        return value

# class HospitalHeaderSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = HospitalHeader
#         fields = [
#             'id', 'hospital', 'department', 'image', 'font_family', 'heading_color',
#             'text_color', 'paper_size', 'logo_position', 'name_position',
#             'department_position', 'address_position', 'phone_position',
#             'email_position', 'fax_position', 'qr_code_position', 'website_position',
#             'emergency_contact_position', 'accreditations_position', 'address',
#             'phone', 'email_address', 'fax_number', 'website_url', 'emergency_contact',
#             'accreditation', 'qr_code_link'
#         ]

#     def validate_phone(self, value):
#         if value and not re.match(r'^\+?\d{10,15}$', value):
#             raise serializers.ValidationError("شماره تلفن باید معتبر باشد (10 تا 15 رقم).")
#         return value

#     def validate_email_address(self, value):
#         if value and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
#             raise serializers.ValidationError("ایمیل نامعتبر است.")
#         return value

#     def validate_paper_size(self, value):
#         valid_sizes = ['A4', 'Letter', 'Legal']
#         if value and value not in valid_sizes:
#             raise serializers.ValidationError(f"اندازه کاغذ باید یکی از این‌ها باشد: {valid_sizes}")
#         return value

#     def validate(self, data):
#         positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right']
#         for field in ['logo_position', 'name_position', 'department_position', 'address_position',
#                       'phone_position', 'email_position', 'fax_position', 'qr_code_position',
#                       'website_position', 'emergency_contact_position', 'accreditations_position']:
#             value = data.get(field)
#             if value and value not in positions:
#                 raise serializers.ValidationError(f"{field} باید یکی از این‌ها باشد: {positions}")
#         return data

class HospitalHeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalHeader
        fields = [
            'id', 'hospital', 'department', 'image', 'font_family', 'heading_color',
            'text_color', 'paper_size', 'logo_position', 'name_position',
            'department_position', 'address_position', 'phone_position',
            'email_position', 'fax_position', 'qr_code_position', 'website_position',
            'emergency_contact_position', 'accreditations_position', 'address',
            'phone', 'email_address', 'fax_number', 'website_url', 'emergency_contact',
            'accreditation', 'qr_code_link'
        ]

    def validate_phone(self, value):
        if value and not re.match(r'^\+?\d{10,15}$', value):
            raise serializers.ValidationError("شماره تلفن باید معتبر باشد (10 تا 15 رقم).")
        return value

    def validate_email_address(self, value):
        if value and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise serializers.ValidationError("ایمیل نامعتبر است.")
        return value

    def validate_paper_size(self, value):
        valid_sizes = ['A4', 'Letter', 'Legal']
        if value and value not in valid_sizes:
            raise serializers.ValidationError(f"اندازه کاغذ باید یکی از این‌ها باشد: {valid_sizes}")
        return value

    def validate_font_family(self, value):
        valid_fonts = ['Helvetica', 'Times-Roman', 'Courier']
        if value and value not in valid_fonts:
            raise serializers.ValidationError(f"فونت باید یکی از این‌ها باشد: {valid_fonts}")
        return value

    def validate_logo_position(self, value):
        valid_positions = ['left', 'right', '']
        if value and value not in valid_positions:
            raise serializers.ValidationError(f"موقعیت لوگو باید یکی از این‌ها باشد: {valid_positions}")
        return value

    def validate(self, data):
        position_choices = ['top-left', 'top-right', 'bottom-left', 'bottom-right', '']
        for field in ['name_position', 'department_position', 'address_position',
                      'phone_position', 'email_position', 'fax_position',
                      'qr_code_position', 'website_position', 'emergency_contact_position',
                      'accreditations_position']:
            value = data.get(field)
            if value and value not in position_choices:
                raise serializers.ValidationError(f"{field} باید یکی از این‌ها باشد: {position_choices}")
        return data




class DemoRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemoRequest
        fields = ['id', 'name', 'email', 'phone', 'company', 'message', 'created_at']

    def validate_email(self, value):
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise serializers.ValidationError("ایمیل نامعتبر است.")
        return value

    def validate_phone(self, value):
        if not re.match(r'^\+?\d{10,15}$', value):
            raise serializers.ValidationError("شماره تلفن باید معتبر باشد (10 تا 15 رقم).")
        return value