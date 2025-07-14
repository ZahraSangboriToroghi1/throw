from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from medical_reports.models import User, Hospital, Patient
from datetime import datetime
import json
import uuid

class DoctorTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.hospital = Hospital.objects.create(
            id=1, name="Test Hospital", address="123 Test St", phone="02112345678"
        )
        self.secretary = User.objects.create_user(
            username="secretary1", email="secretary1@example.com", phone="09123456789",
            role="secretary", hospital=self.hospital, password="sec123", department="General"
        )
        self.doctor = User.objects.create_user(
            username="Doctor", email="doctor@example.com", phone="09123456786",
            role="doctor", hospital=self.hospital, password="doc123Za", department="Radiology"
        )
        self.doctor_id = self.doctor.id

    def test_create_patient(self):
        self.client.force_authenticate(user=self.doctor)
        url = "/api/patients/"
        timestamp = int(datetime.now().timestamp()) % 10000
        data = {
            "first_name": "رضا",
            "last_name": "رضایی",
            "national_id": f"222{timestamp}",
            "birth_date": "1992-07-20",
            "age": 32,
            "gender": "male",
            "phone": "09187654321",
            "modality": "Sonography",
            "status": "waiting",
            "hospital": self.hospital.id
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"خطای ثبت بیمار: {response.content}")
        print("ثبت بیمار موفق:", response.json())
        return response.json()["id"]

    def test_get_patients(self):
        self.client.force_authenticate(user=self.doctor)
        url = "/api/patients/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"خطای گرفتن لیست بیمارها: {response.content}")
        print("لیست بیمارها:", json.dumps(response.json(), indent=2, ensure_ascii=False))

    def test_get_stats(self):
        self.client.force_authenticate(user=self.doctor)
        url = "/api/patients/stats/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"خطای گرفتن آمار: {response.content}")
        print("آمار بیمارها:", response.json())

    def test_get_pending_patients(self):
        self.client.force_authenticate(user=self.doctor)
        url = "/api/patients/pending_patients/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"خطای گرفتن بیمارهای در انتظار: {response.content}")
        print("بیمارهای در انتظار:", json.dumps(response.json(), indent=2, ensure_ascii=False))

    def test_get_completed_patients(self):
        self.client.force_authenticate(user=self.doctor)
        url = "/api/patients/completed_patients/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"خطای گرفتن بیمارهای تکمیل‌شده: {response.content}")
        print("بیمارهای تکمیل‌شده:", json.dumps(response.json(), indent=2, ensure_ascii=False))

    def test_create_report(self):
        self.client.force_authenticate(user=self.doctor)
        patient_id = self.test_create_patient()
        url = "/api/reports/"
        data = {
            "patient": patient_id,
            "doctor": self.doctor_id,
            "content": "گزارش پزشکی برای بیمار",
            "token": str(uuid.uuid4())
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"خطای ثبت گزارش: {response.content}")
        print("ثبت گزارش موفق:", response.json())
        return response.json()["id"]

    def test_sign_report(self):
        self.client.force_authenticate(user=self.doctor)
        report_id = self.test_create_report()
        url = f"/api/reports/{report_id}/sign/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"خطای امضای گزارش: {response.content}")
        print("امضای گزارش موفق:", response.json())

    def test_send_email(self):
        self.client.force_authenticate(user=self.doctor)
        report_id = self.test_create_report()
        url = f"/api/reports/{report_id}/send_email/"
        data = {"email": "patient@example.com"}
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"خطای ارسال ایمیل: {response.content}")
        print("ارسال ایمیل:", response.status_code, response.json())