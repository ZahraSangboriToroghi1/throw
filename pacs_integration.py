
import os
import django
import logging
import uuid
from datetime import datetime
from pynetdicom import AE, sop_class
from pynetdicom.sop_class import PatientRootQueryRetrieveInformationModelFind, EncapsulatedPDFStorage, MRImageStorage
from pydicom.dataset import Dataset
from pydicom.uid import ExplicitVRLittleEndian
from django.conf import settings

# تنظیمات Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_system.settings')
django.setup()

# import مدل‌ها بعد از django.setup()
from medical_reports.models import PACS, Patient, Report, Image, UserActivity

logger = logging.getLogger('medical_reports')

class PACSIntegration:
    def __init__(self, pacs_id):
        self.pacs = PACS.objects.get(id=pacs_id)
        self.ae = AE(ae_title=self.pacs.ae_title_local)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind, ExplicitVRLittleEndian)
        self.ae.add_requested_context(EncapsulatedPDFStorage, ExplicitVRLittleEndian)
        self.ae.add_requested_context(MRImageStorage, ExplicitVRLittleEndian)

    def fetch_patient_data(self):
        """دریافت داده‌های بیمار با C-FIND"""
        assoc = None
        try:
            assoc = self.ae.associate(self.pacs.server_address, self.pacs.port, ae_title=self.pacs.ae_title_remote)
            if assoc.is_established:
                ds = Dataset()
                ds.QueryRetrieveLevel = 'PATIENT'
                ds.PatientID = '*'
                ds.PatientName = '*'
                ds.PatientBirthDate = ''

                responses = assoc.send_c_find(ds, PatientRootQueryRetrieveInformationModelFind)
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
                                    'hospital': self.pacs.hospital,
                                    'birth_date': birth_date,
                                    'gender': 'unknown',
                                    'phone': '',
                                    'modality': 'unknown',
                                    'status': 'pending'
                                }
                            )
                            if created:
                                logger.info(f"New patient created: {patient.national_id}")
                                # Create a system user for PACS operations if needed
                                system_user = User.objects.filter(username='system_pacs').first()
                                if not system_user:
                                    system_user = User.objects.create_user(
                                        username='system_pacs',
                                        email='system@pacs.local',
                                        phone='0000000000',
                                        role='supervisor'
                                    )
                                UserActivity.objects.create(
                                    user=system_user,
                                    action='create_patient_from_pacs',
                                    details=f'Patient {patient.national_id} created from PACS'
                                )
                        patient_data.append(patient_info)
                logger.info(f"Fetched {len(patient_data)} patients from PACS {self.pacs.server_address}:{self.pacs.port}")
                return patient_data
            else:
                logger.error(f"Failed to connect to PACS {self.pacs.server_address}:{self.pacs.port}")
                return []
        except Exception as e:
            logger.error(f"Error in C-FIND: {str(e)}")
            return []
        finally:
            # Ensure association is always released, even if an exception occurs
            if assoc and assoc.is_established:
                try:
                    assoc.release()
                except Exception as release_error:
                    logger.error(f"Error releasing PACS association: {str(release_error)}")

    def send_report_to_pacs(self, report_id):
        """ارسال گزارش به PACS با C-STORE"""
        assoc = None
        try:
            report = Report.objects.get(id=report_id)
            patient = report.patient
            assoc = self.ae.associate(self.pacs.server_address, self.pacs.port, ae_title=self.pacs.ae_title_remote)
            if assoc.is_established:
                ds = Dataset()
                ds.PatientName = f"{patient.first_name}^{patient.last_name}"
                ds.PatientID = patient.national_id
                ds.StudyInstanceUID = str(report.token)
                ds.SeriesInstanceUID = str(uuid.uuid4())
                ds.SOPInstanceUID = str(uuid.uuid4())
                ds.SOPClassUID = sop_class.EncapsulatedPDFStorage
                ds.StudyDate = datetime.now().strftime('%Y%m%d')
                ds.EncapsulatedDocument = report.content.encode('utf-8')

                status = assoc.send_c_store(ds)
                if status.Status == 0:
                    logger.info(f"Report {report_id} sent to PACS {self.pacs.server_address}:{self.pacs.port}")
                    # Get or create system user for PACS operations
                    system_user = User.objects.filter(username='system_pacs').first()
                    if not system_user:
                        system_user = User.objects.create_user(
                            username='system_pacs',
                            email='system@pacs.local',
                            phone='0000000000',
                            role='supervisor'
                        )
                    UserActivity.objects.create(
                        user=system_user,
                        action='send_report_to_pacs',
                        details=f'Report {report_id} sent to PACS'
                    )
                    return True
                else:
                    logger.error(f"Failed to send report {report_id} to PACS: Status {status.Status}")
                    return False
            else:
                logger.error(f"Failed to connect to PACS {self.pacs.server_address}:{self.pacs.port}")
                return False
        except Report.DoesNotExist:
            logger.error(f"Report with ID {report_id} does not exist")
            return False
        except Exception as e:
            logger.error(f"Error in C-STORE for report {report_id}: {str(e)}")
            return False
        finally:
            # Ensure association is always released, even if an exception occurs
            if assoc and assoc.is_established:
                try:
                    assoc.release()
                except Exception as release_error:
                    logger.error(f"Error releasing PACS association: {str(release_error)}")

    def send_image_to_pacs(self, image_id):
        """ارسال تصویر به PACS با C-STORE"""
        assoc = None
        try:
            image = Image.objects.get(id=image_id)
            patient = image.patient
            
            # Validate file exists and is accessible
            file_path = os.path.join(settings.MEDIA_ROOT, image.file.name)
            if not os.path.exists(file_path):
                logger.error(f"Image file not found: {file_path}")
                return False
            
            # Check file size to prevent sending corrupt or empty files
            if os.path.getsize(file_path) == 0:
                logger.error(f"Image file is empty: {file_path}")
                return False
            
            assoc = self.ae.associate(self.pacs.server_address, self.pacs.port, ae_title=self.pacs.ae_title_remote)
            if assoc.is_established:
                try:
                    from pydicom.filebase import DicomFile
                    from pydicom.errors import InvalidDicomError
                    
                    # Safely read DICOM file with proper error handling
                    with DicomFile(file_path, 'rb') as f:
                        ds = f.read()
                    
                    # Validate that we have a valid DICOM dataset
                    if not hasattr(ds, 'SOPClassUID'):
                        logger.error(f"Invalid DICOM file - missing SOPClassUID: {file_path}")
                        return False
                        
                except (InvalidDicomError, OSError, IOError) as dicom_error:
                    logger.error(f"Failed to read DICOM file {file_path}: {str(dicom_error)}")
                    return False
                except Exception as read_error:
                    logger.error(f"Unexpected error reading DICOM file {file_path}: {str(read_error)}")
                    return False
                
                # Update DICOM metadata
                ds.PatientName = f"{patient.first_name}^{patient.last_name}"
                ds.PatientID = patient.national_id
                ds.StudyInstanceUID = str(uuid.uuid4())
                ds.SeriesInstanceUID = str(uuid.uuid4())
                ds.SOPInstanceUID = str(uuid.uuid4())
                ds.StudyDate = datetime.now().strftime('%Y%m%d')
                ds.SOPClassUID = sop_class.MRImageStorage

                status = assoc.send_c_store(ds)
                if status.Status == 0:
                    logger.info(f"Image {image_id} sent to PACS {self.pacs.server_address}:{self.pacs.port}")
                    # Get or create system user for PACS operations  
                    system_user = User.objects.filter(username='system_pacs').first()
                    if not system_user:
                        system_user = User.objects.create_user(
                            username='system_pacs',
                            email='system@pacs.local',
                            phone='0000000000',
                            role='supervisor'
                        )
                    UserActivity.objects.create(
                        user=system_user,
                        action='send_image_to_pacs',
                        details=f'Image {image_id} sent to PACS'
                    )
                    return True
                else:
                    logger.error(f"Failed to send image {image_id} to PACS: Status {status.Status}")
                    return False
            else:
                logger.error(f"Failed to connect to PACS {self.pacs.server_address}:{self.pacs.port}")
                return False
        except Image.DoesNotExist:
            logger.error(f"Image with ID {image_id} does not exist")
            return False
        except Exception as e:
            logger.error(f"Error in C-STORE for image {image_id}: {str(e)}")
            return False
        finally:
            # Ensure association is always released, even if an exception occurs
            if assoc and assoc.is_established:
                try:
                    assoc.release()
                except Exception as release_error:
                    logger.error(f"Error releasing PACS association: {str(release_error)}")

    def sync_pacs_data(self):
        """همگام‌سازی خودکار: دریافت بیماران و ارسال گزارش‌ها و تصاویر"""
        # دریافت داده‌های بیماران
        patients_data = self.fetch_patient_data()
        logger.info(f"Synced {len(patients_data)} patients from PACS")

        # ارسال گزارش‌های جدید
        reports = Report.objects.filter(patient__hospital=self.pacs.hospital, is_deleted=False, signature=True)
        for report in reports:
            if self.send_report_to_pacs(report.id):
                logger.info(f"Report {report.id} sent to PACS")
            else:
                logger.warning(f"Failed to send report {report.id} to PACS")

        # ارسال تصاویر جدید
        images = Image.objects.filter(patient__hospital=self.pacs.hospital, report__is_deleted=False)
        for image in images:
            if self.send_image_to_pacs(image.id):
                logger.info(f"Image {image.id} sent to PACS")
            else:
                logger.warning(f"Failed to send image {image.id} to PACS")

if __name__ == "__main__":
    pacs_id = 1  # جایگزین با ID واقعی PACS
    integration = PACSIntegration(pacs_id)
    integration.sync_pacs_data()
