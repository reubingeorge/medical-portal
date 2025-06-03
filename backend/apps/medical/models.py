"""
Models for the medical app.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
import json


class CancerType(models.Model):
    """
    Model for cancer types.
    Hierarchical structure with parent-child relationships:
    - Parent cancer types represent organ-based classifications
    - Child cancer types represent specific subtypes
    """
    name = models.CharField(
        max_length=100,
        verbose_name=_('Cancer type name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtypes',
        verbose_name=_('Parent cancer type')
    )
    is_organ = models.BooleanField(
        default=False,
        verbose_name=_('Is organ-level type'),
        help_text=_('If checked, this cancer type represents an organ-level classification')
    )

    class Meta:
        verbose_name = _('Cancer type')
        verbose_name_plural = _('Cancer types')
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'parent'],
                name='unique_name_parent'
            )
        ]

    def __str__(self):
        if self.parent:
            return f"{self.name} ({self.parent.name})"
        return self.name
        
    @property
    def full_name(self):
        """
        Returns the full name of the cancer type, including parent name if it's a subtype.
        """
        if self.parent:
            return f"{self.parent.name} - {self.name}"
        return self.name

    @property
    def get_patient_count(self):
        """
        Returns the count of patients with this cancer type.
        This is a fallback method in case the annotated patient_count is not available.
        """
        # Direct patient count
        direct_count = self.patients.count()

        # If this is an organ type, also include patients from subtypes
        if self.is_organ:
            # Get all subtypes
            subtypes = self.subtypes.all()
            # Count patients in all subtypes
            subtype_count = sum(subtype.patients.count() for subtype in subtypes)
            return direct_count + subtype_count

        return direct_count


# CancerStage model removed in favor of using a simple CharField in PatientRecord


class PatientRecord(models.Model):
    """
    Model for patient medical records.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    patient = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medical_record',
        verbose_name=_('Patient')
    )
    cancer_type = models.ForeignKey(
        CancerType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patients',
        verbose_name=_('Cancer type'),
        limit_choices_to={'is_organ': True}  # Only allow organ-level cancer types
    )
    # The cancer_stage field has been removed in favor of cancer_stage_text
    cancer_stage_text = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Cancer stage'),
        help_text=_('Stage of cancer (e.g., Stage I, Stage II, etc.)')
    )
    diagnosis_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Diagnosis date')
    )
    stage_grouping = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Stage grouping')
    )
    recommended_treatment = models.TextField(
        blank=True,
        verbose_name=_('Recommended treatment')
    )
    vital_status = models.BooleanField(
        default=True,
        verbose_name=_('Active patient')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Medical notes')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        verbose_name = _('Patient record')
        verbose_name_plural = _('Patient records')

    def __str__(self):
        return f"Medical record for {self.patient.get_full_name()}"


class DoctorAssignmentRequest(models.Model):
    """
    Model for patients to request assignment to a specific doctor.
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_requests',
        verbose_name=_('Patient')
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_requests',
        verbose_name=_('Requested Doctor')
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Requested at')
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Processed at')
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_requests',
        verbose_name=_('Processed by')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    class Meta:
        verbose_name = _('Doctor assignment request')
        verbose_name_plural = _('Doctor assignment requests')
        ordering = ['-requested_at']
        
    def __str__(self):
        return f"Request from {self.patient.get_full_name()} for Dr. {self.doctor.last_name}"
    
    def approve(self, admin_user):
        """
        Approve the request and assign the doctor to the patient.
        """
        if self.status != 'pending':
            return False
            
        self.status = 'approved'
        self.processed_at = timezone.now()
        self.processed_by = admin_user
        
        # Update the patient's assigned doctor
        self.patient.assigned_doctor = self.doctor
        self.patient.save(update_fields=['assigned_doctor'])
        
        self.save()
        return True
    
    def reject(self, admin_user, notes=None):
        """
        Reject the request.
        """
        if self.status != 'pending':
            return False
            
        self.status = 'rejected'
        self.processed_at = timezone.now()
        self.processed_by = admin_user
        
        if notes:
            self.notes = notes
            
        self.save()
        return True


class MedicalDocument(models.Model):
    """
    Model for medical documents.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medical_documents',
        verbose_name=_('Patient')
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_('Document title')
    )
    document_type = models.CharField(
        max_length=100,
        verbose_name=_('Document type')
    )
    cancer_type = models.ForeignKey(
        CancerType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name=_('Cancer type'),
        limit_choices_to={'is_organ': True}  # Only allow organ-level cancer types
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    patient_notes = models.TextField(
        blank=True,
        verbose_name=_('Notes for patient'),
        help_text=_('Additional notes that will be visible to the patient')
    )
    file = models.FileField(
        upload_to='medical_documents/%Y/%m/%d/',
        verbose_name=_('File')
    )
    file_hash = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_('File hash')
    )
    recommended_treatment = models.TextField(
        blank=True,
        verbose_name=_('Recommended treatment'),
        help_text=_('Treatment recommendations extracted from document')
    )
    language = models.ForeignKey(
        'accounts.Language',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_documents',
        verbose_name=_('Language')
    )
    # AI analysis fields
    extracted_text = models.TextField(
        blank=True,
        verbose_name=_('Extracted text'),
        help_text=_('Text extracted from the document using OCR')
    )
    is_pathology_report = models.BooleanField(
        default=False,
        verbose_name=_('Is pathology report'),
        help_text=_('Indicates if the document was detected as a pathology report')
    )
    ai_analysis_json = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('AI analysis results'),
        help_text=_('Results of AI analysis of the document')
    )
    analysis_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Analysis timestamp'),
        help_text=_('When the document was last analyzed by AI')
    )
    # Upload info
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
        verbose_name=_('Uploaded by')
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Uploaded at')
    )

    class Meta:
        verbose_name = _('Medical document')
        verbose_name_plural = _('Medical documents')
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} - {self.patient.get_full_name()}"
        
    def get_ai_analysis(self):
        """
        Returns the AI analysis results in a structured format.
        """
        if not self.ai_analysis_json:
            return {
                'cancer_type': 'Not analyzed',
                'figo_stage': 'Not analyzed',
                'final_pathologic_stage': 'Not analyzed',
                'recommended_treatment': 'Not analyzed'
            }

        try:
            # If stored as a string, convert to dict
            result = None
            if isinstance(self.ai_analysis_json, str):
                result = json.loads(self.ai_analysis_json)
            else:
                result = self.ai_analysis_json

            # Populate the recommended_treatment field from AI analysis if available
            if result and 'recommended_treatment' in result and result['recommended_treatment'] != "Not specified":
                self.recommended_treatment = result['recommended_treatment']
                try:
                    # Save the field without triggering a full save event
                    from django.db import connection
                    cursor = connection.cursor()
                    cursor.execute(
                        "UPDATE medical_medicaldocument SET recommended_treatment = %s WHERE id = %s",
                        [self.recommended_treatment, str(self.id)]
                    )
                except Exception as e:
                    print(f"Error updating recommended_treatment: {e}")

            return result
        except (json.JSONDecodeError, TypeError):
            return {
                'cancer_type': 'Error parsing results',
                'figo_stage': 'Error parsing results',
                'final_pathologic_stage': 'Error parsing results',
                'recommended_treatment': 'Error parsing results'
            }
            
    def update_patient_record(self):
        """
        Updates the patient's medical record based on AI analysis results.

        This method analyzes the document's AI results and updates the patient's medical
        record with cancer type, cancer stage, recommended treatment, and other relevant
        information. It only updates existing patient records and will not create new ones.

        Returns:
            bool: True if record was updated, False otherwise

        Note:
            This method will NOT create a patient record automatically anymore.
            It will only update an existing record if it already exists.
        """
        # Early exit conditions
        if not self.is_pathology_report or not self.ai_analysis_json:
            return False

        try:
            # Get analysis results
            analysis = self.get_ai_analysis()

            # Try to get an existing patient record (don't create a new one)
            try:
                patient_record = PatientRecord.objects.get(patient=self.patient)
            except PatientRecord.DoesNotExist:
                # Don't create a new record - will be done during document review
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"No patient record exists for patient {self.patient.id}, skipping automatic update")
                return False

            # Update fields based on analysis only if we have an existing record
            fields_updated = False

            # Process each field individually with proper error handling
            fields_updated = self._update_cancer_type(patient_record, analysis) or fields_updated
            fields_updated = self._update_cancer_stage(patient_record, analysis) or fields_updated
            fields_updated = self._update_recommended_treatment(patient_record, analysis) or fields_updated
            fields_updated = self._update_patient_notes(patient_record) or fields_updated

            # Save the record if updated
            if fields_updated:
                patient_record.save()
                return True

            return False

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating patient record: {e}")
            return False

    def _update_cancer_type(self, patient_record, analysis):
        """
        Update the cancer type in the patient record based on AI analysis.

        Args:
            patient_record: PatientRecord instance to update
            analysis: Dictionary containing AI analysis results

        Returns:
            bool: True if the field was updated, False otherwise
        """
        try:
            # Process cancer type if available and not "Not specified"
            cancer_type_name = analysis.get('cancer_type')
            if not cancer_type_name or cancer_type_name == "Not specified":
                return False

            # Try exact match first
            cancer_type = CancerType.objects.filter(
                name__iexact=cancer_type_name,
                is_organ=True
            ).first()

            if cancer_type:
                patient_record.cancer_type = cancer_type
                return True

            return False
        except Exception:
            return False

    def _update_cancer_stage(self, patient_record, analysis):
        """
        Update the cancer stage in the patient record based on AI analysis.

        Args:
            patient_record: PatientRecord instance to update
            analysis: Dictionary containing AI analysis results

        Returns:
            bool: True if the field was updated, False otherwise
        """
        try:
            # Process cancer stage if available and not "Not specified"
            stage_text = analysis.get('figo_stage')
            if not stage_text or stage_text == "Not specified":
                stage_text = analysis.get('final_pathologic_stage')

            if stage_text and stage_text != "Not specified":
                # Set the stage text directly
                patient_record.cancer_stage_text = stage_text[:50]  # Limit to model's max length
                return True

            return False
        except Exception:
            return False

    def _update_recommended_treatment(self, patient_record, analysis):
        """
        Update the recommended treatment in the patient record based on document or AI analysis.

        Args:
            patient_record: PatientRecord instance to update
            analysis: Dictionary containing AI analysis results

        Returns:
            bool: True if the field was updated, False otherwise
        """
        try:
            # Process recommended treatment - first check the document field, then fallback to AI analysis
            if self.recommended_treatment:
                patient_record.recommended_treatment = self.recommended_treatment
                return True
            else:
                # Fallback to AI analysis if document field is empty
                recommended_treatment = analysis.get('recommended_treatment')
                if recommended_treatment and recommended_treatment != "Not specified":
                    patient_record.recommended_treatment = recommended_treatment
                    return True

            return False
        except Exception:
            return False

    def _update_patient_notes(self, patient_record):
        """
        Update the patient notes in the patient record based on document notes.

        Args:
            patient_record: PatientRecord instance to update

        Returns:
            bool: True if the field was updated, False otherwise
        """
        try:
            # If this document has patient notes, use them as medical notes for the patient record
            if not self.patient_notes or not self.patient_notes.strip():
                return False

            # Add document notes to patient record medical notes (append if notes already exist)
            if patient_record.notes:
                patient_record.notes += f"\n\n--- Notes from document uploaded on {self.uploaded_at.strftime('%Y-%m-%d')} ---\n{self.patient_notes}"
            else:
                patient_record.notes = self.patient_notes

            return True
        except Exception:
            return False


class ClinicianReview(models.Model):
    """
    Model for clinician reviews of patient records.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    patient_record = models.ForeignKey(
        PatientRecord,
        on_delete=models.CASCADE,
        related_name='clinician_reviews',
        verbose_name=_('Patient record')
    )
    clinician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Clinician')
    )
    review_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Review date')
    )
    notes = models.TextField(
        verbose_name=_('Review notes')
    )

    class Meta:
        verbose_name = _('Clinician review')
        verbose_name_plural = _('Clinician reviews')
        ordering = ['-review_date']

    def __str__(self):
        return f"Review by {self.clinician.get_full_name()} for {self.patient_record.patient.get_full_name()}"


class PatientFeedback(models.Model):
    """
    Model for patient feedback.
    """
    RATING_CHOICES = [
        (1, _('Poor')),
        (2, _('Fair')),
        (3, _('Good')),
        (4, _('Very good')),
        (5, _('Excellent')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedback',
        verbose_name=_('Patient')
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        verbose_name=_('Rating')
    )
    comments = models.TextField(
        blank=True,
        verbose_name=_('Comments')
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Submitted at')
    )

    class Meta:
        verbose_name = _('Patient feedback')
        verbose_name_plural = _('Patient feedback')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Feedback from {self.patient.get_full_name()} - {self.get_rating_display()}"


class FAQ(models.Model):
    """
    Model for frequently asked questions.
    """
    question_key = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Question key')
    )
    category = models.CharField(
        max_length=100,
        verbose_name=_('Category')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        verbose_name = _('FAQ')
        verbose_name_plural = _('FAQs')
        ordering = ['category', 'question_key']

    def __str__(self):
        return self.question_key


class FAQTranslation(models.Model):
    """
    Model for FAQ translations.
    """
    faq = models.ForeignKey(
        FAQ,
        on_delete=models.CASCADE,
        related_name='translations',
        verbose_name=_('FAQ')
    )
    language = models.ForeignKey(
        'accounts.Language',
        on_delete=models.CASCADE,
        related_name='faq_translations',
        verbose_name=_('Language')
    )
    question = models.TextField(
        verbose_name=_('Question')
    )
    answer = models.TextField(
        verbose_name=_('Answer')
    )

    class Meta:
        verbose_name = _('FAQ translation')
        verbose_name_plural = _('FAQ translations')
        unique_together = ('faq', 'language')

    def __str__(self):
        return f"{self.faq.question_key} - {self.language.code}"