from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from medical_reports.models import User, Patient, Appointment, Hospital
from django.urls import reverse
from django.utils import timezone
import json

class PatientRegistrationAndViewTest(APITestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(
            id=1,
            name="Test Hospital",
            address="123 Test St",
            phone="02112345678"
        )

        self.secretary = User.objects.create_user(
            username="secretary1",
            preferred_name="Secretary One",
            email="secretary1@example.com",
            phone="09123456789",
            role="secretary",
            hospital=self.hospital,
            password="sec123",
            is_active=True
        )

        self.doctor = User.objects.create_user(
            username="Doctor",
            preferred_name="09123456786",
            email="doctor@example.com",
            phone="09123456786",
            role="doctor",
            hospital=self.hospital,
            password="doc123Za",
            is_active=True
        )

        self.client = APIClient()

    def test_register_patient_and_view_by_doctor(self):
        response = self.client.post(
            '/api/auth/login/',
            data=json.dumps({
                "username": "secretary1",
                "password": "sec123"
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        secretary_token = response.data['access']

        patient_data = {
            "first_name": "Ali",
            "last_name": "Rezaei",
            "national_id": "1234567894",
            "birth_date": "1990-01-01",
            "age": 35,
            "gender": "male",
            "phone": "09123456790",
            "modality": "CT Scan",
            "status": "pending",
            "hospital": self.hospital.id,
            "doctor_id": self.doctor.id
        }
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {secretary_token}')
        response = self.client.post(
            '/api/patients/',
            data=json.dumps(patient_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        patient_id = response.data['id']

        response = self.client.post(
            '/api/auth/login/',
            data=json.dumps({
                "username": "Doctor",
                "password": "doc123Za"
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doctor_token = response.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')
        response = self.client.get('/api/patients/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patients = response.data
        self.assertTrue(any(p['national_id'] == '1234567894' for p in patients))

        response = self.client.get('/api/appointments/dashboard_appointments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        appointments = response.data['today']
        self.assertTrue(any(a['patient'] == patient_id for a in appointments))