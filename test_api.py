import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def get_token(username, password):
    url = f"{BASE_URL}/api/auth/login/"
    payload = {
        "username": username,
        "password": password
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    if response.status_code == 200:
        return response.json().get("access")
    else:
        print(f"Failed to get token: {response.status_code} - {response.text}")
        return None

def test_welcome_card(token):
    url = f"{BASE_URL}/api/welcome-card/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    print(f"Welcome Card Response: {response.status_code} - {response.json()}")

def test_create_patient(token):
    url = f"{BASE_URL}/api/patients/"
    payload = {
        "first_name": "Ali",
        "last_name": "Rezaei",
        "national_id": "1234567890",
        "birth_date": "1990-01-01",
        "age": 35,
        "gender": "male",
        "phone": "09123456790",
        "modality": "CT Scan",
        "status": "pending",
        "hospital": 21,
        "doctor_id": 6
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    print(f"Create Patient Response: {response.status_code} - {response.json()}")

def test_create_appointment(token):
    url = f"{BASE_URL}/api/appointments/"
    payload = {
        "patient_id": 32,
        "doctor_id": 6,
        "date": "2025-05-20",
        "time": "10:00:00",
        "status": "scheduled"
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    print(f"Create Appointment Response: {response.status_code} - {response.json()}")

def test_get_doctors(token):
    url = f"{BASE_URL}/api/users/doctors/?hospital_id=21"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    print(f"Get Doctors Response: {response.status_code} - {response.json()}")

if __name__ == "__main__":
    token = get_token("secretary1", "sec123")
    if token:
        test_welcome_card(token)
        test_create_patient(token)
        test_create_appointment(token)
        test_get_doctors(token)