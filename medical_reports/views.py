from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from .models import User, Hospital, Patient, Report, Appointment, Modality, ReportMessage, PACS, EHR, FieldMapping, ReportTemplate, UserActivity, Image, Permission, HospitalHeader, DemoRequest
from .serializers import (
    UserSerializer, HospitalSerializer, PatientSerializer, ReportSerializer, AppointmentSerializer,
    ModalitySerializer, ReportMessageSerializer, PACSSerializer, EHRSerializer, FieldMappingSerializer,
    ReportTemplateSerializer, UserActivitySerializer, ImageSerializer, PermissionSerializer, 
    HospitalHeaderSerializer, DoctorListSerializer, DemoRequestSerializer
)
from rest_framework.decorators import action
from django.utils import timezone
from datetime import datetime, date, timedelta
from django.db.models import Count, Q
from .filters import PatientFilter
from rest_framework.permissions import BasePermission
from pynetdicom import AE, sop_class
from pynetdicom.sop_class import Verification, StudyRootQueryRetrieveInformationModelMove, PatientRootQueryRetrieveInformationModelFind
from pydicom.dataset import Dataset
from pydicom.uid import ExplicitVRLittleEndian
import logging
import requests
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
import uuid
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter, legal
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from io import BytesIO
from django.core.files.base import ContentFile
from django.views.decorators.cache import cache_page  # اضافه شده

logger = logging.getLogger('medical_reports')

class IsAdminOrSupervisor(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['supervisor', 'hospital_admin']

class IsDoctorOrSupervisor(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['doctor', 'supervisor']

class IsSecretaryForPatientActions(BasePermission):
    def has_permission(self, request, view):
        if request.method in ['POST', 'PUT', 'GET']:
            return request.user and request.user.is_authenticated and request.user.role == 'secretary'
        return False

class IsSecretaryForReportedPatients(BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated and request.user.role == 'secretary':
            if request.method == 'GET' or (request.method == 'POST' and view.action in ['export', 'change_status', 'list_reports', 'view_patient_reports', 'completed_patients_reports']):
                return True
        return False

class IsSecretaryForAppointmentCancel(BasePermission):
    def has_permission(self, request, view):
        if request.method == 'POST' and view.action == 'cancel':
            return request.user and request.user.is_authenticated and request.user.role == 'secretary'
        if request.method == 'GET':
            return request.user and request.user.is_authenticated and request.user.role in ['secretary', 'doctor']
        return False

class IsDoctorOrSecretary(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['doctor', 'secretary']

class IsAdminSupervisorOrDoctor(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['supervisor', 'hospital_admin', 'doctor']

class IsAuthenticatedOrSecretary(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['supervisor', 'hospital_admin', 'doctor', 'secretary']

class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class WelcomeCardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        hospital = user.hospital
        header = HospitalHeader.objects.filter(hospital=hospital, department=user.department).first() if hospital else None
        
        response_data = {
            'user': {
                'username': user.username,
                'preferred_name': user.preferred_name or None,
                'role': user.role,
                'department': user.department or ''
            },
            'hospital': HospitalSerializer(hospital).data if hospital else None,
            'header': HospitalHeaderSerializer(header).data if header else None,
        }

        if user.role != 'secretary':
            hospital_id = request.query_params.get('hospital_id')
            doctors = []
            if hospital_id:
                try:
                    hospital_id = int(hospital_id)
                    doctors = User.objects.filter(role='doctor', hospital_id=hospital_id)
                except ValueError:
                    return Response({'error': 'شناسه بیمارستان نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
            elif hospital:
                doctors = User.objects.filter(role='doctor', hospital=hospital)
            response_data['doctors'] = DoctorListSerializer(doctors, many=True).data
        
        return Response(response_data)

# logger = logging.getLogger('medical_reports')

# class DoctorViewSet(viewsets.ViewSet):
#     permission_classes = [IsAuthenticated, IsDoctorOrSupervisor]

#     @action(detail=False, methods=['get'])
#     def stats(self, request):
#         user = request.user
#         # گزارش‌های پزشک
#         reports = Report.objects.filter(doctor=user, is_deleted=False)
#         report_stats = reports.aggregate(
#             pending=Count('id', filter=Q(signature=False)),
#             submitted=Count('id', filter=Q(status='submitted')),
#             review=Count('id', filter=Q(status='review')),
#             completed=Count('id', filter=Q(signature=True))
#         )

#         # قرارهای پزشک
#         appointments = Appointment.objects.filter(doctor=user)
#         appointment_stats = appointments.aggregate(
#             total_appointments=Count('id'),
#             scheduled=Count('id', filter=Q(status='scheduled')),
#             cancelled=Count('id', filter=Q(status='cancelled')),
#             completed=Count('id', filter=Q(status='completed')),
#             pending=Count('id', filter=Q(status='pending'))
#         )

#         response_data = {
#             'report_stats': {
#                 'pending': report_stats['pending'] or 0,
#                 'submitted': report_stats['submitted'] or 0,
#                 'review': report_stats['review'] or 0,
#                 'completed': report_stats['completed'] or 0
#             },
#             'appointment_stats': {
#                 'total_appointments': appointment_stats['total_appointments'] or 0,
#                 'scheduled': appointment_stats['scheduled'] or 0,
#                 'cancelled': appointment_stats['cancelled'] or 0,
#                 'completed': appointment_stats['completed'] or 0,
#                 'pending': appointment_stats['pending'] or 0
#             }
#         }

#         UserActivity.objects.create(
#             user=user,
#             action='view_doctor_stats',
#             details=f'Doctor stats viewed by user {user.username}'
#         )
#         logger.info(f"Doctor stats viewed by user {user.username}")
#         return Response(response_data)

#     @action(detail=False, methods=['get'])
#     def advanced_search(self, request):
#         """
#         Advanced search for completed patients (has_report=True and status='completed') for the doctor.
#         """
#         user = request.user
#         queryset = Patient.objects.filter(
#             has_report=True, status='completed', reference_doctor=user
#         ).prefetch_related('appointment_set')

#         name = request.query_params.get('name', '')
#         if name:
#             queryset = queryset.filter(
#                 Q(first_name__icontains=name) | Q(last_name__icontains=name)
#             )

#         national_id = request.query_params.get('national_id', '')
#         if national_id:
#             queryset = queryset.filter(national_id__icontains=national_id)

#         gender = request.query_params.get('gender', '')
#         if gender in ['male', 'female']:
#             queryset = queryset.filter(gender=gender)
#         elif gender:
#             return Response({'error': "جنسیت باید 'male' یا 'female' باشد"}, status=status.HTTP_400_BAD_REQUEST)

#         min_age = request.query_params.get('min_age', '')
#         max_age = request.query_params.get('max_age', '')
#         if min_age:
#             try:
#                 min_age = int(min_age)
#                 queryset = queryset.filter(age__gte=min_age)
#             except ValueError:
#                 return Response({'error': 'پارامتر حداقل سن نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
#         if max_age:
#             try:
#                 max_age = int(max_age)
#                 queryset = queryset.filter(age__lte=max_age)
#             except ValueError:
#                 return Response({'error': 'پارامتر حداکثر سن نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

#         modality = request.query_params.get('modality', '')
#         if modality:
#             valid_modalities = ['CT Scan', 'MRI', 'X-Ray', 'Sonography', 'PET Scan', 'Angiography', 'Echocardiography']
#             if modality in valid_modalities:
#                 queryset = queryset.filter(modality=modality)
#             else:
#                 return Response({'error': f'مدالیتی نامعتبر است. باید یکی از این‌ها باشد: {valid_modalities}'}, status=status.HTTP_400_BAD_REQUEST)

#         start_date = request.query_params.get('start_date', '')
#         end_date = request.query_params.get('end_date', '')
#         if start_date and end_date:
#             try:
#                 start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
#                 end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
#                 queryset = queryset.filter(registration_date__date__range=[start_date, end_date])
#             except ValueError:
#                 return Response({'error': 'فرمت تاریخ نامعتبر است. از YYYY-MM-DD استفاده کنید'}, status=status.HTTP_400_BAD_REQUEST)

#         serializer = PatientSerializer(queryset, many=True)
#         UserActivity.objects.create(
#             user=user,
#             action='doctor_advanced_search_completed_patients',
#             details=f'Advanced search performed on completed patients by doctor {user.username} with params: {request.query_params}'
#         )
#         logger.info(f"Advanced search performed on completed patients by doctor {user.username}")
#         return Response(serializer.data)



logger = logging.getLogger('medical_reports')

class DoctorViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsDoctorOrSupervisor]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        user = request.user
        # گزارش‌های پزشک
        reports = Report.objects.filter(doctor=user, is_deleted=False)
        report_stats = reports.aggregate(
            pending=Count('id', filter=Q(signature=False)),
            completed=Count('id', filter=Q(signature=True))
        )

        # نوبت‌های امروز
        today = date.today()
        today_appointments = Appointment.objects.filter(doctor=user, date=today).count()

        # درصد تکمیل گزارش‌ها
        total_reports = (report_stats['pending'] or 0) + (report_stats['completed'] or 0)
        completion = (report_stats['completed'] / total_reports * 100) if total_reports > 0 else 0

        response_data = {
            'pending': report_stats['pending'] or 0,
            'completed': report_stats['completed'] or 0,
            'today': today_appointments,
            'completion': round(completion, 2)
        }

        UserActivity.objects.create(
            user=user,
            action='view_doctor_stats',
            details=f'Doctor stats viewed by user {user.username}'
        )
        logger.info(f"Doctor stats viewed by user {user.username}")
        return Response(response_data)

    @action(detail=False, methods=['get'])
    def advanced_search(self, request):
        user = request.user
        queryset = Patient.objects.filter(
            has_report=True, status='completed', reference_doctor=user
        ).prefetch_related('appointment_set')

        name = request.query_params.get('name', '')
        if name:
            queryset = queryset.filter(
                Q(first_name__icontains=name) | Q(last_name__icontains=name)
            )

        national_id = request.query_params.get('national_id', '')
        if national_id:
            queryset = queryset.filter(national_id__icontains=national_id)

        gender = request.query_params.get('gender', '')
        if gender in ['male', 'female']:
            queryset = queryset.filter(gender=gender)
        elif gender:
            return Response({'error': "جنسیت باید 'male' یا 'female' باشد"}, status=status.HTTP_400_BAD_REQUEST)

        min_age = request.query_params.get('min_age', '')
        max_age = request.query_params.get('max_age', '')
        if min_age:
            try:
                min_age = int(min_age)
                queryset = queryset.filter(age__gte=min_age)
            except ValueError:
                return Response({'error': 'پارامتر حداقل سن نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        if max_age:
            try:
                max_age = int(max_age)
                queryset = queryset.filter(age__lte=max_age)
            except ValueError:
                return Response({'error': 'پارامتر حداکثر سن نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

        modality = request.query_params.get('modality', '')
        if modality:
            valid_modalities = ['CT Scan', 'MRI', 'X-Ray', 'Sonography', 'PET Scan', 'Angiography', 'Echocardiography']
            if modality in valid_modalities:
                queryset = queryset.filter(modality=modality)
            else:
                return Response({'error': f'مدالیتی نامعتبر است. باید یکی از این‌ها باشد: {valid_modalities}'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = request.query_params.get('start_date', '')
        end_date = request.query_params.get('end_date', '')
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(registration_date__date__range=[start_date, end_date])
            except ValueError:
                return Response({'error': 'فرمت تاریخ نامعتبر است. از YYYY-MM-DD استفاده کنید'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PatientSerializer(queryset, many=True)
        UserActivity.objects.create(
            user=user,
            action='doctor_advanced_search_completed_patients',
            details=f'Advanced search performed on completed patients by doctor {user.username} with params: {request.query_params}'
        )
        logger.info(f"Advanced search performed on completed patients by doctor {user.username}")
        return Response(serializer.data)



class ModalityConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        modalities = ['CT Scan', 'MRI', 'X-Ray', 'Sonography', 'PET Scan', 'Angiography', 'Echocardiography']
        return Response({'modalities': modalities})

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            UserActivity.objects.create(
                user=request.user,
                action='logout',
                details=f'Logout at {timezone.now()}'
            )
            logger.info(f"User {request.user.username} logged out")
            return Response({"status": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Logout failed for user {request.user.username}: {str(e)}")
            return Response({"error": f"خطا در خروج: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class DemoRequestView(APIView):
    def post(self, request):
        serializer = DemoRequestSerializer(data=request.data)
        if serializer.is_valid():
            demo_request = serializer.save()
            
            content = f"""
Demo Request Details:
Name: {demo_request.name}
Email: {demo_request.email}
Phone: {demo_request.phone}
Company: {demo_request.company or 'N/A'}
Message: {demo_request.message or 'N/A'}
Created At: {demo_request.created_at}
"""
            file_content = ContentFile(content.encode('utf-8'))
            
            email = EmailMessage(
                subject='New Demo Request',
                body=f'A new demo request has been submitted by {demo_request.name}. See attached file for details.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.DEMO_REQUEST_EMAIL],
            )
            email.attach(f'demo_request_{demo_request.id}.txt', file_content.read(), 'text/plain')
            
            try:
                email.send()
                logger.info(f"Demo request email sent for {demo_request.name}")
                return Response({'status': 'Demo request submitted successfully'}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Failed to send demo request email: {str(e)}")
                return Response({'error': f'خطا در ارسال ایمیل: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminSupervisorOrDoctor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['username', 'role', 'hospital']

    def destroy(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            user_id = user.id
            username = user.username
            user.delete()
            UserActivity.objects.create(
                user=self.request.user,
                action='delete_user',
                details=f'User {user_id} ({username}) deleted by {request.user.username}'
            )
            logger.info(f"User {user_id} ({username}) deleted by {request.user.username}")
            return Response({'message': 'کاربر با موفقیت حذف شد'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            logger.error(f"User with id {kwargs.get('pk')} not found for deletion by {request.user.username}")
            return Response({'error': 'کاربر با این شناسه یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to delete user by {request.user.username}: {str(e)}")
            return Response({'error': f'خطا در حذف کاربر: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    # سایر action‌ها (doctors, set_permissions, profile) بدون تغییر
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedOrSecretary])
    def doctors(self, request):
        hospital_id = request.query_params.get('hospital_id')
        if hospital_id:
            try:
                hospital_id = int(hospital_id)
                doctors = User.objects.filter(role='doctor', hospital_id=hospital_id)
            except ValueError:
                return Response({'error': 'شناسه بیمارستان نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            doctors = User.objects.filter(role='doctor', hospital=request.user.hospital)
        serializer = DoctorListSerializer(doctors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def set_permissions(self, request, pk=None):
        try:
            user = self.get_object()
            permissions_data = request.data.get('permissions', {})

            role_permissions = {
                'supervisor': ['view_all', 'edit_all', 'delete_all'],
                'hospital_admin': ['view_hospital', 'edit_hospital', 'manage_users'],
                'doctor': ['view_patients', 'create_reports', 'sign_reports', 'create_patients', 'manage_appointments'],
                'secretary': ['view_patients', 'create_patients', 'manage_appointments']
            }

            valid_permissions = role_permissions.get(user.role, [])
            received_permissions = [perm for perm, value in permissions_data.items() if value is True]
            invalid_permissions = [perm for perm in received_permissions if perm not in valid_permissions]

            if invalid_permissions:
                return Response({
                    'error': f'پرمیشن‌های نامعتبر برای نقش {user.role}: {invalid_permissions}'
                }, status=status.HTTP_400_BAD_REQUEST)

            Permission.objects.filter(user=user, hospital=user.hospital).delete()

            for permission, enabled in permissions_data.items():
                if enabled and permission in valid_permissions:
                    Permission.objects.create(
                        user=user,
                        permission=permission,
                        hospital=user.hospital
                    )

            UserActivity.objects.create(
                user=user,
                action='set_permissions',
                details=f'Permissions updated: {received_permissions} by {request.user.username}'
            )
            logger.info(f"Permissions updated for user {user.username} by {request.user.username}")
            return Response({'message': 'پرمیشن‌ها با موفقیت به‌روزرسانی شدند'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            logger.error(f"User with id {pk} not found for setting permissions by {request.user.username}")
            return Response({'error': 'کاربر با این شناسه یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to set permissions for user {pk} by {request.user.username}: {str(e)}")
            return Response({'error': f'خطا در به‌روزرسانی پرمیشن‌ها: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        user = self.get_object()
        activities = UserActivity.objects.filter(user=user).order_by('-timestamp')
        login_count = activities.filter(action='login').count()
        report_count = activities.filter(action='create_report').count()
        last_login = activities.filter(action='login').first()

        serializer = UserSerializer(user)
        activity_serializer = UserActivitySerializer(activities, many=True)
        return Response({
            'profile': serializer.data,
            'activities': activity_serializer.data,
            'stats': {
                'login_count': login_count,
                'report_count': report_count,
                'last_login': last_login.timestamp if last_login else None
            }
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrSupervisor])
    def search(self, request):
        queryset = self.get_queryset()

        username = request.query_params.get('username', '')
        if username:
            queryset = queryset.filter(username__icontains=username)

        email = request.query_params.get('email', '')
        if email:
            queryset = queryset.filter(email__icontains=email)

        phone = request.query_params.get('phone', '')
        if phone:
            queryset = queryset.filter(phone__icontains=phone)

        role = request.query_params.get('role', '')
        if role:
            valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
            if role in valid_roles:
                queryset = queryset.filter(role=role)
            else:
                return Response({'error': f'نقش باید یکی از این‌ها باشد: {valid_roles}'}, status=status.HTTP_400_BAD_REQUEST)

        is_active = request.query_params.get('is_active', '')
        if is_active in ['true', 'false']:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        department = request.query_params.get('department', '')
        if department:
            queryset = queryset.filter(department__icontains=department)

        preferred_name = request.query_params.get('preferred_name', '')
        if preferred_name:
            queryset = queryset.filter(preferred_name__icontains=preferred_name)

        serializer = self.get_serializer(queryset, many=True)
        UserActivity.objects.create(
            user=request.user,
            action='search_users',
            details=f'User search performed by {request.user.username} with params: {request.query_params}'
        )
        logger.info(f"User search performed by {request.user.username}")
        return Response(serializer.data)

    
class HospitalViewSet(viewsets.ModelViewSet):
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    permission_classes = [IsAuthenticated]

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated, IsDoctorOrSecretary]
    filterset_class = PatientFilter
    filter_backends = [DjangoFilterBackend]

    def create(self, request, *args, **kwargs):
        logger.info(f"Received patient create request: {request.data}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        
        patient_phone = patient.phone
        hospital_name = patient.hospital.name
        message = f"بیمار گرامی {patient.first_name} {patient.last_name}، ثبت شما با کد ملی {patient.national_id} با موفقیت انجام شد. بیمارستان {hospital_name}"
        
        try:
            sms_response = requests.post(
                'https://api.sms-provider.com/send',
                json={'phone': patient_phone, 'message': message},
                headers={'Authorization': f'Bearer {settings.SMS_API_KEY}'},
                timeout=10
            )
            sms_response.raise_for_status()
            UserActivity.objects.create(
                user=self.request.user,
                action='send_sms_patient_registration',
                details=f'SMS sent for patient {patient.national_id} to {patient_phone}'
            )
            logger.info(f"SMS sent for patient {patient.national_id} to {patient_phone}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send SMS for patient {patient.national_id}: {str(e)}")
        
        UserActivity.objects.create(
            user=self.request.user,
            action='create_patient',
            details=f'Patient {patient.national_id} created with visit_date {patient.visit_date}'
        )
        return Response({"message": "بیمار ثبت شد"}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        try:
            logger.info(f"Received patient update request: {request.data}")
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            # ارسال پیامک اگر visit_date تغییر کرده
            if 'visit_date' in request.data:
                patient = instance  # تعریف patient به درستی
                message = f"بیمار گرامی {patient.first_name} {patient.last_name}، تاریخ ویزیت شما به {request.data['visit_date']} تغییر یافت. بیمارستان {patient.hospital.name}"
                try:
                    sms_response = requests.post(
                        'https://api.sms-provider.com/send',
                        json={'phone': patient.phone, 'message': message},
                        headers={'Authorization': f'Bearer {settings.SMS_API_KEY}'},
                        timeout=10
                    )
                    sms_response.raise_for_status()
                    logger.info(f"SMS sent for patient {patient.national_id} to {patient.phone}")
                except requests.exceptions.RequestException as e:
                    logger.error(f"Failed to send SMS for patient {patient.national_id}: {str(e)}")
            
            UserActivity.objects.create(
                user=self.request.user,
                action='update_patient',
                details=f'Patient {instance.national_id} updated by {request.user.username}'
            )
            logger.info(f"Patient {instance.national_id} updated by {request.user.username}")
            
            return Response({"message": "بیمار با موفقیت ویرایش شد"}, status=status.HTTP_200_OK)
        except ValidationError as e:
            logger.error(f"Validation error updating patient: {str(e)}")
            return Response({"statusCode": 400, "message": "خطای اعتبارسنجی", "errors": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Failed to update patient: {str(e)}")
            return Response({"statusCode": 500, "message": "خطای سرور", "errors": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def destroy(self, request, *args, **kwargs):
        try:
            patient = self.get_object()
            patient_id = patient.id
            national_id = patient.national_id
            patient.delete()
            logger.info(f"Patient {patient_id} (national_id: {national_id}) deleted by user {request.user.username}")
            UserActivity.objects.create(
                user=self.request.user,
                action='delete_patient',
                details=f'Patient {patient_id} (national_id: {national_id}) deleted'
            )
            return Response({'message': 'بیمار با موفقیت حذف شد'}, status=status.HTTP_200_OK)
        except Patient.DoesNotExist:
            return Response({'error': 'بیمار با این شناسه یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to delete patient: {str(e)}")
            return Response({'error': f'خطا در حذف بیمار: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        if self.action == 'stats':
            return [IsAuthenticated(), IsDoctorOrSecretary()]
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def stats(self, request):
        total_patients = Patient.objects.count()
        completed_patients = Patient.objects.filter(has_report=True).count()
        pending_patients = Patient.objects.filter(status='pending').count()
        active_doctors_patients = Appointment.objects.filter(
            status='scheduled',
            date=date.today()
        ).values('doctor').annotate(patient_count=Count('patient')).count()
        return Response({
            'total_patients': total_patients,
            'completed_patients': completed_patients,
            'pending_patients': pending_patients,
            'active_doctors_patients': active_doctors_patients
        })

    @action(detail=False, methods=['get'])
    def pending_patients(self, request):
        queryset = Patient.objects.filter(status='pending')
        
        name = request.query_params.get('name', '')
        if name:
            queryset = queryset.filter(
                Q(first_name__icontains=name) | Q(last_name__icontains=name)
            )

        modality = request.query_params.get('modality', '')
        if modality:
            queryset = queryset.filter(modality=modality)

        date_str = request.query_params.get('date', '')
        days_ahead = request.query_params.get('days_ahead', '')
        if date_str:
            try:
                filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(registration_date__date=filter_date)
            except ValueError:
                return Response({'error': 'فرمت تاریخ نامعتبر است. از YYYY-MM-DD استفاده کنید'}, status=status.HTTP_400_BAD_REQUEST)
        elif days_ahead:
            try:
                days = int(days_ahead)
                start_date = date.today() + timedelta(days=1)
                end_date = start_date + timedelta(days=days)
                queryset = queryset.filter(registration_date__date__range=[start_date, end_date])
            except ValueError:
                return Response({'error': 'پارامتر days_ahead نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def completed_patients(self, request):
        queryset = Patient.objects.filter(has_report=True).prefetch_related('appointment_set')
        if request.user.role == 'doctor':
            queryset = queryset.filter(reference_doctor=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def report_status(self, request, pk=None):
        patient = self.get_object()
        reports = Report.objects.filter(patient=patient)
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        patients = Patient.objects.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(national_id__icontains=query)
        )
        serializer = self.get_serializer(patients, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def reset_filters(self, request):
        patients = Patient.objects.all()
        serializer = self.get_serializer(patients, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def check_national_id(self, request):
        national_id = request.data.get('national_id')
        existing_patient = Patient.objects.filter(national_id=national_id).first()
        if existing_patient:
            return Response({
                'exists': True,
                'patient': PatientSerializer(existing_patient).data
            })
        return Response({'exists': False})

    @action(detail=False, methods=['get'])
    def advanced_search(self, request):
        queryset = Patient.objects.all()

        name = request.query_params.get('name', '')
        if name:
            queryset = queryset.filter(
                Q(first_name__icontains=name) | Q(last_name__icontains=name)
            )

        national_id = request.query_params.get('national_id', '')
        if national_id:
            queryset = queryset.filter(national_id__icontains=national_id)

        gender = request.query_params.get('gender', '')
        if gender in ['male', 'female']:
            queryset = queryset.filter(gender=gender)

        min_age = request.query_params.get('min_age', '')
        max_age = request.query_params.get('max_age', '')
        if min_age:
            try:
                min_age = int(min_age)
                queryset = queryset.filter(age__gte=min_age)
            except ValueError:
                return Response({'error': 'پارامتر حداقل سن نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        if max_age:
            try:
                max_age = int(max_age)
                queryset = queryset.filter(age__lte=max_age)
            except ValueError:
                return Response({'error': 'پارامتر حداکثر سن نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

        modality = request.query_params.get('modality', '')
        if modality:
            valid_modalities = ['CT Scan', 'MRI', 'X-Ray', 'Sonography', 'PET Scan', 'Angiography', 'Echocardiography']
            if modality in valid_modalities:
                queryset = queryset.filter(modality=modality)
            else:
                return Response({'error': f'مدالیتی نامعتبر است. باید یکی از این‌ها باشد: {valid_modalities}'}, status=status.HTTP_400_BAD_REQUEST)

        doctor_id = request.query_params.get('doctor_id', '')
        if doctor_id:
            try:
                doctor_id = int(doctor_id)
                queryset = queryset.filter(reference_doctor__id=doctor_id)
            except ValueError:
                return Response({'error': 'شناسه پزشک نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

        status = request.query_params.get('status', '')
        if status:
            valid_statuses = ['waiting', 'pending', 'completed']
            if status in valid_statuses:
                queryset = queryset.filter(status=status)
            else:
                return Response({'error': f'وضعیت نامعتبر است. باید یکی از این‌ها باشد: {valid_statuses}'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = request.query_params.get('start_date', '')
        end_date = request.query_params.get('end_date', '')
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(registration_date__date__range=[start_date, end_date])
            except ValueError:
                return Response({'error': 'فرمت تاریخ نامعتبر است. از YYYY-MM-DD استفاده کنید'}, status=status.HTTP_400_BAD_REQUEST)

        visit_date = request.query_params.get('visit_date', '')  # فیلتر جدید
        if visit_date:
            try:
                visit_date = datetime.strptime(visit_date, '%Y-%m-%d').date()
                queryset = queryset.filter(visit_date=visit_date)
            except ValueError:
                return Response({'error': 'فرمت تاریخ ویزیت نامعتبر است. از YYYY-MM-DD استفاده کنید'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(queryset, many=True)
        UserActivity.objects.create(
            user=request.user,
            action='advanced_search_patients',
            details=f'Advanced search performed with params: {request.query_params}'
        )
        logger.info(f"Advanced search performed by user {request.user.username}")
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='completed_patients/advanced_search')
    def completed_patients_advanced_search(self, request):
        """
        Advanced search for completed patients (has_report=True and status='completed').
        """
        queryset = Patient.objects.filter(has_report=True, status='completed').prefetch_related('appointment_set')

        # محدود کردن به بیمارستان کاربر برای منشی‌ها
        if request.user.role == 'secretary' and request.user.hospital:
            queryset = queryset.filter(hospital=request.user.hospital)

        name = request.query_params.get('name', '')
        if name:
            queryset = queryset.filter(
                Q(first_name__icontains=name) | Q(last_name__icontains=name)
            )

        national_id = request.query_params.get('national_id', '')
        if national_id:
            queryset = queryset.filter(national_id__icontains=national_id)

        gender = request.query_params.get('gender', '')
        if gender in ['male', 'female']:
            queryset = queryset.filter(gender=gender)
        elif gender:
            return Response({'error': "جنسیت باید 'male' یا 'female' باشد"}, status=status.HTTP_400_BAD_REQUEST)

        min_age = request.query_params.get('min_age', '')
        max_age = request.query_params.get('max_age', '')
        if min_age:
            try:
                min_age = int(min_age)
                queryset = queryset.filter(age__gte=min_age)
            except ValueError:
                return Response({'error': 'پارامتر حداقل سن نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        if max_age:
            try:
                max_age = int(max_age)
                queryset = queryset.filter(age__lte=max_age)
            except ValueError:
                return Response({'error': 'پارامتر حداکثر سن نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

        modality = request.query_params.get('modality', '')
        if modality:
            valid_modalities = ['CT Scan', 'MRI', 'X-Ray', 'Sonography', 'PET Scan', 'Angiography', 'Echocardiography']
            if modality in valid_modalities:
                queryset = queryset.filter(modality=modality)
            else:
                return Response({'error': f'مدالیتی نامعتبر است. باید یکی از این‌ها باشد: {valid_modalities}'}, status=status.HTTP_400_BAD_REQUEST)

        doctor_id = request.query_params.get('doctor_id', '')
        if doctor_id:
            try:
                doctor_id = int(doctor_id)
                queryset = queryset.filter(reference_doctor__id=doctor_id)
            except ValueError:
                return Response({'error': 'شناسه پزشک نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = request.query_params.get('start_date', '')
        end_date = request.query_params.get('end_date', '')
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(registration_date__date__range=[start_date, end_date])
            except ValueError:
                return Response({'error': 'فرمت تاریخ نامعتبر است. از YYYY-MM-DD استفاده کنید'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.role == 'doctor':
            queryset = queryset.filter(reference_doctor=request.user)

        serializer = self.get_serializer(queryset, many=True)
        UserActivity.objects.create(
            user=request.user,
            action='advanced_search_completed_patients',
            details=f'Advanced search performed on completed patients with params: {request.query_params}'
        )
        logger.info(f"Advanced search performed on completed patients by user {request.user.username}")
        return Response(serializer.data)

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        images = self.request.FILES.getlist('images', [])
        report = serializer.save(doctor=self.request.user)
        for image_file in images:
            Image.objects.create(
                patient=report.patient,
                report=report,
                file=image_file,
                created_at=timezone.now()
            )
        UserActivity.objects.create(
            user=self.request.user,
            action='create_report',
            details=f'Report {report.id} created for patient {report.patient.national_id}'
        )
        logger.info(f"Report {report.id} created with {len(images)} images by user {self.request.user.username}")

    def get_permissions(self):
        if self.action in ['retrieve', 'export', 'change_status', 'list_reports', 'view_patient_reports', 'completed_patients_reports']:
            return [IsAuthenticated(), IsSecretaryForReportedPatients()]
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def list_reports(self, request):
        queryset = Report.objects.filter(is_deleted=False)
        
        name = request.query_params.get('name', '')
        if name:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=name) | Q(patient__last_name__icontains=name)
            )

        national_id = request.query_params.get('national_id', '')
        if national_id:
            queryset = queryset.filter(patient__national_id__icontains=national_id)

        date_str = request.query_params.get('date', '')
        if date_str:
            try:
                filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date=filter_date)
            except ValueError:
                return Response({'error': 'فرمت تاریخ نامعتبر است. از YYYY-MM-DD استفاده کنید'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        report = self.get_object()
        report.signature = True
        report.save()
        UserActivity.objects.create(
            user=request.user,
            action='sign_report',
            details=f'Report {report.id} signed'
        )
        logger.info(f"Report {report.id} signed by user {self.request.user.username}")
        return Response({'status': 'گزارش امضا شد'})

    @action(detail=True, methods=['post'])
    def send_email(self, request, pk=None):
        report = self.get_object()
        email = request.data.get('email')
        try:
            send_mail(
                subject='Medical Report',
                message=f'Your report is available. Token: {report.token}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            UserActivity.objects.create(
                user=request.user,
                action='send_email',
                details=f'Email sent for report {report.id} to {email}'
            )
            logger.info(f"Email sent for report {report.id} to {email}")
            return Response({'status': f'ایمیل به {email} ارسال شد'})
        except Exception as e:
            logger.error(f"Failed to send email for report {report.id}: {str(e)}")
            return Response({'error': f'خطا در ارسال ایمیل: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def request_revision(self, request, pk=None):
        report = self.get_object()
        message = request.data.get('message')
        UserActivity.objects.create(
            user=request.user,
            action='request_revision',
            details=f'Revision requested for report {report.id}: {message}'
        )
        logger.info(f"Revision requested for report {report.id}: {message}")
        return Response({'status': 'درخواست بازبینی ثبت شد', 'message': message})

    @action(detail=True, methods=['post'])
    def process_audio(self, request, pk=None):
        report = self.get_object()
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({'error': 'فایل صوتی ارائه نشده است'}, status=status.HTTP_400_BAD_REQUEST)

        report.audio_file = audio_file
        report.save()
        UserActivity.objects.create(
            user=self.request.user,
            action='process_audio',
            details=f'Audio uploaded for report {report.id}'
        )
        logger.info(f"Audio file uploaded for report {report.id}")

        try:
            llm_response = requests.post(
                'https://api.x.ai/transcribe',
                files={'audio': audio_file},
                headers={'Authorization': f'Bearer {settings.AUTH_API_KEY}'}
            )
            llm_response.raise_for_status()
            transcription = llm_response.json().get('text', '')

            template = ReportTemplate.objects.filter(
                modality=report.patient.modality,
                hospital=report.patient.hospital
            ).first()
            if not template:
                return Response({'error': 'قالبی برای این مدالیتی یافت نشد'}, status=status.HTTP_400_BAD_REQUEST)

            structure = json.loads(template.structure)
            patient_info = {
                'name': f"{report.patient.first_name} {report.patient.last_name}",
                'national_id': report.patient.national_id,
                'birth_date': report.patient.birth_date.strftime('%Y-%m-%d'),
                'gender': report.patient.gender
            }

            llm_input = {
                'patient_info': patient_info,
                'test_type': report.patient.modality,
                'findings': transcription,
                'template': structure
            }

            llm_response = requests.post(
                'https://api.x.ai/generate-report',
                json=llm_input,
                headers={'Authorization': f'Bearer {settings.AUTH_API_KEY}'}
            )
            llm_response.raise_for_status()
            report_content = llm_response.json().get('report', '')

            formatted_content = ""
            for section in structure.get('sections', []):
                section_key = section.get('key')
                section_title = section.get('title', section_key.capitalize())
                section_content = report_content.get(section_key, '')
                formatted_content += f"{section_title}:\n{section_content}\n\n"

            report.content = formatted_content
            report.save()
            UserActivity.objects.create(
                user=self.request.user,
                action='update_report_content',
                details=f'Report {report.id} content updated from audio using template'
            )
            logger.info(f"Audio processed for report {report.id}, content updated with template")

            return Response({
                'status': 'فایل صوتی پردازش شد',
                'transcription': transcription,
                'report_content': formatted_content
            })
        except Exception as e:
            logger.error(f"Failed to process audio for report {report.id}: {str(e)}")
            return Response({'error': f'خطا در پردازش فایل صوتی: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        report = self.get_object()
        report.signature = True
        report.patient.has_report = True
        report.patient.status = 'completed'
        report.patient.save()
        report.save()

        default_actions = report.default_actions or {
            'send_to_pacs': True,
            'send_sms': True,
            'send_to_ehr': True
        }

        results = {}
        if default_actions.get('send_to_pacs', False):
            pacs = PACS.objects.filter(hospital=report.patient.hospital).first()
            if pacs:
                try:
                    ae = AE(ae_title=pacs.ae_title_local)
                    ae.add_requested_context(EncapsulatedPDFStorage, ExplicitVRLittleEndian)
                    assoc = ae.associate(
                        pacs.server_address,
                        pacs.port,
                        ae_title=pacs.ae_title_remote
                    )
                    if assoc.is_established:
                        ds = Dataset()
                        ds.PatientName = f"{report.patient.first_name}^{report.patient.last_name}"
                        ds.PatientID = report.patient.national_id
                        ds.StudyDate = datetime.now().strftime('%Y%m%d')
                        ds.StudyDescription = report.content[:100]
                        ds.StudyInstanceUID = str(report.token)
                        ds.SeriesInstanceUID = str(uuid.uuid4())
                        ds.SOPInstanceUID = str(uuid.uuid4())
                        ds.SOPClassUID = sop_class.EncapsulatedPDFStorage
                        ds.EncapsulatedDocument = report.content.encode('utf-8')

                        status = assoc.send_c_store(ds)
                        assoc.release()
                        if status.Status == 0:
                            results['pacs'] = 'با موفقیت به PACS ارسال شد'
                            UserActivity.objects.create(
                                user=request.user,
                                action='send_to_pacs',
                                details=f'Report {report.id} sent to PACS'
                            )
                            logger.info(f"Report {report.id} sent to PACS at {pacs.server_address}:{pacs.port}")
                        else:
                            results['pacs'] = f'خطا در ارسال به PACS: Status {status.Status}'
                            logger.error(f"Failed to send report {report.id} to PACS: Status {status.Status}")
                    else:
                        results['pacs'] = 'خطا در اتصال به PACS'
                        logger.error(f"Failed to connect to PACS {pacs.server_address}:{pacs.port}")
                except Exception as e:
                    results['pacs'] = f'خطا در ارسال به PACS: {str(e)}'
                    logger.error(f"Failed to send report {report.id} to PACS: {str(e)}")
            else:
                results['pacs'] = 'PACS پیکربندی نشده است'
                logger.warning(f"No PACS configured for hospital {report.patient.hospital.id}")

        if default_actions.get('send_sms', False):
            patient_phone = report.patient.phone
            try:
                response = requests.post(
                    'https://api.sms-provider.com/send',
                    json={
                        'phone': patient_phone,
                        'message': f'Your report is ready. Token: {report.token}'
                    },
                    headers={'Authorization': f'Bearer {settings.SMS_API_KEY}'},
                    timeout=10
                )
                response.raise_for_status()
                results['sms'] = 'پیامک با موفقیت ارسال شد'
                UserActivity.objects.create(
                    user=request.user,
                    action='send_sms',
                    details=f'SMS sent for report {report.id} to {patient_phone}'
                )
                logger.info(f"SMS sent for report {report.id} to {patient_phone}")
            except requests.exceptions.RequestException as e:
                results['sms'] = f'خطا در ارسال پیامک: {str(e)}'
                logger.error(f"Failed to send SMS for report {report.id}: {str(e)}")

        if default_actions.get('send_to_ehr', False):
            ehr = EHR.objects.filter(hospital=report.patient.hospital).first()
            if ehr:
                try:
                    headers = {'Authorization': f'Bearer {ehr.auth_token}'} if ehr.auth_token else {}
                    response = requests.post(
                        ehr.endpoint,
                        json={
                            'report_id': report.id,
                            'content': report.content,
                            'patient_id': report.patient.national_id
                        },
                        headers=headers,
                        timeout=10
                    )
                    response.raise_for_status()
                    results['ehr'] = 'با موفقیت به EHR ارسال شد'
                    UserActivity.objects.create(
                        user=request.user,
                        action='send_to_ehr',
                        details=f'Report {report.id} sent to EHR'
                    )
                    logger.info(f"Report {report.id} sent to EHR at {ehr.endpoint}")
                except requests.exceptions.RequestException as e:
                    results['ehr'] = f'خطا در ارسال به EHR: {str(e)}'
                    logger.error(f"Failed to send report {report.id} to EHR: {str(e)}")
            else:
                results['ehr'] = 'EHR پیکربندی نشده است'
                logger.warning(f"No EHR configured for hospital {report.patient.hospital.id}")

        UserActivity.objects.create(
            user=request.user,
            action='complete_report',
            details=f'Report {report.id} completed with results: {json.dumps(results)}'
        )
        logger.info(f"Report {report.id} completed with results: {results}")
        return Response({'status': 'گزارش تکمیل شد', 'results': results})

    # @action(detail=True, methods=['post'])
    # def export_pdf(self, request, pk=None):
    #     report = self.get_object()
    #     hospital_header = HospitalHeader.objects.filter(
    #         hospital=report.patient.hospital,
    #         department=report.doctor.department
    #     ).first()

    #     buffer = BytesIO()
    #     page_size = A4
    #     if hospital_header and hospital_header.paper_size:
    #         page_sizes = {'A4': A4, 'Letter': letter, 'Legal': legal}
    #         page_size = page_sizes.get(hospital_header.paper_size, A4)

    #     c = canvas.Canvas(buffer, pagesize=page_size)
        
    #     if hospital_header:
    #         c.setFont(hospital_header.font_family or 'Helvetica', 12)
    #         c.setFillColor(HexColor(hospital_header.heading_color or '#000000'))

    #         x_logo = 20*mm if hospital_header.logo_position == 'left' else 160*mm
    #         x_text = 20*mm if hospital_header.logo_position == 'right' else 50*mm
    #         if hospital_header.image and os.path.exists(os.path.join(settings.MEDIA_ROOT, hospital_header.image.name)):
    #             c.drawImage(
    #                 os.path.join(settings.MEDIA_ROOT, hospital_header.image.name),
    #                 x_logo, 260*mm, width=30*mm, height=15*mm
    #             )
    #         c.drawString(x_text, 280*mm, hospital_header.hospital.name)
    #         if hospital_header.department:
    #             c.drawString(x_text, 275*mm, hospital_header.department)
    #         if hospital_header.address:
    #             c.drawString(x_text, 270*mm, hospital_header.address)
    #         if hospital_header.phone:
    #             c.drawString(x_text, 265*mm, f"Phone: {hospital_header.phone}")
    #         if hospital_header.email_address:
    #             c.drawString(x_text, 260*mm, f"Email: {hospital_header.email_address}")
    #         if hospital_header.qr_code_link:
    #             qr_x = 160*mm if hospital_header.qr_code_position == 'right' else 20*mm
    #             qr_y = 280*mm if hospital_header.qr_code_position in ['top-right', 'top-left'] else 15*mm
    #             c.drawString(qr_x, qr_y, 'Scan QR Code for Report')

    #         c.setFont(hospital_header.font_family or 'Helvetica', 10)
    #         c.setFillColor(HexColor(hospital_header.text_color or '#000000'))
    #         footer_y = 15*mm
    #         if hospital_header.phone and hospital_header.phone_position == 'bottom-left':
    #             c.drawString(20*mm, footer_y, f"Phone: {hospital_header.phone}")
    #             footer_y -= 5*mm
    #         if hospital_header.fax_number and hospital_header.fax_position == 'bottom-left':
    #             c.drawString(20*mm, footer_y, f"Fax: {hospital_header.fax_number}")
    #             footer_y -= 5*mm
    #         if hospital_header.website_url:
    #             c.drawString(20*mm, footer_y, hospital_header.website_url)
    #             footer_y -= 5*mm
    #         if hospital_header.emergency_contact:
    #             c.drawString(20*mm, footer_y, f"Emergency: {hospital_header.emergency_contact}")
    #             footer_y -= 5*mm
    #         if hospital_header.accreditation:
    #             c.drawString(20*mm, footer_y, hospital_header.accreditation)

    #     c.setFont('Helvetica', 12)
    #     c.setFillColor('black')
    #     c.drawString(20*mm, 240*mm, f"Report for {report.patient.first_name} {report.patient.last_name}")
    #     text_object = c.beginText(20*mm, 230*mm)
    #     text_object.setFont('Helvetica', 10)
    #     for line in report.content.split('\n'):
    #         text_object.textLine(line)
    #     c.drawText(text_object)

    #     images = Image.objects.filter(report=report)
    #     y_position = 200*mm
    #     for image in images:
    #         if os.path.exists(os.path.join(settings.MEDIA_ROOT, image.file.name)):
    #             c.drawImage(
    #                 os.path.join(settings.MEDIA_ROOT, image.file.name),
    #                 20*mm, y_position, width=60*mm, height=30*mm
    #             )
    #             y_position -= 35*mm
    #         else:
    #             logger.warning(f"Image not found for report {report.id}: {image.file.name}")

    #     c.showPage()
    #     c.save()
    #     buffer.seek(0)

    #     response = Response(
    #         buffer.getvalue(),
    #         content_type='application/pdf',
    #         status=status.HTTP_200_OK
    #     )
    #     response['Content-Disposition'] = f'attachment; filename=report_{report.id}.pdf'
    #     UserActivity.objects.create(
    #         user=request.user,
    #         action='export_pdf',
    #         details=f'PDF exported for report {report.id}'
    #     )
    #     logger.info(f"PDF exported for report {report.id}")
    #     return response



    @action(detail=True, methods=['post'])
    def export_pdf(self, request, pk=None):
        report = self.get_object()
        # اولویت به هدر با department خاص، سپس هدر بدون department
        hospital_header = HospitalHeader.objects.filter(
            hospital=report.patient.hospital,
            department=report.doctor.department
        ).first() or HospitalHeader.objects.filter(
            hospital=report.patient.hospital,
            department=""
        ).first()

        buffer = BytesIO()
        page_size = A4
        default_font = 'Helvetica'
        default_heading_color = '#000000'
        default_text_color = '#000000'

        if hospital_header and hospital_header.paper_size:
            page_sizes = {'A4': A4, 'Letter': letter, 'Legal': legal}
            page_size = page_sizes.get(hospital_header.paper_size, A4)

        c = canvas.Canvas(buffer, pagesize=page_size)

        # تنظیم هدر و فوتر ثابت
        if hospital_header:
            c.setFont(hospital_header.font_family or default_font, 12)
            c.setFillColor(HexColor(hospital_header.heading_color or default_heading_color))
            x_logo = 20*mm if hospital_header.logo_position == 'left' else 160*mm
            x_text = 20*mm if hospital_header.logo_position == 'right' else 50*mm
            if hospital_header.image and os.path.exists(os.path.join(settings.MEDIA_ROOT, hospital_header.image.name)):
                c.drawImage(
                    os.path.join(settings.MEDIA_ROOT, hospital_header.image.name),
                    x_logo, 260*mm, width=30*mm, height=15*mm
                )
            c.drawString(x_text, 280*mm, hospital_header.hospital.name)
            if hospital_header.department:
                c.drawString(x_text, 275*mm, hospital_header.department)
            if hospital_header.address:
                c.drawString(x_text, 270*mm, hospital_header.address)
            if hospital_header.phone:
                c.drawString(x_text, 265*mm, f"Phone: {hospital_header.phone}")
            if hospital_header.email_address:
                c.drawString(x_text, 260*mm, f"Email: {hospital_header.email_address}")
            if hospital_header.qr_code_link:
                qr_x = 160*mm if hospital_header.qr_code_position == 'right' else 20*mm
                qr_y = 280*mm if hospital_header.qr_code_position in ['top-right', 'top-left'] else 15*mm
                c.drawString(qr_x, qr_y, 'Scan QR Code for Report')

            c.setFont(hospital_header.font_family or default_font, 10)
            c.setFillColor(HexColor(hospital_header.text_color or default_text_color))
            footer_y = 15*mm
            if hospital_header.phone and hospital_header.phone_position in ['bottom-left', 'bottom_center', 'bottom-right']:
                c.drawString(20*mm, footer_y, f"Phone: {hospital_header.phone}")
                footer_y -= 5*mm
            if hospital_header.fax_number and hospital_header.fax_position in ['bottom-left', 'bottom_center', 'bottom-right']:
                c.drawString(20*mm, footer_y, f"Fax: {hospital_header.fax_number}")
                footer_y -= 5*mm
            if hospital_header.website_url and hospital_header.website_position in ['bottom-left', 'bottom_center', 'bottom-right']:
                c.drawString(20*mm, footer_y, hospital_header.website_url)
                footer_y -= 5*mm
            if hospital_header.emergency_contact and hospital_header.emergency_contact_position in ['bottom-left', 'bottom_center', 'bottom-right']:
                c.drawString(20*mm, footer_y, f"Emergency: {hospital_header.emergency_contact}")
                footer_y -= 5*mm
            if hospital_header.accreditation and hospital_header.accreditations_position in ['bottom-left', 'bottom_center', 'bottom-right']:
                c.drawString(20*mm, footer_y, hospital_header.accreditation)
        else:
            c.setFont(default_font, 12)
            c.setFillColor(HexColor(default_heading_color))
            c.drawString(20*mm, 280*mm, report.patient.hospital.name)
            c.setFont(default_font, 10)
            c.setFillColor(HexColor(default_text_color))
            c.drawString(20*mm, 15*mm, "Default Footer")

        c.setFont('Helvetica', 12)
        c.setFillColor('black')
        c.drawString(20*mm, 240*mm, f"Report for {report.patient.first_name} {report.patient.last_name}")
        text_object = c.beginText(20*mm, 230*mm)
        text_object.setFont('Helvetica', 10)
        for line in report.content.split('\n'):
            text_object.textLine(line)
        c.drawText(text_object)

        images = Image.objects.filter(report=report)
        y_position = 200*mm
        for image in images:
            if os.path.exists(os.path.join(settings.MEDIA_ROOT, image.file.name)):
                c.drawImage(
                    os.path.join(settings.MEDIA_ROOT, image.file.name),
                    20*mm, y_position, width=60*mm, height=30*mm
                )
                y_position -= 35*mm
            else:
                logger.warning(f"Image not found for report {report.id}: {image.file.name}")

        c.showPage()
        c.save()
        buffer.seek(0)

        response = Response(
            buffer.getvalue(),
            content_type='application/pdf',
            status=status.HTTP_200_OK
        )
        response['Content-Disposition'] = f'attachment; filename=report_{report.id}.pdf'
        UserActivity.objects.create(
            user=request.user,
            action='export_pdf',
            details=f'PDF exported for report {report.id}'
        )
        logger.info(f"PDF exported for report {report.id}")
        return response



    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        report = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['submitted', 'review']:
            return Response({'error': 'وضعیت نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        report.status = new_status
        report.save()
        UserActivity.objects.create(
            user=self.request.user,
            action='change_report_status',
            details=f'Report {report.id} status changed to {new_status}'
        )
        logger.info(f"Report {report.id} status changed to {new_status} by user {self.request.user.username}")
        return Response({'status': f'وضعیت گزارش به {new_status} تغییر کرد'})

    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        report = self.get_object()
        export_to = request.data.get('export_to', [])

        results = {}
        if 'pacs' in export_to:
            pacs = PACS.objects.filter(hospital=report.patient.hospital).first()
            if pacs:
                try:
                    ae = AE(ae_title=pacs.ae_title_local)
                    ae.add_requested_context(EncapsulatedPDFStorage, ExplicitVRLittleEndian)
                    assoc = ae.associate(
                        pacs.server_address,
                        pacs.port,
                        ae_title=pacs.ae_title_remote
                    )
                    if assoc.is_established:
                        ds = Dataset()
                        ds.PatientName = f"{report.patient.first_name}^{report.patient.last_name}"
                        ds.PatientID = report.patient.national_id
                        ds.StudyDate = datetime.now().strftime('%Y%m%d')
                        ds.StudyDescription = report.content[:100]
                        ds.StudyInstanceUID = str(report.token)
                        ds.SeriesInstanceUID = str(uuid.uuid4())
                        ds.SOPInstanceUID = str(uuid.uuid4())
                        ds.SOPClassUID = sop_class.EncapsulatedPDFStorage
                        ds.EncapsulatedDocument = report.content.encode('utf-8')

                        status = assoc.send_c_store(ds)
                        assoc.release()
                        if status.Status == 0:
                            results['pacs'] = 'با موفقیت به PACS ارسال شد'
                            UserActivity.objects.create(
                                user=request.user,
                                action='export_to_pacs',
                                details=f'Report {report.id} exported to PACS'
                            )
                            logger.info(f"Report {report.id} exported to PACS at {pacs.server_address}:{pacs.port}")
                        else:
                            results['pacs'] = f'خطا در ارسال به PACS: Status {status.Status}'
                            logger.error(f"Failed to export report {report.id} to PACS: Status {status.Status}")
                    else:
                        results['pacs'] = 'خطا در اتصال به PACS'
                        logger.error(f"Failed to connect to PACS {pacs.server_address}:{pacs.port}")
                except Exception as e:
                    results['pacs'] = f'خطا در ارسال به PACS: {str(e)}'
                    logger.error(f"Failed to export report {report.id} to PACS: {str(e)}")
            else:
                results['pacs'] = 'PACS پیکربندی نشده است'
                logger.warning(f"No PACS configured for hospital {report.patient.hospital.id}")

        if 'ehr' in export_to:
            ehr = EHR.objects.filter(hospital=report.patient.hospital).first()
            if ehr:
                try:
                    headers = {'Authorization': f'Bearer {ehr.auth_token}'} if ehr.auth_token else {}
                    response = requests.post(
                        ehr.endpoint,
                        json={
                            'report_id': report.id,
                            'content': report.content,
                            'patient_id': report.patient.national_id
                        },
                        headers=headers,
                        timeout=10
                    )
                    response.raise_for_status()
                    results['ehr'] = 'با موفقیت به EHR ارسال شد'
                    UserActivity.objects.create(
                        user=request.user,
                        action='export_to_ehr',
                        details=f'Report {report.id} exported to EHR'
                    )
                    logger.info(f"Report {report.id} exported to EHR at {ehr.endpoint}")
                except requests.exceptions.RequestException as e:
                    results['ehr'] = f'خطا در ارسال به EHR: {str(e)}'
                    logger.error(f"Failed to export report {report.id} to EHR: {str(e)}")
            else:
                results['ehr'] = 'EHR پیکربندی نشده است'
                logger.warning(f"No EHR configured for hospital {report.patient.hospital.id}")

        if 'sms' in export_to:
            patient_phone = report.patient.phone
            try:
                response = requests.post(
                    'https://api.sms-provider.com/send',
                    json={
                        'phone': patient_phone,
                        'message': f'Your report is ready. Token: {report.token}'
                    },
                    headers={'Authorization': f'Bearer {settings.SMS_API_KEY}'},
                    timeout=10
                )
                response.raise_for_status()
                results['sms'] = 'پیامک با موفقیت ارسال شد'
                UserActivity.objects.create(
                    user=request.user,
                    action='export_sms',
                    details=f'SMS sent for report {report.id} to {patient_phone}'
                )
                logger.info(f"SMS sent for report {report.id} to {patient_phone}")
            except requests.exceptions.RequestException as e:
                results['sms'] = f'خطا در ارسال پیامک: {str(e)}'
                logger.error(f"Failed to send SMS for report {report.id}: {str(e)}")

        UserActivity.objects.create(
            user=request.user,
            action='export_report',
            details=f'Report {report.id} exported: {json.dumps(results)}'
        )
        logger.info(f"Export completed for report {report.id}: {results}")
        return Response({'status': 'صادرات گزارش تکمیل شد', 'results': results})

    @action(detail=False, methods=['get'], url_path=r'view_patient_reports/(?P<patient_id>\d+)')
    def view_patient_reports(self, request, patient_id=None):
        if not patient_id:
            return Response({'error': 'شناسه بیمار الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({'error': 'بیمار یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        reports = Report.objects.filter(patient=patient, is_deleted=False)
        serializer = ReportSerializer(reports, many=True)
        
        UserActivity.objects.create(
            user=request.user,
            action='view_patient_reports',
            details=f'Secretary viewed reports for patient {patient.national_id}'
        )
        logger.info(f"Reports viewed for patient {patient.national_id} by user {self.request.user.username}")
        
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def completed_patients_reports(self, request):
        """
        Retrieve all reports for patients with completed reports (has_report=True), accessible only to secretaries.
        """
        queryset = Report.objects.filter(patient__has_report=True, is_deleted=False)
        
        patient_id = request.query_params.get('patient_id', '')
        if patient_id:
            try:
                patient_id = int(patient_id)
                queryset = queryset.filter(patient_id=patient_id)
            except ValueError:
                return Response({'error': 'شناسه بیمار نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

        name = request.query_params.get('name', '')
        if name:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=name) | Q(patient__last_name__icontains=name)
            )

        national_id = request.query_params.get('national_id', '')
        if national_id:
            queryset = queryset.filter(patient__national_id__icontains=national_id)

        report_date = request.query_params.get('report_date', '')
        if report_date:
            try:
                filter_date = datetime.strptime(report_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date=filter_date)
            except ValueError:
                return Response({'error': 'فرمت تاریخ نامعتبر است. از YYYY-MM-DD استفاده کنید'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReportSerializer(queryset, many=True)
        
        UserActivity.objects.create(
            user=request.user,
            action='view_completed_patients_reports',
            details=f'Secretary viewed reports for completed patients'
        )
        logger.info(f"Completed patients reports viewed by user {self.request.user.username}")
        
        return Response(serializer.data)

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsDoctorOrSecretary]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == 'doctor':
            queryset = queryset.filter(doctor=self.request.user)
        return queryset.order_by('date', 'time')

    def perform_create(self, serializer):
        appointment = serializer.save()
        UserActivity.objects.create(
            user=self.request.user,
            action='create_appointment',
            details=f'Appointment {appointment.id} created for patient {appointment.patient.national_id}'
        )
        logger.info(f"Appointment {appointment.id} created by user {self.request.user.username}")

    def perform_create(self, serializer):
        appointment = serializer.save()
        patient = appointment.patient
        message = f"بیمار گرامی {patient.first_name} {patient.last_name}، نوبت شما برای تاریخ {appointment.date} ساعت {appointment.time.strftime('%I:%M %p')} با دکتر {appointment.doctor.preferred_name} ثبت شد."
        try:
            sms_response = requests.post(
                'https://api.sms-provider.com/send',
                json={'phone': patient.phone, 'message': message},
                headers={'Authorization': f'Bearer {settings.SMS_API_KEY}'},
                timeout=10
            )
            sms_response.raise_for_status()
            logger.info(f"SMS sent for appointment {appointment.id} to {patient.phone}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send SMS for appointment {appointment.id}: {str(e)}")
        UserActivity.objects.create(
            user=self.request.user,
            action='create_appointment',
            details=f'Appointment {appointment.id} created for patient {appointment.patient.national_id}'
        )
        logger.info(f"Appointment {appointment.id} created by user {self.request.user.username}")

    @action(detail=False, methods=['get'])
    def stats(self, request):
        tab = request.query_params.get('tab', 'today')
        hospital_id = request.query_params.get('hospital_id', '')
        date_str = request.query_params.get('date', '')

        queryset = Appointment.objects.all()

        if hospital_id:
            try:
                hospital_id = int(hospital_id)
                queryset = queryset.filter(patient__hospital_id=hospital_id)
            except ValueError:
                return Response({'error': 'شناسه بیمارستان نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.role == 'doctor':
            queryset = queryset.filter(doctor=self.request.user)

        today = date.today()
        if tab == 'today':
            if date_str:
                try:
                    filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    queryset = queryset.filter(date=filter_date)
                except ValueError:
                    return Response({'error': 'فرمت تاریخ نامعتبر است. از YYYY-MM-DD استفاده کنید'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                queryset = queryset.filter(date=today)
        elif tab == 'future':
            queryset = queryset.filter(date__gt=today)
        elif tab == 'past':
            queryset = queryset.filter(date__lt=today)
        else:
            return Response({'error': 'تب نامعتبر است. از today، future یا past استفاده کنید'}, status=status.HTTP_400_BAD_REQUEST)

        stats = queryset.aggregate(
            total_appointments=Count('id'),
            scheduled=Count('id', filter=Q(status='scheduled')),
            cancelled=Count('id', filter=Q(status='cancelled')),
            completed=Count('id', filter=Q(status='completed')),
            pending=Count('id', filter=Q(status='pending'))
        )

        return Response({
            'total_appointments': stats['total_appointments'] or 0,
            'scheduled': stats['scheduled'] or 0,
            'cancelled': stats['cancelled'] or 0,
            'completed': stats['completed'] or 0,
            'pending': stats['pending'] or 0
        })

    @action(detail=False, methods=['get'])
    def dashboard_appointments(self, request):
        date_filter = request.query_params.get('date', date.today())
        try:
            date_filter = datetime.strptime(date_filter, '%Y-%m-%d').date()
        except ValueError:
            date_filter = date.today()

        appointments = Appointment.objects.filter(
            date=date_filter,
            status='scheduled'
        )
        if self.request.user.role == 'doctor':
            appointments = appointments.filter(doctor=self.request.user)
        appointments = appointments.order_by('time')
        serializer = self.get_serializer(appointments, many=True)
        return Response({'today': serializer.data})

    @action(detail=False, methods=['get'])
    def future_appointments(self, request):
        days = request.query_params.get('days', 10)
        date_filter = request.query_params.get('date')
        try:
            days = int(days)
            if days < 1:
                raise ValueError("Days must be a positive integer.")
        except ValueError:
            return Response({'error': 'پارامتر days نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

        if date_filter:
            try:
                start_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                end_date = start_date
            except ValueError:
                return Response({'error': 'فرمت تاریخ نامعتبر است. از YYYY-MM-DD استفاده کنید'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            start_date = date.today()
            end_date = start_date + timedelta(days=days)

        appointments = Appointment.objects.filter(
            date__range=[start_date, end_date],
            status='scheduled'
        )
        if self.request.user.role == 'doctor':
            appointments = appointments.filter(doctor=self.request.user)
        appointments = appointments.order_by('date', 'time')
        serializer = self.get_serializer(appointments, many=True)
        return Response({'appointments': serializer.data})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        try:
            appointment = self.get_object()
            appointment.status = 'cancelled'
            appointment.save()
            UserActivity.objects.create(
                user=self.request.user,
                action='cancel_appointment',
                details=f'Appointment {appointment.id} cancelled'
            )
            logger.info(f"Appointment {appointment.id} cancelled by user {self.request.user.username}")
            return Response({'status': 'لغو شد'}, status=status.HTTP_200_OK)
        except Appointment.DoesNotExist:
            logger.error(f"Appointment with id {pk} not found for user {request.user.username}")
            return Response({'error': f'قرار ملاقات با شناسه {pk} یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None):
        appointment = self.get_object()
        appointment_id = appointment.id
        appointment.delete()
        UserActivity.objects.create(
            user=self.request.user,
            action='delete_appointment',
            details=f'Appointment {appointment_id} deleted'
        )
        logger.info(f"Appointment {appointment_id} deleted by user {self.request.user.username}")
        return Response({'message': 'نوبت با موفقیت حذف شد'})

class ModalityViewSet(viewsets.ModelViewSet):
    queryset = Modality.objects.all()
    serializer_class = ModalitySerializer
    permission_classes = [IsAuthenticated]

class ReportMessageViewSet(viewsets.ModelViewSet):
    queryset = ReportMessage.objects.all()
    serializer_class = ReportMessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['report', 'sender', 'receiver']

# class PACSViewSet(viewsets.ModelViewSet):
#     queryset = PACS.objects.all()
#     serializer_class = PACSSerializer
#     permission_classes = [IsAuthenticated, IsAdminOrSupervisor]

#     @action(detail=True, methods=['post'])
#     def test_connection(self, request, pk=None):
#         pacs = self.get_object()
#         try:
#             ae = AE(ae_title=pacs.ae_title_local)
#             ae.add_requested_context(Verification)
#             assoc = ae.associate(
#                 pacs.server_address,
#                 pacs.server_port,
#                 ae_title=pacs.ae_title_remote
#             )
#             if assoc.is_established:
#                 response = assoc.send_c_echo()
#                 assoc.release()
#                 UserActivity.objects.create(
#                     user=self.request.user,
#                     action='test_pacs_connection',
#                     details=f'PACS connection test successful for {pacs.server_address}:{pacs.server_port}'
#                 )
#                 logger.info(f"PACS connection test successful for {pacs.server_address}:{pacs.server_port}")
#                 return Response({
#                     'status': 'success',
#                     'message': 'اتصال موفق',
#                     'color': 'green'
#                 }, status=status.HTTP_200_OK)
#             else:
#                 UserActivity.objects.create(
#                     user=self.request.user,
#                     action='test_pacs_connection',
#                     details=f'PACS connection test failed for {pacs.server_address}:{pacs.server_port}'
#                 )
#                 logger.error(f"PACS connection test failed for {pacs.server_address}:{pacs.server_port}")
#                 return Response({
#                     'status': 'error',
#                     'message': 'خطا در اتصال',
#                     'color': 'red'
#                 }, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             UserActivity.objects.create(
#                 user=self.request.user,
#                 action='test_pacs_connection',
#                 details=f'PACS connection test error: {str(e)}'
#             )
#             logger.error(f"PACS connection test error: {str(e)}")
#             return Response({
#                 'status': 'error',
#                 'message': f'خطا: {str(e)}',
#                 'color': 'red'
#             }, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=True, methods=['post'])
#     def send_report(self, request, pk=None):
#         pacs = self.get_object()
#         report_id = request.data.get('report_id')
#         try:
#             report = Report.objects.get(id=report_id)
#             patient = report.patient

#             ae = AE(ae_title=pacs.ae_title_local)
#             ae.add_requested_context(StudyRootQueryRetrieveInformationModelMove)
#             assoc = ae.associate(
#                 pacs.server_address,
#                 pacs.server_port,
#                 ae_title=pacs.ae_title_remote
#             )
#             if assoc.is_established:
#                 ds = Dataset()
#                 ds.PatientName = f"{patient.first_name}^{patient.last_name}"
#                 ds.PatientID = patient.national_id
#                 ds.StudyDate = datetime.now().strftime('%Y%m%d')
#                 ds.StudyDescription = report.content[:100]

#                 assoc.send_c_store(ds)
#                 assoc.release()
#                 UserActivity.objects.create(
#                     user=self.request.user,
#                     action='send_report_to_pacs',
#                     details=f'Report {report.id} sent to PACS {pacs.server_address}:{pacs.server_port}'
#                 )
#                 logger.info(f"Report {report.id} sent to PACS {pacs.server_address}:{pacs.server_port}")
#                 return Response({
#                     'status': 'success',
#                     'message': 'گزارش با موفقیت به PACS ارسال شد'
#                 }, status=status.HTTP_200_OK)
#             else:
#                 UserActivity.objects.create(
#                     user=self.request.user,
#                     action='send_report_to_pacs',
#                     details=f'Failed to send report {report.id} to PACS {pacs.server_address}:{pacs.server_port}'
#                 )
#                 logger.error(f"Failed to connect to PACS {pacs.server_address}:{pacs.server_port}")
#                 return Response({
#                     'status': 'error',
#                     'message': 'خطا در اتصال به PACS'
#                 }, status=status.HTTP_400_BAD_REQUEST)
#         except Report.DoesNotExist:
#             return Response({'error': 'گزارش یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             UserActivity.objects.create(
#                 user=self.request.user,
#                 action='send_report_to_pacs',
#                 details=f'Error sending report to PACS: {str(e)}'
#             )
#             logger.error(f"Failed to send report to PACS: {str(e)}")
#             return Response({
#                 'status': 'error',
#                 'message': f'خطا در ارسال گزارش: {str(e)}'
#             }, status=status.HTTP_400_BAD_REQUEST)

#     @action(detail=True, methods=['get'])
#     def fetch_patient_data(self, request, pk=None):
#         pacs = self.get_object()
#         national_id = request.query_params.get('national_id')
#         if not national_id:
#             return Response({'error': 'کد ملی بیمار الزامی است'}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             ae = AE(ae_title=pacs.ae_title_local)
#             ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
#             assoc = ae.associate(
#                 pacs.server_address,
#                 pacs.server_port,
#                 ae_title=pacs.ae_title_remote
#             )
#             if assoc.is_established:
#                 ds = Dataset()
#                 ds.QueryRetrieveLevel = 'PATIENT'
#                 ds.PatientID = national_id
#                 ds.PatientName = ''
#                 ds.PatientBirthDate = ''

#                 responses = assoc.send_c_find(ds)
#                 patient_data = []
#                 for (status, identifier) in responses:
#                     if status and identifier:
#                         patient_data.append({
#                             'PatientName': str(identifier.get('PatientName', '')),
#                             'PatientID': identifier.get('PatientID', ''),
#                             'BirthDate': identifier.get('PatientBirthDate', '')
#                         })
#                 assoc.release()
#                 UserActivity.objects.create(
#                     user=self.request.user,
#                     action='fetch_pacs_data',
#                     details=f'Patient data fetched from PACS {pacs.server_address}:{pacs.server_port} for patient {national_id}'
#                 )
#                 logger.info(f"Patient data fetched from PACS {pacs.server_address}:{pacs.server_port}")
#                 return Response({
#                     'status': 'success',
#                     'data': patient_data
#                 }, status=status.HTTP_200_OK)
#             else:
#                 UserActivity.objects.create(
#                     user=self.request.user,
#                     action='fetch_pacs_data',
#                     details=f'Failed to fetch data from PACS {pacs.server_address}:{pacs.server_port}'
#                 )
#                 logger.error(f"Failed to connect to PACS {pacs.server_address}:{pacs.server_port}")
#                 return Response({
#                     'status': 'error',
#                     'message': 'خطا در اتصال به PACS'
#                 }, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             UserActivity.objects.create(
#                 user=self.request.user,
#                 action='fetch_pacs_data',
#                 details=f'Failed to fetch patient data from PACS: {str(e)}'
#             )
#             logger.error(f"Failed to fetch patient data from PACS: {str(e)}")
#             return Response({
#                 'status': 'error',
#                 'message': f'خطا در دریافت داده: {str(e)}'
#             }, status=status.HTTP_400_BAD_REQUEST)


logger = logging.getLogger('medical_reports')

class EHRViewSet(viewsets.ModelViewSet):
    queryset = EHR.objects.all()
    serializer_class = EHRSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSupervisor]

    @action(detail=True, methods=['post'])
    def sync_with_pacs(self, request, pk=None):
        ehr = self.get_object()
        report_id = request.data.get('report_id')
        pacs = PACS.objects.filter(hospital=ehr.hospital).first()
        if not pacs:
            return Response({'error': 'سیستم PACS برای این بیمارستان پیکربندی نشده است'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            report = Report.objects.get(id=report_id)
            patient = report.patient

            ae = AE(ae_title=pacs.ae_title_local)
            ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind, ExplicitVRLittleEndian)
            assoc = ae.associate(
                pacs.server_address,
                pacs.port,
                ae_title=pacs.ae_title_remote
            )
            if assoc.is_established:
                ds = Dataset()
                ds.QueryRetrieveLevel = 'PATIENT'
                ds.PatientID = patient.national_id
                ds.PatientName = ''
                ds.PatientBirthDate = ''

                responses = assoc.send_c_find(ds)
                patient_data = None
                for (status, identifier) in responses:
                    if status and identifier:
                        patient_data = {
                            'PatientName': str(identifier.get('PatientName', '')),
                            'PatientID': identifier.get('PatientID', ''),
                            'BirthDate': identifier.get('PatientBirthDate', '')
                        }
                        break
                assoc.release()

                if not patient_data:
                    UserActivity.objects.create(
                        user=self.request.user,
                        action='sync_with_pacs',
                        details=f'No patient data found in PACS for patient {patient.national_id}'
                    )
                    logger.error(f"No patient data found in PACS for patient {patient.national_id}")
                    return Response({
                        'status': 'error',
                        'message': 'داده‌ای برای بیمار در PACS یافت نشد'
                    }, status=status.HTTP_404_NOT_FOUND)

                ehr_data = {
                    'patient_id': patient.national_id,
                    'report_id': report.id,
                    'content': report.content,
                    'patient_info': patient_data
                }
                headers = {'Authorization': f'Bearer {ehr.auth_token}'} if ehr.auth_token else {}
                response = requests.post(
                    f'{ehr.endpoint}/reports',
                    json=ehr_data,
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                UserActivity.objects.create(
                    user=self.request.user,
                    action='sync_with_pacs',
                    details=f'Report {report.id} synced with EHR {ehr.endpoint}'
                )
                logger.info(f"Report {report.id} synced with EHR {ehr.endpoint}")
                return Response({
                    'status': 'success',
                    'message': 'گزارش با موفقیت با EHR همگام‌سازی شد'
                }, status=status.HTTP_200_OK)
            else:
                UserActivity.objects.create(
                    user=self.request.user,
                    action='sync_with_pacs',
                    details=f'Failed to connect to PACS {pacs.server_address}:{pacs.port}'
                )
                logger.error(f"Failed to connect to PACS {pacs.server_address}:{pacs.port}")
                return Response({
                    'status': 'error',
                    'message': 'خطا در اتصال به PACS'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Report.DoesNotExist:
            return Response({'error': 'گزارش یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        except requests.exceptions.RequestException as e:
            UserActivity.objects.create(
                user=self.request.user,
                action='sync_with_pacs',
                details=f'Failed to sync report with EHR: {str(e)}'
            )
            logger.error(f"Failed to sync report with EHR: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'خطا در همگام‌سازی با EHR: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            UserActivity.objects.create(
                user=self.request.user,
                action='sync_with_pacs',
                details=f'Error syncing with EHR: {str(e)}'
            )
            logger.error(f"Error syncing with EHR: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'خطا: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)



# from rest_framework import viewsets, status
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.decorators import action
# from pynetdicom import AE, sop_class
# from pynetdicom.sop_class import Verification, PatientRootQueryRetrieveInformationModelFind, EncapsulatedPDFStorage
# from pydicom.dataset import Dataset
# from pydicom.uid import ExplicitVRLittleEndian
# from .models import PACS, Patient, Report, Image, UserActivity, Hospital
# from .serializers import PACSSerializer
# import logging
# import uuid
# from django.views.decorators.cache import cache_page

logger = logging.getLogger('medical_reports')

class PACSViewSet(viewsets.ModelViewSet):
    queryset = PACS.objects.all()
    serializer_class = PACSSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSupervisor]

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        pacs = self.get_object()
        try:
            ae = AE(ae_title=pacs.ae_title_local)
            ae.add_requested_context(Verification, ExplicitVRLittleEndian)
            assoc = ae.associate(pacs.server_address, pacs.port, ae_title=pacs.ae_title_remote)
            if assoc.is_established:
                response = assoc.send_c_echo()
                assoc.release()
                UserActivity.objects.create(
                    user=request.user,
                    action='test_pacs_connection',
                    details=f'PACS connection test successful for {pacs.server_address}:{pacs.port}'
                )
                logger.info(f"PACS connection test successful for {pacs.server_address}:{pacs.port}")
                return Response({
                    'status': 'success',
                    'message': 'اتصال موفق',
                    'color': 'green'
                }, status=status.HTTP_200_OK)
            else:
                UserActivity.objects.create(
                    user=request.user,
                    action='test_pacs_connection',
                    details=f'PACS connection test failed for {pacs.server_address}:{pacs.port}'
                )
                logger.error(f"PACS connection test failed for {pacs.server_address}:{pacs.port}")
                return Response({
                    'status': 'error',
                    'message': 'خطا در اتصال',
                    'color': 'red'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            UserActivity.objects.create(
                user=request.user,
                action='test_pacs_connection',
                details=f'PACS connection test error: {str(e)}'
            )
            logger.error(f"PACS connection test error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'خطا: {str(e)}',
                'color': 'red'
            }, status=status.HTTP_400_BAD_REQUEST)
    

    def destroy(self, request, *args, **kwargs):
        try:
            pacs = self.get_object()
            pacs_id = pacs.id
            pacs_name = pacs.name
            pacs.delete()
            UserActivity.objects.create(
                user=self.request.user,
                action='delete_pacs',
                details=f'PACS {pacs_id} ({pacs_name}) deleted by {request.user.username}'
            )
            logger.info(f"PACS {pacs_id} ({pacs_name}) deleted by {request.user.username}")
            return Response({'message': 'PACS با موفقیت حذف شد'}, status=status.HTTP_200_OK)
        except PACS.DoesNotExist:
            logger.error(f"PACS with id {kwargs.get('pk')} not found for deletion by {request.user.username}")
            return Response({'error': 'PACS با این شناسه یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to delete PACS by {request.user.username}: {str(e)}")
            return Response({'error': f'خطا در حذف PACS: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=['post'])
    def send_report(self, request, pk=None):
        try:
            pacs = self.get_object()
            report_id = request.data.get('report_id')
            if not report_id:
                return Response({'error': 'شناسه گزارش الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
            
            report = Report.objects.get(id=report_id)
            patient = report.patient

            ae = AE(ae_title=pacs.ae_title_local)
            ae.add_requested_context(EncapsulatedPDFStorage, ExplicitVRLittleEndian)
            assoc = ae.associate(pacs.server_address, pacs.port, ae_title=pacs.ae_title_remote)
            
            if assoc.is_established:
                ds = Dataset()
                ds.file_meta = FileMetaDataset()
                ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
                ds.SOPClassUID = EncapsulatedPDFStorage
                ds.SOPInstanceUID = pydicom.uid.generate_uid()
                ds.PatientID = patient.national_id
                ds.StudyInstanceUID = pydicom.uid.generate_uid()
                ds.SeriesInstanceUID = pydicom.uid.generate_uid()
                
                pdf_content = report.content.encode('utf-8')
                ds.EncapsulatedDocument = pdf_content
                ds.MIMETypeOfEncapsulatedDocument = 'application/pdf'

                status_response = assoc.send_c_store(ds)
                assoc.release()
                
                if status_response.Status == 0x0000:
                    UserActivity.objects.create(
                        user=self.request.user,
                        action='send_to_pacs',
                        details=f'Report {report.id} sent to PACS {pacs.server_address}:{pacs.port}'
                    )
                    logger.info(f"Report {report.id} sent to PACS {pacs.server_address}:{pacs.port}")
                    return Response({
                        'status': 'success',
                        'message': 'گزارش با موفقیت به PACS ارسال شد'
                    }, status=status.HTTP_200_OK)
                else:
                    UserActivity.objects.create(
                        user=self.request.user,
                        action='send_to_pacs',
                        details=f'Failed to send report {report.id} to PACS {pacs.server_address}:{pacs.port}'
                    )
                    logger.error(f"Failed to send report {report.id} to PACS {pacs.server_address}:{pacs.port}")
                    return Response({
                        'status': 'error',
                        'message': 'خطا در ارسال گزارش به PACS'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                UserActivity.objects.create(
                    user=self.request.user,
                    action='send_to_pacs',
                    details=f'Failed to connect to PACS {pacs.server_address}:{pacs.port}'
                )
                logger.error(f"Failed to connect to PACS {pacs.server_address}:{pacs.port}")
                return Response({
                    'status': 'error',
                    'message': 'خطا در اتصال به PACS'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Report.DoesNotExist:
            UserActivity.objects.create(
                user=self.request.user,
                action='send_to_pacs',
                details=f'Report {report_id} not found'
            )
            logger.error(f"Report {report_id} not found")
            return Response({'error': 'گزارش یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            UserActivity.objects.create(
                user=self.request.user,
                action='send_to_pacs',
                details=f'Failed to send report to PACS: {str(e)}'
            )
            logger.error(f"Failed to send report to PACS: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'خطا در ارسال گزارش: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def send_image(self, request, pk=None):
        pacs = self.get_object()
        image_id = request.data.get('image_id')
        try:
            image = Image.objects.get(id=image_id)
            patient = image.patient
            ae = AE(ae_title=pacs.ae_title_local)
            ae.add_requested_context(sop_class.MRImageStorage, ExplicitVRLittleEndian)
            assoc = ae.associate(pacs.server_address, pacs.port, ae_title=pacs.ae_title_remote)
            if assoc.is_established:
                from pydicom.filebase import DicomFile
                with DicomFile(os.path.join(settings.MEDIA_ROOT, image.file.name), 'rb') as f:
                    ds = f.read()
                ds.PatientName = f"{patient.first_name}^{patient.last_name}"
                ds.PatientID = patient.national_id
                ds.StudyInstanceUID = str(uuid.uuid4())
                ds.SeriesInstanceUID = str(uuid.uuid4())
                ds.SOPInstanceUID = str(uuid.uuid4())
                ds.StudyDate = datetime.now().strftime('%Y%m%d')

                status = assoc.send_c_store(ds)
                assoc.release()
                if status.Status == 0:
                    UserActivity.objects.create(
                        user=request.user,
                        action='send_image_to_pacs',
                        details=f'Image {image.id} sent to PACS {pacs.server_address}:{pacs.port}'
                    )
                    logger.info(f"Image {image.id} sent to PACS {pacs.server_address}:{pacs.port}")
                    return Response({
                        'status': 'success',
                        'message': 'تصویر با موفقیت به PACS ارسال شد'
                    }, status=status.HTTP_200_OK)
                else:
                    UserActivity.objects.create(
                        user=request.user,
                        action='send_image_to_pacs',
                        details=f'Failed to send image {image.id} to PACS: Status {status.Status}'
                    )
                    logger.error(f"Failed to send image {image.id} to PACS: Status {status.Status}")
                    return Response({
                        'status': 'error',
                        'message': f'خطا در ارسال تصویر: Status {status.Status}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                UserActivity.objects.create(
                    user=request.user,
                    action='send_image_to_pacs',
                    details=f'Failed to connect to PACS {pacs.server_address}:{pacs.port}'
                )
                logger.error(f"Failed to connect to PACS {pacs.server_address}:{pacs.port}")
                return Response({
                    'status': 'error',
                    'message': 'خطا در اتصال به PACS'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Image.DoesNotExist:
            return Response({'error': 'تصویر یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            UserActivity.objects.create(
                user=request.user,
                action='send_image_to_pacs',
                details=f'Error sending image to PACS: {str(e)}'
            )
            logger.error(f"Failed to send image to PACS: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'خطا در ارسال تصویر: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    @cache_page(60 * 15)
    def fetch_patient_data(self, request, pk=None):
        pacs = self.get_object()
        try:
            ae = AE(ae_title=pacs.ae_title_local)
            ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind, ExplicitVRLittleEndian)
            assoc = ae.associate(pacs.server_address, pacs.port, ae_title=pacs.ae_title_remote)
            if assoc.is_established:
                ds = Dataset()
                ds.QueryRetrieveLevel = 'PATIENT'
                ds.PatientID = '*'
                ds.PatientName = '*'
                ds.PatientBirthDate = ''

                responses = assoc.send_c_find(ds)
                patient_data = []
                for (status, identifier) in responses:
                    if status and identifier:
                        patient_info = {
                            'PatientName': str(identifier.get('PatientName', '')),
                            'PatientID': identifier.get('PatientID', ''),
                            'BirthDate': identifier.get('PatientBirthDate', '')
                        }
                        if patient_info['PatientID']:
                            name_parts = patient_info['PatientName'].split('^') if '^' in patient_info['PatientName'] else [patient_info['PatientName'], '']
                            first_name = name_parts[0]
                            last_name = name_parts[1] if len(name_parts) > 1 else ''
                            birth_date = patient_info['BirthDate'] or None
                            if birth_date:
                                try:
                                    birth_date = datetime.strptime(birth_date, '%Y%m%d').date()
                                except ValueError:
                                    birth_date = None
                            patient, created = Patient.objects.get_or_create(
                                national_id=patient_info['PatientID'],
                                defaults={
                                    'first_name': first_name,
                                    'last_name': last_name,
                                    'hospital': pacs.hospital,
                                    'birth_date': birth_date,
                                    'gender': 'unknown',
                                    'phone': '',
                                    'modality': 'unknown',
                                    'status': 'pending'
                                }
                            )
                            if created:
                                logger.info(f"New patient created: {patient.national_id}")
                        patient_data.append(patient_info)
                assoc.release()
                UserActivity.objects.create(
                    user=self.request.user,
                    action='fetch_pacs_data',
                    details=f'Patient data fetched from PACS {pacs.server_address}:{pacs.port}'
                )
                logger.info(f"Patient data fetched from PACS {pacs.server_address}:{pacs.port}")
                return Response({
                    'status': 'success',
                    'data': patient_data
                }, status=status.HTTP_200_OK)
            else:
                UserActivity.objects.create(
                    user=self.request.user,
                    action='fetch_pacs_data',
                    details=f'Failed to connect to PACS {pacs.server_address}:{pacs.port}'
                )
                logger.error(f"Failed to connect to PACS {pacs.server_address}:{pacs.port}")
                return Response({
                    'status': 'error',
                    'message': 'خطا در اتصال به PACS'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            UserActivity.objects.create(
                user=self.request.user,
                action='fetch_pacs_data',
                details=f'Failed to fetch patient data from PACS: {str(e)}'
            )
            logger.error(f"Failed to fetch patient data from PACS: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'خطا در دریافت داده: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)



class FieldMappingViewSet(viewsets.ModelViewSet):
    queryset = FieldMapping.objects.all()
    serializer_class = FieldMappingSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def by_hospital(self, request):
        hospital_id = request.query_params.get('hospital_id')
        if not hospital_id:
            return Response({'error': 'شناسه بیمارستان الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        mappings = FieldMapping.objects.filter(hospital_id=hospital_id)
        serializer = self.get_serializer(mappings, many=True)
        return Response(serializer.data)

class ReportTemplateViewSet(viewsets.ModelViewSet):
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSupervisor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['modality', 'hospital']

    @action(detail=False, methods=['get'])
    def by_modality(self, request):
        modality = request.query_params.get('modality')
        if not modality:
            return Response({'error': 'مدالیتی الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        templates = ReportTemplate.objects.filter(modality=modality)
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)

class UserActivityViewSet(viewsets.ModelViewSet):
    queryset = UserActivity.objects.all()
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated, IsAdminOrSupervisor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'action', 'timestamp']

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'شناسه کاربر الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        activities = UserActivity.objects.filter(user_id=user_id).order_by('-timestamp')
        serializer = UserActivitySerializer(activities, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'شناسه کاربر الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        activities = UserActivity.objects.filter(user_id=user_id)
        login_count = activities.filter(action='login').count()
        report_count = activities.filter(action='create_report').count()
        last_login = activities.filter(action='login').order_by('-timestamp').first()
        return Response({
            'login_count': login_count,
            'report_count': report_count,
            'last_login': last_login.timestamp if last_login else None,
            'recent_activities': UserActivitySerializer(activities.order_by('-timestamp')[:5], many=True).data
        })

    @action(detail=False, methods=['get'])
    def all_activities(self, request):
        try:
            activities = UserActivity.objects.all().order_by('-timestamp')
            serializer = UserActivitySerializer(activities, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to retrieve all activities by {request.user.username}: {str(e)}")
            return Response({'error': f'خطا در دریافت فعالیت‌ها: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ImageViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    permission_classes = [IsAuthenticated]

class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]

class HospitalHeaderViewSet(viewsets.ModelViewSet):
    queryset = HospitalHeader.objects.all()
    serializer_class = HospitalHeaderSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSupervisor]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['hospital', 'department']

    @action(detail=False, methods=['get'])
    def by_department(self, request):
        hospital_id = request.query_params.get('hospital_id')
        department = request.query_params.get('department', '')
        if not hospital_id:
            return Response({'error': 'شناسه بیمارستان الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        headers = HospitalHeader.objects.filter(hospital_id=hospital_id, department=department)
        serializer = self.get_serializer(headers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        header = self.get_object()
        serializer = HospitalHeaderSerializer(header)
        buffer = BytesIO()
        page_size = A4
        if header.paper_size:
            page_sizes = {'A4': A4, 'Letter': letter, 'Legal': legal}
            page_size = page_sizes.get(header.paper_size, A4)

        c = canvas.Canvas(buffer, pagesize=page_size)
        
        c.setFont(header.font_family or 'Helvetica', 12)
        c.setFillColor(HexColor(header.heading_color or '#000000'))

        x_logo = 20*mm if header.logo_position == 'left' else 160*mm
        x_text = 20*mm if header.logo_position == 'right' else 50*mm
        if header.image and os.path.exists(os.path.join(settings.MEDIA_ROOT, header.image.name)):
            c.drawImage(
                os.path.join(settings.MEDIA_ROOT, header.image.name),
                x_logo, 260*mm, width=30*mm, height=15*mm
            )

        positions = {
            'top-left': (20*mm, 280*mm),
            'top-right': (160*mm, 280*mm),
            'bottom-left': (20*mm, 15*mm),
            'bottom-right': (160*mm, 15*mm)
        }
        if header.name_position in positions:
            c.drawString(*positions[header.name_position], header.hospital.name)
        if header.department and header.department_position in positions:
            c.drawString(*positions[header.department_position], header.department)
        if header.address and header.address_position in positions:
            c.drawString(*positions[header.address_position], header.address)
        if header.phone and header.phone_position in positions:
            c.drawString(*positions[header.phone_position], f"Phone: {header.phone}")
        if header.email_address and header.email_position in positions:
            c.drawString(*positions[header.email_position], f"Email: {header.email_address}")
        if header.fax_number and header.fax_position in positions:
            c.drawString(*positions[header.fax_position], f"Fax: {header.fax_number}")
        if header.qr_code_link and header.qr_code_position in positions:
            c.drawString(*positions[header.qr_code_position], 'Scan QR Code for Report')

        c.setFont(header.font_family or 'Helvetica', 10)
        c.setFillColor(HexColor(header.text_color or '#000000'))
        footer_y = 15*mm
        if header.website_url and header.website_position == 'bottom-left':
            c.drawString(20*mm, footer_y, header.website_url)
            footer_y -= 5*mm
        if header.emergency_contact and header.emergency_contact_position == 'bottom-left':
            c.drawString(20*mm, footer_y, f"Emergency: {header.emergency_contact}")
            footer_y -= 5*mm
        if header.accreditation and header.accreditations_position == 'bottom-left':
            c.drawString(20*mm, footer_y, header.accreditation)

        c.setFont('Helvetica', 12)
        c.setFillColor('black')
        c.drawString(20*mm, 240*mm, "Sample Report Preview")
        text_object = c.beginText(20*mm, 230*mm)
        text_object.setFont('Helvetica', 10)
        text_object.textLine("This is a preview of the hospital header.")
        c.drawText(text_object)

        c.showPage()
        c.save()
        buffer.seek(0)

        response = Response(
            buffer.getvalue(),
            content_type='application/pdf',
            status=status.HTTP_200_OK
        )
        response['Content-Disposition'] = f'inline; filename=header_preview_{header.id}.pdf'
        UserActivity.objects.create(
            user=self.request.user,
            action='preview_header',
            details=f'Header {header.id} previewed for hospital {header.hospital.name}'
        )
        logger.info(f"Header {header.id} previewed by user {self.request.user.username}")
        return response