
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import os
from datetime import date
import uuid

def default_date():
    """Return today's date as default."""
    return date.today()

def patient_directory_path(instance, filename):
    """Generate upload path for patient-related files."""
    return f'patients/{instance.patient.national_id}/{filename}'

class Hospital(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    fax = models.CharField(max_length=20, blank=True)
    header_color = models.CharField(max_length=7, blank=True)
    header_font = models.CharField(max_length=100, blank=True)
    logo_position = models.CharField(max_length=20, blank=True)
    qr_code_position = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name

class UserManager(BaseUserManager):
    def create_user(self, username, email, phone, role, password=None, **extra_fields):
        if not username:
            raise ValueError('نام کاربری الزامی است')
        if not email:
            raise ValueError('ایمیل الزامی است')
        if not phone:
            raise ValueError('شماره تلفن الزامی است')
        if not role:
            raise ValueError('نقش الزامی است')

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, phone=phone, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, phone, role, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(username, email, phone, role, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('supervisor', 'سرپرست'),
        ('hospital_admin', 'مدیر بیمارستان'),
        ('doctor', 'پزشک'),
        ('secretary', 'منشی'),
    )

    username = models.CharField(max_length=150, unique=True)
    preferred_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    hospital = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'phone', 'role']

    def __str__(self):
        return self.username

class Patient(models.Model):
    GENDER_CHOICES = (
        ('male', 'مرد'),
        ('female', 'زن'),
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    national_id = models.CharField(max_length=20, unique=True)
    birth_date = models.DateField()
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=20)
    modality = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    registration_date = models.DateTimeField(default=timezone.now)
    reference_doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_patients')
    created_at = models.DateTimeField(default=timezone.now)
    has_report = models.BooleanField(default=False)
    visit_date = models.DateField(null=True, blank=True, verbose_name="تاریخ ویزیت")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Appointment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=default_date)
    time = models.TimeField()
    status = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.patient} with {self.doctor} on {self.date}"

class Report(models.Model):
    STATUS_CHOICES = (
        ('submitted', 'Submitted'),
        ('review', 'Review'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    audio_file = models.FileField(upload_to=patient_directory_path, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    signature = models.BooleanField(default=False)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_deleted = models.BooleanField(default=False)
    default_actions = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')

    def __str__(self):
        return f"Report for {self.patient}"

class Modality(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class ReportMessage(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    receiver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_messages')

    def __str__(self):
        return f"Message for {self.report}"

class PACS(models.Model):
    name = models.CharField(max_length=100)
    server_address = models.CharField(max_length=50)  # بدون رمزنگاری
    port = models.IntegerField()
    ae_title_local = models.CharField(max_length=50)  # بدون رمزنگاری
    ae_title_remote = models.CharField(max_length=50)  # بدون رمزنگاری
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True)
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=['hospital']),
            models.Index(fields=['patient']),
        ]

    def __str__(self):
        return f"PACS {self.name} for {self.hospital}"

class EHR(models.Model):
    PROTOCOL_CHOICES = (
        ('FHIR', 'FHIR'),
        ('HL7', 'HL7'),
    )

    name = models.CharField(max_length=100)
    protocol = models.CharField(max_length=50, choices=PROTOCOL_CHOICES)
    endpoint = models.URLField()
    auth_token = models.CharField(max_length=255, blank=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"EHR {self.name} for {self.hospital}"

class FieldMapping(models.Model):
    TYPE_CHOICES = (
        ('string', 'String'),
        ('integer', 'Integer'),
        ('date', 'Date'),
        ('boolean', 'Boolean'),
    )

    system_field = models.CharField(max_length=100)
    external_field = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.system_field} -> {self.external_field}"

class ReportTemplate(models.Model):
    modality = models.CharField(max_length=100)
    structure = models.TextField()
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)

    def __str__(self):
        return self.modality

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user} - {self.action}"

class Permission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.CharField(max_length=100)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.user} - {self.permission}"

class HospitalHeader(models.Model):
    POSITION_CHOICES = (
        ('top-left', 'Top Left'),
        ('top-right', 'Top Right'),
        ('bottom-left', 'Bottom Left'),
        ('bottom-right', 'Bottom Right'),
    )

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    department = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    fax_number = models.CharField(max_length=20, blank=True)
    email_address = models.EmailField(blank=True)
    website_url = models.URLField(blank=True)
    department_name = models.CharField(max_length=100, blank=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    accreditation = models.TextField(blank=True)
    paper_size = models.CharField(max_length=20, blank=True, choices=[('A4', 'A4'), ('Letter', 'Letter'), ('Legal', 'Legal')])
    font_family = models.CharField(max_length=100, blank=True, choices=[
        ('Helvetica', 'Helvetica'),
        ('Times-Roman', 'Times Roman'),
        ('Courier', 'Courier')
    ])
    heading_color = models.CharField(max_length=7, blank=True)
    text_color = models.CharField(max_length=7, blank=True)
    logo_position = models.CharField(max_length=20, blank=True, choices=[('left', 'Left'), ('right', 'Right')])
    name_position = models.CharField(max_length=20, blank=True, choices=POSITION_CHOICES)
    department_position = models.CharField(max_length=20, blank=True, choices=POSITION_CHOICES)
    address_position = models.CharField(max_length=20, blank=True, choices=POSITION_CHOICES)
    phone_position = models.CharField(max_length=20, blank=True, choices=POSITION_CHOICES)
    email_position = models.CharField(max_length=20, blank=True, choices=POSITION_CHOICES)
    fax_position = models.CharField(max_length=20, blank=True, choices=POSITION_CHOICES)
    website_position = models.CharField(max_length=20, blank=True, choices=POSITION_CHOICES)
    emergency_contact_position = models.CharField(max_length=20, blank=True, choices=POSITION_CHOICES)
    accreditations_position = models.CharField(max_length=20, blank=True, choices=POSITION_CHOICES)
    qr_code_position = models.CharField(max_length=20, blank=True, choices=POSITION_CHOICES)
    qr_code_link = models.URLField(blank=True)
    image = models.ImageField(upload_to='hospital_headers/', blank=True, null=True)
    header = models.TextField(blank=True)

    def __str__(self):
        return f"Header for {self.hospital} - {self.department if self.department else 'General'}"
    
class Image(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    file = models.ImageField(upload_to=patient_directory_path)
    created_at = models.DateTimeField(default=timezone.now)
    report = models.ForeignKey(Report, on_delete=models.SET_NULL, null=True, blank=True, related_name='images')

    def __str__(self):
        return f"Image for {self.patient}"

class DemoRequest(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    company = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Demo Request from {self.name}"