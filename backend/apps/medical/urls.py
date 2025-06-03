"""
URL Configuration for the medical app.
"""
from django.urls import path
from . import views

app_name = 'medical'

urlpatterns = [
    # Patient views
    path('patient/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/record/', views.patient_medical_record, name='patient_medical_record'),
    path('patient/documents/', views.patient_documents, name='patient_documents'),
    path('patient/feedback/', views.patient_provide_feedback, name='patient_feedback'),
    path('patient/doctor-search-modal/', views.doctor_search_modal, name='doctor_search_modal'),
    path('patient/doctor-search/', views.doctor_search, name='doctor_search'),
    path('patient/request-doctor/', views.request_doctor_assignment, name='request_doctor_assignment'),
    path('patient/document/<uuid:document_id>/modal/', views.document_detail_modal, name='document_detail_modal'),

    # Clinician views
    path('clinician/', views.clinician_dashboard, name='doctor_dashboard'),
    path('clinician/patient/<int:patient_id>/', views.clinician_patient_detail, name='clinician_patient_detail'),
    path('clinician/patient/<int:patient_id>/edit/', views.clinician_edit_patient_record,
         name='clinician_edit_patient_record'),
    path('clinician/patient/<int:patient_id>/review/', views.clinician_add_review, name='clinician_add_review'),
    path('clinician/patient/<int:patient_id>/upload/', views.upload_medical_document, name='clinician_upload_document'),
    path('document/<uuid:document_id>/view/', views.view_medical_document, name='view_medical_document'),
    path('document/<uuid:document_id>/review/', views.review_medical_document, name='review_medical_document'),
    path('document/<uuid:document_id>/api/data/', views.get_document_data, name='get_document_data'),
    path('document/<uuid:document_id>/api/update/', views.update_document_data, name='update_document_data'),
    path('ai-debug/', views.view_ai_debug, name='view_ai_debug'),
    path('get_subtypes/', views.get_cancer_subtypes, name='get_cancer_subtypes'),

    # Administrator views
    path('admin/', views.admin_medical_dashboard, name='admin_dashboard'),
    path('admin/patients/', views.admin_patient_list, name='admin_patient_list'),
    path('admin/clinicians/', views.admin_clinician_list, name='admin_clinician_list'),
    path('admin/patient/<int:patient_id>/', views.admin_patient_detail, name='admin_patient_detail'),
    path('admin/patient/<int:patient_id>/assign/', views.admin_assign_doctor, name='admin_assign_doctor'),
    path('admin/patient/<int:patient_id>/upload/', views.upload_medical_document, name='admin_upload_document'),
    path('admin/user/<int:user_id>/modal/', views.admin_user_modal, name='admin_user_modal'),
    path('admin/process-doctor-request/<uuid:request_id>/', views.process_doctor_request, name='process_doctor_request'),
    path('admin/cancer-types/', views.admin_cancer_types, name='admin_cancer_types'),
    path('admin/cancer-stages/', views.admin_cancer_stages, name='admin_cancer_stages'),
    path('admin/faqs/', views.admin_faqs, name='admin_faqs'),
    path('admin/faqs/<int:faq_id>/translations/', views.admin_faq_translations, name='admin_faq_translations'),
]