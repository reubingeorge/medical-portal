"""
Admin configuration for the medical app.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    CancerType, PatientRecord, MedicalDocument,
    ClinicianReview, PatientFeedback, FAQ, FAQTranslation
)


@admin.register(CancerType)
class CancerTypeAdmin(admin.ModelAdmin):
    """
    Admin interface for CancerType model.
    """
    list_display = ('name', 'get_patients_count')
    search_fields = ('name', 'description')

    def get_patients_count(self, obj):
        """Get number of patients with this cancer type."""
        return obj.patients.count()

    get_patients_count.short_description = _('Patients')


# CancerStageAdmin removed since we're no longer using the CancerStage model


class ClinicianReviewInline(admin.TabularInline):
    """
    Inline admin for ClinicianReview model.
    """
    model = ClinicianReview
    extra = 0
    readonly_fields = ('clinician', 'review_date')
    fields = ('clinician', 'review_date', 'notes')
    can_delete = False


@admin.register(PatientRecord)
class PatientRecordAdmin(admin.ModelAdmin):
    """
    Admin interface for PatientRecord model.
    """
    list_display = (
        'patient', 'cancer_type', 'cancer_stage_text',
        'diagnosis_date', 'vital_status', 'updated_at'
    )
    list_filter = ('vital_status', 'cancer_type', 'diagnosis_date')
    search_fields = ('patient__first_name', 'patient__last_name', 'patient__email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('patient', 'vital_status')
        }),
        (_('Diagnosis'), {
            'fields': ('cancer_type', 'cancer_stage_text', 'diagnosis_date', 'stage_grouping')
        }),
        (_('Treatment'), {
            'fields': ('recommended_treatment',)
        }),
        (_('Additional Information'), {
            'fields': ('notes',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [ClinicianReviewInline]


@admin.register(MedicalDocument)
class MedicalDocumentAdmin(admin.ModelAdmin):
    """
    Admin interface for MedicalDocument model.
    """
    list_display = (
        'title', 'document_type', 'patient',
        'cancer_type', 'language', 'uploaded_by', 'uploaded_at'
    )
    list_filter = ('document_type', 'cancer_type', 'language', 'uploaded_at')
    search_fields = (
        'title', 'description', 'patient__first_name',
        'patient__last_name', 'patient__email'
    )
    readonly_fields = ('uploaded_at', 'uploaded_by')
    fieldsets = (
        (None, {
            'fields': ('patient', 'title', 'document_type')
        }),
        (_('Document Details'), {
            'fields': ('cancer_type', 'description', 'language', 'file')
        }),
        (_('Metadata'), {
            'fields': ('uploaded_by', 'uploaded_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ClinicianReview)
class ClinicianReviewAdmin(admin.ModelAdmin):
    """
    Admin interface for ClinicianReview model.
    """
    list_display = ('patient_name', 'clinician', 'review_date')
    list_filter = ('review_date', 'clinician')
    search_fields = (
        'patient_record__patient__first_name',
        'patient_record__patient__last_name',
        'clinician__first_name',
        'clinician__last_name',
        'notes'
    )
    readonly_fields = ('review_date',)

    def patient_name(self, obj):
        """Get patient name."""
        return obj.patient_record.patient.get_full_name()

    patient_name.short_description = _('Patient')


@admin.register(PatientFeedback)
class PatientFeedbackAdmin(admin.ModelAdmin):
    """
    Admin interface for PatientFeedback model.
    """
    list_display = ('patient', 'rating', 'submitted_at')
    list_filter = ('rating', 'submitted_at')
    search_fields = ('patient__first_name', 'patient__last_name', 'comments')
    readonly_fields = ('submitted_at',)


class FAQTranslationInline(admin.TabularInline):
    """
    Inline admin for FAQTranslation model.
    """
    model = FAQTranslation
    extra = 1
    fieldsets = (
        (None, {
            'fields': ('language', 'question', 'answer')
        }),
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    """
    Admin interface for FAQ model.
    """
    list_display = ('question_key', 'category', 'get_translations_count')
    list_filter = ('category',)
    search_fields = ('question_key', 'category')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [FAQTranslationInline]

    def get_translations_count(self, obj):
        """Get number of translations for this FAQ."""
        return obj.translations.count()

    get_translations_count.short_description = _('Translations')


@admin.register(FAQTranslation)
class FAQTranslationAdmin(admin.ModelAdmin):
    """
    Admin interface for FAQTranslation model.
    """
    list_display = ('faq', 'language', 'question_preview')
    list_filter = ('language', 'faq__category')
    search_fields = ('question', 'answer', 'faq__question_key')

    def question_preview(self, obj):
        """Get a preview of the question."""
        if len(obj.question) > 50:
            return f"{obj.question[:50]}..."
        return obj.question

    question_preview.short_description = _('Question')