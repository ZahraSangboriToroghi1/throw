from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView
from .views import (
    UserViewSet, HospitalViewSet, PatientViewSet, ReportViewSet, AppointmentViewSet,
    ModalityViewSet, ReportMessageViewSet, PACSViewSet, EHRViewSet, FieldMappingViewSet,
    ReportTemplateViewSet, UserActivityViewSet, ImageViewSet, PermissionViewSet,
    HospitalHeaderViewSet, WelcomeCardView, ModalityConfigView, LogoutView, AuthMeView,
    DoctorViewSet, DemoRequestView
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'hospitals', HospitalViewSet)
router.register(r'patients', PatientViewSet)
router.register(r'reports', ReportViewSet)
router.register(r'appointments', AppointmentViewSet)
router.register(r'modalities', ModalityViewSet)
router.register(r'report-messages', ReportMessageViewSet)
router.register(r'pacs', PACSViewSet)
router.register(r'ehr', EHRViewSet)
router.register(r'field-mappings', FieldMappingViewSet)
router.register(r'report-templates', ReportTemplateViewSet)
router.register(r'user-activities', UserActivityViewSet)
router.register(r'images', ImageViewSet)
router.register(r'permissions', PermissionViewSet)
router.register(r'hospital-headers', HospitalHeaderViewSet)
router.register(r'doctors', DoctorViewSet, basename='doctors')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', AuthMeView.as_view(), name='auth-me'),
    path('welcome/', WelcomeCardView.as_view(), name='welcome-card'),
    path('demo-request/', DemoRequestView.as_view(), name='demo-request'),
    path('config/modalities/', ModalityConfigView.as_view(), name='modality-config'),
    path('users/search/', UserViewSet.as_view({'get': 'search'}), name='user-search'),
    path('users/doctors/', UserViewSet.as_view({'get': 'doctors'}), name='doctors-list'),
    path('users/<int:pk>/profile/', UserViewSet.as_view({'get': 'profile'}), name='user-profile'),
    path('users/<int:pk>/set_permissions/', UserViewSet.as_view({'post': 'set_permissions'}), name='set-permissions'),
    path('patients/search/', PatientViewSet.as_view({'get': 'search'}), name='patient-search'),
    path('patients/reset_filters/', PatientViewSet.as_view({'get': 'reset_filters'}), name='reset-filters'),
    path('patients/advanced_search/', PatientViewSet.as_view({'get': 'advanced_search'}), name='patient-advanced-search'),
    path('patients/check_national_id/', PatientViewSet.as_view({'post': 'check_national_id'}), name='check-national-id'),
    path('patients/stats/', PatientViewSet.as_view({'get': 'stats'}), name='patient-stats'),
    path('patients/pending_patients/', PatientViewSet.as_view({'get': 'pending_patients'}), name='pending-patients-record'),
    path('patients/completed_patients/', PatientViewSet.as_view({'get': 'completed_patients'}), name='completed_patients'),
    path('patients/<int:pk>/report_status/', PatientViewSet.as_view({'get': 'report_status'}), name='report-status'),
    path('patients/completed_patients/advanced_search/', PatientViewSet.as_view({'get': 'completed_patients_advanced_search'}), name='completed-patients-advanced-search'),
    path('pacs/<int:pk>/test_connection/', PACSViewSet.as_view({'post': 'test_connection'}), name='pacs-test-connection'),
    path('pacs/<int:pk>/send_report/', PACSViewSet.as_view({'post': 'send_report'}), name='pacs-send-report'),
    path('pacs/<int:pk>/fetch_patient_data/', PACSViewSet.as_view({'get': 'fetch_patient_data'}), name='pacs-fetch-patient-data'),
    path('ehr/<int:pk>/sync_with_pacs/', EHRViewSet.as_view({'post': 'sync_with_pacs'}), name='ehr-sync-with-pacs'),
    path('hospital-headers/by_department/', HospitalHeaderViewSet.as_view({'get': 'by_department'}), name='hospital-headers-by-department'),
    path('hospital-headers/<int:pk>/preview/', HospitalHeaderViewSet.as_view({'post': 'preview'}), name='hospital-header-preview'),
    path('report-templates/by_modality/', ReportTemplateViewSet.as_view({'get': 'by_modality'}), name='report-templates-by-modality'),
    path('user-activities/by_user/', UserActivityViewSet.as_view({'get': 'by_user'}), name='user-activities-by-user'),
    path('user-activities/summary/', UserActivityViewSet.as_view({'get': 'summary'}), name='user-activities-summary'),
    path('user-activities/all/', UserActivityViewSet.as_view({'get': 'all_activities'}), name='all-activities'),
    path('field-mappings/by_hospital/', FieldMappingViewSet.as_view({'get': 'by_hospital'}), name='field-mappings-by-hospital'),
    path('reports/<int:pk>/process_audio/', ReportViewSet.as_view({'post': 'process_audio'}), name='report-process-audio'),
    path('reports/<int:pk>/complete/', ReportViewSet.as_view({'post': 'complete'}), name='report-complete'),
    path('reports/<int:pk>/export_pdf/', ReportViewSet.as_view({'post': 'export_pdf'}), name='report-export-pdf'),
    path('reports/<int:pk>/change_status/', ReportViewSet.as_view({'post': 'change_status'}), name='report-change-status'),
    path('reports/<int:pk>/export/', ReportViewSet.as_view({'post': 'export'}), name='report-export'),
    path('reports/<int:pk>/sign/', ReportViewSet.as_view({'post': 'sign'}), name='report-sign'),
    path('reports/<int:pk>/send_email/', ReportViewSet.as_view({'post': 'send_email'}), name='report-send-email'),
    path('reports/<int:pk>/request_revision/', ReportViewSet.as_view({'post': 'request_revision'}), name='report-request-revision'),
    path('reports/list/', ReportViewSet.as_view({'get': 'list_reports'}), name='list-reports'),
    path('reports/view_patient_reports/<int:patient_id>/', ReportViewSet.as_view({'get': 'view_patient_reports'}), name='view-patient-reports'),
    path('reports/completed_patients_reports/', ReportViewSet.as_view({'get': 'completed_patients_reports'}), name='completed-patients-reports'),
    path('appointments/stats/', AppointmentViewSet.as_view({'get': 'stats'}), name='appointment-stats'),
    path('appointments/dashboard_appointments/', AppointmentViewSet.as_view({'get': 'dashboard_appointments'}), name='dashboard-appointments'),
    path('appointments/future_appointments/', AppointmentViewSet.as_view({'get': 'future_appointments'}), name='future-appointments'),
    path('appointments/<int:pk>/cancel/', AppointmentViewSet.as_view({'post': 'cancel'}), name='appointment-cancel'),
    path('appointments/<int:pk>/delete/', AppointmentViewSet.as_view({'delete': 'delete'}), name='appointment-delete'),
]