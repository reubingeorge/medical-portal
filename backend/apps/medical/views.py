"""
Views for the medical app.

This module contains all views for the medical application, including patient, clinician,
and administrator interfaces for managing medical records, documents, and other medical data.
"""
import logging
import os
import uuid
import json
import datetime
from typing import Dict, Any, Optional, List, Union

# Django imports
from django.db.models import Q, Count, Sum, F, Value, IntegerField, Case, When
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.urls import reverse
from django.template.defaultfilters import pprint
from django.db import connection

# Local app imports
from apps.accounts.decorators import role_required
from apps.accounts.models import User
from .models import (
    PatientRecord, MedicalDocument, ClinicianReview,
    PatientFeedback, CancerType, FAQ, FAQTranslation,
    DoctorAssignmentRequest
)
from .forms import (
    PatientRecordForm, MedicalDocumentForm, MedicalDocumentReviewForm, ClinicianReviewForm,
    PatientFeedbackForm, CancerTypeForm, FAQForm, FAQTranslationForm
)

logger = logging.getLogger(__name__)


# Patient Dashboard Views
@login_required
@role_required(['patient'])
def patient_dashboard(request):
    """
    Patient dashboard view.

    Displays the patient's medical record, recent documents, FAQs, and doctor assignment status.
    The view handles schema changes gracefully by checking for field existence before querying.

    Args:
        request: HttpRequest object containing metadata about the request

    Returns:
        HttpResponse object with the rendered template
    """
    # Get patient record
    try:
        medical_record = PatientRecord.objects.get(patient=request.user)
    except PatientRecord.DoesNotExist:
        medical_record = None

    # Get recent documents with safe field selection
    from .utils import get_queryset_with_safe_fields, check_column_exists

    # Define the fields we know existed in the original schema (required)
    required_fields = [
        'id', 'patient', 'title', 'document_type', 'cancer_type', 'description',
        'patient_notes', 'file', 'file_hash', 'language', 'uploaded_by', 'uploaded_at'
    ]

    # Define the fields that were added later (optional)
    optional_fields = [
        'extracted_text', 'is_pathology_report', 'ai_analysis_json', 'analysis_timestamp'
    ]

    # Get documents with only fields that exist in the database
    document_queryset = MedicalDocument.objects.filter(patient=request.user).order_by('-uploaded_at')[:5]
    documents = get_queryset_with_safe_fields(
        document_queryset,
        'medical_medicaldocument',
        required_fields,
        optional_fields
    )

    # Check for pending doctor assignment requests
    pending_doctor_request = None
    if not request.user.assigned_doctor:
        pending_doctor_request = DoctorAssignmentRequest.objects.filter(
            patient=request.user,
            status='pending'
        ).select_related('doctor').first()

    # Get FAQs in patient's preferred language
    faqs = []
    if request.user.language:
        faq_translations = FAQTranslation.objects.filter(
            language=request.user.language
        ).select_related('faq').order_by('faq__category', 'faq__question_key')

        faqs = faq_translations

    context = {
        'medical_record': medical_record,
        'documents': documents,
        'faqs': faqs,
        'pending_doctor_request': pending_doctor_request,
    }

    return render(request, 'medical/patient/dashboard.html', context)


@login_required
@role_required(['patient'])
def patient_medical_record(request):
    """
    View for patient to see their medical record.
    """
    try:
        medical_record = PatientRecord.objects.get(patient=request.user)
    except PatientRecord.DoesNotExist:
        medical_record = None

    context = {
        'medical_record': medical_record,
    }

    return render(request, 'medical/patient/medical_record.html', context)


@login_required
@role_required(['patient'])
def patient_documents(request):
    """
    View for patient to see their medical documents.

    Displays all medical documents associated with the patient, handling potential schema
    changes gracefully by checking for field existence before querying.

    Args:
        request: HttpRequest object containing metadata about the request

    Returns:
        HttpResponse object with the rendered template
    """
    # Get documents with safe field selection using the utility function
    from .utils import get_queryset_with_safe_fields

    # Define the fields we know existed in the original schema (required)
    required_fields = [
        'id', 'patient', 'title', 'document_type', 'cancer_type', 'description',
        'patient_notes', 'file', 'file_hash', 'language', 'uploaded_by', 'uploaded_at'
    ]

    # Define the fields that were added later (optional)
    optional_fields = [
        'extracted_text', 'is_pathology_report', 'ai_analysis_json', 'analysis_timestamp'
    ]

    # Get all documents with only fields that exist in the database
    document_queryset = MedicalDocument.objects.filter(patient=request.user).order_by('-uploaded_at')
    documents = get_queryset_with_safe_fields(
        document_queryset,
        'medical_medicaldocument',
        required_fields,
        optional_fields
    )

    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        documents = documents.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(document_type__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(documents, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }

    if request.htmx:
        return render(request, 'medical/patient/partials/document_list.html', context)

    return render(request, 'medical/patient/documents.html', context)


@login_required
@role_required(['patient'])
def patient_provide_feedback(request):
    """
    View for patient to provide feedback.
    """
    # Check if the user has already submitted feedback
    existing_feedback = PatientFeedback.objects.filter(patient=request.user).order_by('-submitted_at').first()

    if request.method == 'POST':
        form = PatientFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.patient = request.user
            feedback.save()

            messages.success(request, _('Thank you for your feedback!'))

            if request.htmx:
                return HttpResponse(
                    _("Thank you for your feedback!"),
                    headers={"HX-Trigger": "feedbackSubmitted"}
                )
            return redirect('medical:patient_dashboard')
    else:
        # Pre-fill form with existing feedback if available
        form = PatientFeedbackForm(instance=existing_feedback)

    context = {
        'form': form,
        'existing_feedback': existing_feedback,
    }

    if request.htmx:
        return render(request, 'medical/patient/partials/feedback_form.html', context)

    return render(request, 'medical/patient/feedback.html', context)


@login_required
@role_required(['patient'])
def doctor_search_modal(request):
    """
    View for showing the doctor search modal.
    """
    # Check if patient already has a pending request
    pending_request = DoctorAssignmentRequest.objects.filter(
        patient=request.user,
        status='pending'
    ).first()
    
    if pending_request:
        # Return a message indicating a request is already pending
        context = {
            'request_exists': True,
            'pending_request': pending_request
        }
        return render(request, 'medical/patient/partials/doctor_request_modal.html', context)
    
    # Get initial doctor list (first page)
    doctors = User.objects.filter(role__name='clinician').select_related('role')
    
    # Initialize paginator with default limit of 5 items per page
    paginator = Paginator(doctors, 5)
    page_obj = paginator.get_page(1)
    
    context = {
        'doctors': page_obj,
        'page_obj': page_obj,
    }
    
    return render(request, 'medical/patient/partials/doctor_request_modal.html', context)


@login_required
@role_required(['patient'])
def doctor_search(request):
    """
    View for searching doctors with pagination.
    """
    # Get search query
    search_query = request.GET.get('q', '')
    
    # Base query for clinicians
    doctors = User.objects.filter(role__name='clinician').select_related('role')
    
    # Apply search filters if a query is provided
    if search_query:
        doctors = doctors.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(specialty_name__icontains=search_query) |
            Q(email__icontains=search_query)
        ).order_by('first_name', 'last_name')
    else:
        # If no search query, order by most recently added
        doctors = doctors.order_by('-date_joined')
    
    # Paginate results (default: 5 per page)
    paginator = Paginator(doctors, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'doctors': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    # Add a small delay to simulate server processing (makes the indicator visible)
    if search_query:
        import time
        time.sleep(0.2)  # 200ms delay
    
    return render(request, 'medical/patient/partials/doctor_list.html', context)


@login_required
@role_required(['patient'])
def request_doctor_assignment(request):
    """
    View for submitting a doctor assignment request.
    """
    if request.method == 'POST':
        # Check if user already has a doctor assigned
        if request.user.assigned_doctor:
            messages.error(request, _("You already have a doctor assigned."))
            return redirect('medical:patient_dashboard')
            
        # Check if the user has any pending request (for any doctor)
        any_pending_request = DoctorAssignmentRequest.objects.filter(
            patient=request.user,
            status='pending'
        ).first()
        
        if any_pending_request:
            # Return a message indicating a request is already pending
            context = {
                'request_exists': True,
                'pending_request': any_pending_request
            }
            return render(request, 'medical/patient/partials/doctor_list.html', context)
        
        # Get the doctor ID from the POST data
        doctor_id = request.POST.get('doctor_id')
        
        if doctor_id:
            try:
                # Get the requested doctor
                doctor = User.objects.get(id=doctor_id, role__name='clinician')
                
                # Create a new request
                DoctorAssignmentRequest.objects.create(
                    patient=request.user,
                    doctor=doctor,
                    status='pending'
                )
                
                # Return the doctor list with a success flag
                context = {
                    'request_sent': True,
                    'doctor': doctor
                }
                
                return render(request, 'medical/patient/partials/doctor_list.html', context)
                
            except User.DoesNotExist:
                pass
    
    # If there was an error or not a POST request, return to the search view
    return redirect('medical:doctor_search')


@login_required
@role_required(['patient'])
def document_detail_modal(request, document_id):
    """
    View for displaying a medical document in a modal.
    """
    try:
        # Use select_related to fetch the uploaded_by user and patient in one query
        document = get_object_or_404(
            MedicalDocument.objects.select_related('uploaded_by', 'patient'),
            id=document_id
        )

        # Security check - make sure the patient can view this document
        if document.patient_id != request.user.id:
            return HttpResponse(_('Unauthorized'), status=403)

        context = {
            'document': document,
        }

        return render(request, 'medical/patient/partials/document_detail_modal.html', context)
    except Exception as e:
        logger.error(f"Error loading document modal for document {document_id}: {str(e)}")
        return HttpResponse(_('Error loading document'), status=500)


# Clinician Dashboard Views
@login_required
@role_required(['clinician'])
def clinician_dashboard(request):
    """
    Clinician dashboard view.
    """
    # Get assigned patients
    patients = User.objects.filter(assigned_doctor=request.user).select_related('role', 'language')
    # Removed specialty field select_related to prevent DB error

    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
            # Removed cancer_type reference to prevent DB issues
        )

    # Pagination
    paginator = Paginator(patients, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }

    if request.htmx:
        return render(request, 'medical/clinician/partials/patient_list.html', context)

    return render(request, 'medical/clinician/dashboard.html', context)


@login_required
@role_required(['clinician'])
def clinician_patient_detail(request, patient_id):
    """
    View for clinician to see patient details.
    """
    # Use select_related to efficiently load the language object in a single query
    patient = get_object_or_404(
        User.objects.select_related('language'),
        id=patient_id,
        assigned_doctor=request.user
    )

    # Get patient record if exists
    medical_record = None
    try:
        medical_record = PatientRecord.objects.get(patient=patient)
    except PatientRecord.DoesNotExist:
        # No record exists yet
        pass

    # Try to get only the fields that are guaranteed to exist to avoid DB errors
    try:
        # Check if new AI fields exist in the database
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='medical_medicaldocument' AND column_name='extracted_text'")
        ai_fields_exist = bool(cursor.fetchone())
        
        # Only request fields that exist
        if ai_fields_exist:
            documents = MedicalDocument.objects.filter(patient=patient).order_by('-uploaded_at')
        else:
            # Only select fields that existed before the AI fields were added
            documents = MedicalDocument.objects.filter(patient=patient).only(
                'id', 'patient', 'title', 'document_type', 'cancer_type', 'description', 
                'patient_notes', 'file', 'file_hash', 'language', 'uploaded_by', 'uploaded_at'
            ).order_by('-uploaded_at')
    except Exception:
        # Fallback to a safer query with defer
        documents = MedicalDocument.objects.filter(patient=patient).defer(
            'extracted_text', 'is_pathology_report', 'ai_analysis_json', 'analysis_timestamp'
        ).order_by('-uploaded_at')

    # Get reviews
    reviews = ClinicianReview.objects.filter(
        patient_record=medical_record
    ).order_by('-review_date') if medical_record else []

    context = {
        'patient': patient,
        'medical_record': medical_record,
        'documents': documents,
        'reviews': reviews,
    }

    return render(request, 'medical/clinician/patient_detail.html', context)


@login_required
@role_required(['clinician'])
def clinician_edit_patient_record(request, patient_id):
    """
    View for clinician to edit patient medical record.
    """
    patient = get_object_or_404(User, id=patient_id, assigned_doctor=request.user)

    # Get or create medical record
    try:
        medical_record = PatientRecord.objects.get(patient=patient)
    except PatientRecord.DoesNotExist:
        medical_record = PatientRecord(patient=patient)

    if request.method == 'POST':
        form = PatientRecordForm(request.POST, instance=medical_record)
        if form.is_valid():
            form.save()

            # Create a review record of this change
            review = ClinicianReview(
                patient_record=medical_record,
                clinician=request.user,
                notes=_('Updated patient medical record.')
            )
            review.save()

            messages.success(request, _('Patient record updated successfully.'))

            if request.htmx:
                return HttpResponse(
                    _("Patient record updated successfully."),
                    headers={"HX-Trigger": "recordUpdated"}
                )
            return redirect('medical:clinician_patient_detail', patient_id=patient_id)
    else:
        form = PatientRecordForm(instance=medical_record)

    context = {
        'form': form,
        'patient': patient,
        'medical_record': medical_record,
    }

    if request.htmx:
        return render(request, 'medical/clinician/partials/record_form.html', context)

    return render(request, 'medical/clinician/edit_record.html', context)


@login_required
@role_required(['clinician', 'administrator'])
def get_cancer_subtypes(request):
    """
    View to get cancer subtypes based on selected organ.
    Returns a list of options for the cancer type dropdown.
    """
    organ_id = request.GET.get('organ_id')
    
    if not organ_id:
        # If no organ is selected, return empty options
        options_html = '<option value="">--- Select an organ type first ---</option>'
    else:
        # Get the organ type
        try:
            organ = CancerType.objects.get(id=organ_id)
            
            # Is this an organ type?
            if organ.is_organ:
                # Get all subtypes for this organ
                subtypes = CancerType.objects.filter(parent=organ)
                
                if subtypes.exists():
                    # Create HTML options for the dropdown with a placeholder
                    options_html = ('<option value="">--- Select a cancer subtype ---</option>' + 
                                   "".join([f'<option value="{subtype.id}">{subtype.name}</option>'
                                          for subtype in subtypes]))
                else:
                    # No subtypes found, use the organ type itself
                    options_html = f'<option value="{organ.id}">{organ.name} (Primary)</option>'
            else:
                # It's already a subtype, just show it
                options_html = f'<option value="{organ.id}">{organ.name}</option>'
        except CancerType.DoesNotExist:
            options_html = '<option value="">--- Invalid organ type selected ---</option>'
    
    # For debugging
    logger.debug(f"Organ ID: {organ_id}, Generated options: {options_html}")
    
    return HttpResponse(options_html)


@login_required
@role_required(['clinician'])
def clinician_add_review(request, patient_id):
    """
    View for clinician to add a review note.
    """
    patient = get_object_or_404(User, id=patient_id, assigned_doctor=request.user)

    # Get medical record
    medical_record = get_object_or_404(PatientRecord, patient=patient)

    if request.method == 'POST':
        form = ClinicianReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.patient_record = medical_record
            review.clinician = request.user
            review.save()

            messages.success(request, _('Review note added successfully.'))

            if request.htmx:
                context = {
                    'review': review,
                    'just_added': True,
                }
                return render(request, 'medical/clinician/partials/review_item.html', context)
            return redirect('medical:clinician_patient_detail', patient_id=patient_id)
    else:
        form = ClinicianReviewForm()

    context = {
        'form': form,
        'patient': patient,
    }

    if request.htmx:
        return render(request, 'medical/clinician/partials/review_form.html', context)

    return render(request, 'medical/clinician/add_review.html', context)


@login_required
@role_required(['clinician', 'administrator'])
def upload_medical_document(request, patient_id):
    """
    Step 1: View for clinician or admin to upload a medical document.
    Only requires selecting a PDF file; AI will handle the rest.
    """
    if request.user.is_clinician():
        patient = get_object_or_404(User, id=patient_id, assigned_doctor=request.user)
    else:
        patient = get_object_or_404(User, id=patient_id)

    if request.method == 'POST':
        form = MedicalDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            # First create a basic document with minimal information to avoid schema issues
            import os
            import uuid
            import json
            import hashlib
            from django.utils import timezone
            
            # Get filename
            uploaded_file = form.cleaned_data['file']
            filename = uploaded_file.name
            
            # Create a placeholder hash
            temp_hash = hashlib.sha256(filename.encode()).hexdigest()
            
            # Create and save the document
            document = MedicalDocument(
                patient=patient,
                uploaded_by=request.user,
                file=uploaded_file,
                title=filename,
                document_type='Medical Document',
                description='Document uploaded successfully.',
                file_hash=temp_hash,  # Add the placeholder hash
                patient_notes=''
            )
            document.save()
            document_id = document.id
            
            # Now try to process with AI if fields exist
            try:
                # Check if AI analysis fields exist in the database
                from django.db import connection
                cursor = connection.cursor()
                cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name='medical_medicaldocument' AND column_name='extracted_text'")
                ai_fields_exist = bool(cursor.fetchone()[0])
                
                if ai_fields_exist:
                    from utils.ai import process_document_for_analysis, get_matching_cancer_types
                    from .utils import get_language_by_code
                    
                    # Get fresh document instance
                    document = MedicalDocument.objects.get(id=document_id)
                    
                    # Calculate proper file hash
                    try:
                        with document.file.open('rb') as f:
                            file_content = f.read()
                            file_hash = hashlib.sha256(file_content).hexdigest()
                            # Update the hash
                            document.file_hash = file_hash
                            document.save(update_fields=['file_hash'])
                    except Exception as e:
                        logger.error(f"Error calculating file hash: {str(e)}")
                    
                    # Process the document with AI
                    logger.info(f"Starting AI analysis for document: {document_id}")
                    ai_result, extracted_text, metadata = process_document_for_analysis(document.file.path)
                    
                    # Log AI processing results
                    logger.info(f"AI analysis completed. Results summary:")
                    logger.info(f"- Extracted text length: {len(extracted_text) if extracted_text else 0} characters")
                    logger.info(f"- Is pathology report: {ai_result is not None}")
                    logger.info(f"- Metadata keys found: {', '.join(metadata.keys())}")
                    
                    if ai_result:
                        logger.info(f"- Cancer type detected: {ai_result.get('cancer_type', 'Not specified')}")
                        logger.info(f"- FIGO stage: {ai_result.get('figo_stage', 'Not specified')}")
                        logger.info(f"- Pathologic stage: {ai_result.get('final_pathologic_stage', 'Not specified')}")
                    
                    # Store AI processing results in session for displaying to user
                    request.session['ai_processing_results'] = {
                        'document_id': str(document_id),
                        'extracted_text_length': len(extracted_text) if extracted_text else 0,
                        'is_pathology_report': ai_result is not None,
                        'cancer_type_detected': ai_result.get('cancer_type', 'Not specified') if ai_result else 'None',
                        'figo_stage': ai_result.get('figo_stage', 'Not specified') if ai_result else 'None',
                        'pathologic_stage': ai_result.get('final_pathologic_stage', 'Not specified') if ai_result else 'None',
                        'metadata': {
                            'title': metadata.get('title', filename),
                            'document_type': metadata.get('document_type', 'Medical Document'),
                            'cancer_type_text': metadata.get('cancer_type_text', ''),
                            'language': metadata.get('language', 'en'),
                        }
                    }
                    
                    # Prepare updated metadata
                    title = metadata.get('title', filename)
                    document_type = metadata.get('document_type', 'Medical Document')
                    description = metadata.get('description', '')
                    patient_notes = metadata.get('patient_notes', '')
                    
                    # Get language if detected
                    language = None
                    language_code = metadata.get('language', 'en')
                    language = get_language_by_code(language_code)
                    if language:
                        document.language = language
                    
                    # Try to match cancer type
                    cancer_type_text = metadata.get('cancer_type_text', '')
                    
                    # Also try the analyzed pathology report if no direct cancer type was found
                    if not cancer_type_text and ai_result and ai_result.get('cancer_type') and ai_result.get('cancer_type') != "Not specified":
                        cancer_type_text = ai_result.get('cancer_type')
                    
                    # Track if we found a cancer type
                    cancer_type_found = False
                    matching_info = {}
                    
                    if cancer_type_text:
                        logger.info(f"Attempting to match cancer type: '{cancer_type_text}'")
                        
                        # Get all cancer types for debugging
                        from django.db.models import Count
                        all_types = list(CancerType.objects.all().values('id', 'name', 'is_organ', 'parent_id'))
                        logger.info(f"Available cancer types in database: {len(all_types)}")
                        logger.info(f"Top 5 cancer types: {', '.join([t['name'] for t in all_types[:5]])}")
                        
                        # Get available languages for debugging
                        from apps.accounts.models import Language
                        all_langs = list(Language.objects.all().values('id', 'code'))
                        logger.info(f"Available languages in database: {len(all_langs)}")
                        if all_langs:
                            logger.info(f"Language codes: {', '.join([l['code'] for l in all_langs])}")
                        else:
                            logger.warning("No languages found in database!")
                        
                        # Try to match cancer type
                        organ_type, subtype = get_matching_cancer_types(cancer_type_text)
                        
                        # Store matching info for display
                        matching_info = {
                            'search_text': cancer_type_text,
                            'matched_organ': organ_type.name if organ_type else None,
                            'matched_subtype': subtype.name if subtype else None
                        }
                        request.session['cancer_type_matching'] = matching_info
                        
                        if subtype:
                            # Found a specific subtype
                            document.cancer_type = subtype
                            cancer_type_found = True
                            logger.info(f"Matched to specific cancer subtype: {subtype.name} (organ: {subtype.parent.name})")
                        elif organ_type:
                            # Found only the organ type
                            document.cancer_type = organ_type
                            cancer_type_found = True
                            logger.info(f"Matched to organ type: {organ_type.name}")
                    
                    # If we couldn't match the cancer type but have text, add it to description
                    if not cancer_type_found and cancer_type_text:
                        additional_info = f"\n\nAI detected possible cancer type: {cancer_type_text}"
                        if description:
                            description += additional_info
                        else:
                            description = f"Document uploaded and processed.{additional_info}"
                        
                        logger.warning(f"Could not match cancer type text: '{cancer_type_text}' to database entries. Available types: {[t['name'] for t in all_types[:5]]}")
                    
                    # Update basic document info
                    document.title = title
                    
                    # Update document_type to indicate pathology report if detected by AI
                    if ai_result is not None:
                        document.document_type = "Pathology Report"
                    else:
                        document.document_type = document_type
                        
                    document.description = description
                    document.patient_notes = patient_notes
                    
                    # Save the document changes
                    document.save()
                    
                    # Now try to update AI fields if they exist
                    try:
                        cursor.execute(
                            """
                            SELECT COUNT(*) FROM information_schema.columns 
                            WHERE table_name='medical_medicaldocument' 
                            AND column_name IN ('extracted_text', 'is_pathology_report', 'ai_analysis_json', 'analysis_timestamp')
                            """
                        )
                        num_fields = cursor.fetchone()[0]
                        
                        if num_fields == 4:
                            # Get the model and set the fields
                            document = MedicalDocument.objects.get(id=document_id)
                            document.extracted_text = extracted_text
                            document.is_pathology_report = ai_result is not None
                            document.ai_analysis_json = ai_result
                            document.analysis_timestamp = timezone.now()
                            document.save()
                            
                            # For debugging
                            logger.info(f"Successfully updated document {document_id} with AI analysis fields")
                    except Exception as e:
                        logger.error(f"Error updating AI fields: {str(e)}")
                    
                    # If this is a pathology report, DON'T create a patient record automatically
                    # Just log that we found a pathology report for later processing in the review stage
                    is_pathology_report = ai_result is not None
                    if is_pathology_report and ai_result:
                        try:
                            # Check if a patient record already exists (don't create one)
                            try:
                                existing_record = PatientRecord.objects.get(patient=patient)
                                logger.info(f"Existing patient record found for {patient.id}, will not modify until review")
                            except PatientRecord.DoesNotExist:
                                logger.info(f"No patient record exists for {patient.id}, will be created during review")

                            # Store detected values for later but don't create a record
                            cancer_type_name = ai_result.get('cancer_type')
                            if cancer_type_name and cancer_type_name != "Not specified" and document.cancer_type:
                                logger.info(f"Detected cancer type '{cancer_type_name}' will be applied during review")

                            # Process cancer stage if available
                            stage_text = ai_result.get('figo_stage')
                            if not stage_text or stage_text == "Not specified":
                                stage_text = ai_result.get('final_pathologic_stage')

                            if stage_text and stage_text != "Not specified":
                                logger.info(f"Detected cancer stage '{stage_text}' will be applied during review")

                        except Exception as e:
                            logger.error(f"Error checking patient record status: {str(e)}")
                    
                    # Redirect to the review page
                    return redirect('medical:review_medical_document', document_id=document_id)
                else:
                    # AI fields don't exist yet in the database
                    messages.success(request, _('Document uploaded successfully. AI analysis not available.'))
            except ImportError as e:
                logger.error(f"Import error: {str(e)}")
                messages.success(request, _('Document uploaded successfully. AI analysis not installed.'))
            except Exception as e:
                logger.error(f"Error processing document: {str(e)}")
                messages.success(request, _('Document uploaded successfully. Error during analysis.'))
            
            # If we didn't redirect to review page above, show processing results in the response
            if request.htmx:
                # Prepare debug message with AI processing results
                if 'ai_processing_results' in request.session:
                    ai_results = request.session['ai_processing_results']
                    results_html = f"""
                    <div class="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                        <h3 class="text-md font-semibold text-blue-800 mb-2">AI Processing Results:</h3>
                        <ul class="list-disc pl-5 text-sm">
                            <li>Document Type: {ai_results.get('metadata', {}).get('document_type', 'Not detected')}</li>
                            <li>Cancer Type: {ai_results.get('cancer_type_detected', 'Not detected')}</li>
                            <li>Is Pathology Report: {'Yes' if ai_results.get('is_pathology_report') else 'No'}</li>
                            <li>Text Extracted: {ai_results.get('extracted_text_length', 0)} characters</li>
                            {'<li>FIGO Stage: ' + ai_results.get('figo_stage') + '</li>' if ai_results.get('figo_stage') and ai_results.get('figo_stage') != 'Not specified' and ai_results.get('figo_stage') != 'None' else ''}
                            {'<li>Pathologic Stage: ' + ai_results.get('pathologic_stage') + '</li>' if ai_results.get('pathologic_stage') and ai_results.get('pathologic_stage') != 'Not specified' and ai_results.get('pathologic_stage') != 'None' else ''}
                        </ul>
                        <div class="mt-2">
                            <a href="/medical/document/{ai_results.get('document_id')}/view/" class="text-sm text-blue-600 hover:underline">View Full Analysis</a>
                        </div>
                    </div>
                    """
                    success_message = _("Document uploaded and processed successfully.")
                    return HttpResponse(
                        f"<div>{success_message}{results_html}</div>",
                        headers={"HX-Trigger": "documentUploaded"}
                    )
                
                # Fallback if no AI results
                return HttpResponse(
                    _("Document uploaded successfully."),
                    headers={"HX-Trigger": "documentUploaded"}
                )

            # Redirect based on role
            if request.user.is_clinician():
                return redirect('medical:clinician_patient_detail', patient_id=patient_id)
            else:
                return redirect('medical:admin_patient_detail', patient_id=patient_id)
        else:
            # Form validation failed
            logger.error(f"Form validation errors: {form.errors}")

            # Return a more helpful error message for HTMX requests
            if request.htmx:
                error_message = _("Please select a valid PDF file to upload.")
                if 'file' in form.errors:
                    error_message = form.errors['file'][0]

                return HttpResponse(
                    f'<div class="p-4 bg-red-50 border border-red-200 rounded-md">'
                    f'<p class="text-red-700">{error_message}</p>'
                    f'</div>',
                    status=400
                )
    else:
        form = MedicalDocumentForm()

    context = {
        'form': form,
        'patient': patient,
    }

    if request.htmx:
        return render(request, 'medical/partials/document_upload_form.html', context)

    return render(request, 'medical/upload_document.html', context)


@login_required
@role_required(['clinician', 'administrator'])
def view_ai_debug(request):
    """
    Debug view to see the raw AI results stored in the session.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Prepare context with any debug data
    context = {
        'ai_processing_results': request.session.get('ai_processing_results', {}),
        'cancer_type_matching': request.session.get('cancer_type_matching', {})
    }
    
    # Simple template with debug information
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Debug View</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100 p-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-2xl font-bold mb-4">AI Processing Debug Information</h1>
            
            <div class="bg-white rounded-lg shadow p-6 mb-6">
                <h2 class="text-lg font-semibold mb-3">AI Processing Results</h2>
                <div class="bg-gray-50 p-4 rounded overflow-auto">
                    <pre class="text-sm">{pprint(context['ai_processing_results'])}</pre>
                </div>
            </div>
            
            <div class="bg-white rounded-lg shadow p-6">
                <h2 class="text-lg font-semibold mb-3">Cancer Type Matching</h2>
                <div class="bg-gray-50 p-4 rounded overflow-auto">
                    <pre class="text-sm">{pprint(context['cancer_type_matching'])}</pre>
                </div>
            </div>
            
            <div class="mt-6">
                <a href="javascript:history.back()" class="text-blue-600 hover:underline">← Back</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


@login_required
def view_medical_document(request, document_id):
    """
    View for displaying a medical document with all its AI-generated analysis and metadata.

    This function retrieves and displays a medical document to authorized users.
    It performs security checks to ensure the user has permission to view the document,
    and handles AI analysis data if available by checking for the required database fields.

    Args:
        request: HttpRequest object containing metadata about the request
        document_id: UUID of the document to view

    Returns:
        HttpResponse object with the rendered template or redirect
    """
    # Import the error handling utility
    from utils.error_handling import handle_view_exception, safe_execution
    from .utils import check_column_exists

    try:
        document = get_object_or_404(MedicalDocument, id=document_id)

        # First check if the user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, _('You must be logged in to view documents.'))
            return redirect('login')

        # Security check using utility function - only allow assigned doctor
        from .utils import can_view_document
        if not can_view_document(request.user, document, doctor_only=True):
            messages.error(request, _('Only the assigned doctor can view this document.'))
            # Redirect to appropriate dashboard based on user role
            if hasattr(request.user, 'role') and request.user.role:
                if request.user.role.name == 'patient':
                    return redirect('medical:patient_dashboard')
                elif request.user.role.name == 'clinician':
                    return redirect('medical:clinician_dashboard')
            return redirect('accounts:login')

        # Function to safely check for AI fields existence
        @safe_execution(default_return=False)
        def check_ai_fields_exist():
            """Check if AI fields exist in the database schema"""
            # Define the set of AI fields to check
            ai_fields = ['extracted_text', 'is_pathology_report', 'ai_analysis_json', 'analysis_timestamp']

            # Check each field individually
            return all(
                check_column_exists('medical_medicaldocument', field_name)
                for field_name in ai_fields
            )

        # Check if AI fields exist using our utility function
        ai_fields_exist = check_ai_fields_exist()

        # If AI fields don't exist, set attributes to None to prevent template errors
        if not ai_fields_exist:
            document.extracted_text = None
            document.is_pathology_report = False
            document.ai_analysis_json = None
            document.analysis_timestamp = None

        context = {
            'document': document,
            'patient': document.patient,
        }

        return render(request, 'medical/view_document.html', context)

    except Exception as e:
        # Handle any exceptions with our centralized error handler
        return handle_view_exception(
            request,
            e,
            error_template="medical/error.html",
            default_message=_("An error occurred while trying to view this document.")
        )


@login_required
def review_medical_document(request, document_id):
    """
    Step 2: Review and adjust AI-generated document metadata before finalizing.
    """
    # Handle cancel request - special case if document doesn't exist
    if request.GET.get('action') == 'cancel':
        # Try to get the document, but handle the case where it might be already deleted
        try:
            document = MedicalDocument.objects.get(id=document_id)
            
            # Get patient info before deleting
            patient = document.patient
            patient_id = patient.id if patient else None
            
            # Store patient ID in session for potential future use
            if patient_id:
                request.session['last_patient_id'] = patient_id
            
            # Security check for cancel
            if not (hasattr(request.user, 'is_administrator') and request.user.is_administrator() or
                   request.user == document.uploaded_by or
                   (patient and patient.assigned_doctor == request.user)):
                messages.error(request, _('You do not have permission to cancel this document review.'))
                if patient_id:
                    if request.user.is_clinician():
                        return redirect('medical:clinician_patient_detail', patient_id=patient_id)
                    else:
                        return redirect('medical:admin_patient_detail', patient_id=patient_id)
                else:
                    return redirect('medical:clinician_dashboard')
            
            # Log the cancellation attempt
            logger.info(f"Cancel requested for document {document_id} by user {request.user.id}")
            
            try:
                # Delete the document
                document.delete()
                logger.info(f"Document {document_id} successfully deleted on cancel")
                
                # Add success message
                messages.success(request, _('Document review cancelled and document deleted.'))
            except Exception as e:
                logger.error(f"Error deleting document {document_id} on cancel: {str(e)}")
                messages.error(request, _('Error cancelling document review. Please try again.'))
            
            # Redirect based on user role and patient existence
            if patient_id:
                if request.user.is_clinician():
                    return redirect('medical:clinician_patient_detail', patient_id=patient_id)
                else:
                    return redirect('medical:admin_patient_detail', patient_id=patient_id)
            else:
                return redirect('medical:clinician_dashboard')
                
        except MedicalDocument.DoesNotExist:
            # Document was already deleted or doesn't exist
            logger.info(f"Cancel requested for non-existent document {document_id}")
            messages.info(request, _('Document was already deleted or doesn\'t exist.'))
            
            # Try to get patient ID from session or referrer
            patient_id = request.session.get('last_patient_id')
            
            if patient_id:
                if request.user.is_clinician():
                    return redirect('medical:clinician_patient_detail', patient_id=patient_id)
                else:
                    return redirect('medical:admin_patient_detail', patient_id=patient_id)
            else:
                # No patient ID available, redirect to dashboard
                return redirect('medical:clinician_dashboard')
    
    # For all other requests (non-cancel), get the document or 404
    try:
        document = MedicalDocument.objects.get(id=document_id)
    except MedicalDocument.DoesNotExist:
        messages.error(request, _('The document you are trying to review does not exist.'))
        return redirect('medical:clinician_dashboard')
    
    # Store patient ID in session for potential future use
    if document.patient:
        request.session['last_patient_id'] = document.patient.id
        patient = document.patient
    else:
        patient = None

    # Security check - only the uploader, the assigned doctor, or an admin can review
    if not (hasattr(request.user, 'is_administrator') and request.user.is_administrator() or
            request.user == document.uploaded_by or
            (document.patient and document.patient.assigned_doctor == request.user)):
        messages.error(request, _('You do not have permission to review this document.'))
        return redirect('medical:clinician_dashboard')
    
    # Initialize document_url - was missing in some execution paths
    document_url = document.file.url if document.file else None
    
    # Keep AI processing debug info available for this view
    # (already stored in session by the upload function)
    
    if request.method == 'POST':
        form = MedicalDocumentReviewForm(request.POST, instance=document)
        if form.is_valid():
            # Before saving, check if all required fields are populated
            required_fields = ['title', 'document_type', 'description', 'patient_notes']
            for field in required_fields:
                if not form.cleaned_data.get(field):
                    messages.error(request, _('Please fill in all required fields before finalizing the document.'))
                    # Prepare context for form
                    context = {
                        'form': form,
                        'document': document,
                        'ai_analysis': document.ai_analysis if hasattr(document, 'ai_analysis') else None,
                        'is_pathology_report': document.is_pathology_report if hasattr(document, 'is_pathology_report') else False,
                    }
                    
                    # Check if this is a modal request
                    is_modal = request.GET.get('format') == 'modal'
                    
                    if is_modal or request.htmx:
                        # Return the form for HTMX or modal requests
                        return render(request, 'medical/partials/document_review_form.html', context)
                    else:
                        # Return the full page for regular requests
                        context.update({
                            'patient': document.patient,
                            'document_url': document_url,
                            'has_extracted_text': hasattr(document, 'extracted_text') and document.extracted_text,
                        })
                        return render(request, 'medical/review_document.html', context)

            # Check if a valid cancer type is selected - CRITICAL VALIDATION
            cancer_type = form.cleaned_data.get('cancer_type')
            if not cancer_type:
                messages.error(request, _('Please select a valid cancer type before finalizing.'))
                # Prepare context for form
                context = {
                    'form': form,
                    'document': document,
                    'ai_analysis': document.ai_analysis if hasattr(document, 'ai_analysis') else None,
                    'is_pathology_report': document.is_pathology_report if hasattr(document, 'is_pathology_report') else False,
                }
                
                # Check if this is a modal request
                is_modal = request.GET.get('format') == 'modal'
                
                if is_modal or request.htmx:
                    # Return the form for HTMX or modal requests
                    return render(request, 'medical/partials/document_review_form.html', context)
                else:
                    # Return the full page for regular requests
                    context.update({
                        'patient': document.patient,
                        'document_url': document_url,
                        'has_extracted_text': hasattr(document, 'extracted_text') and document.extracted_text,
                    })
                    return render(request, 'medical/review_document.html', context)
                
            # Additional validation to ensure the cancer type exists
            try:
                # Verify it exists in the database right now
                valid_cancer_type = CancerType.objects.get(id=cancer_type.id)
            except CancerType.DoesNotExist:
                messages.error(request, _('The selected cancer type is not valid. Please select a different one.'))
                # Prepare context for form
                context = {
                    'form': form,
                    'document': document,
                    'ai_analysis': document.ai_analysis if hasattr(document, 'ai_analysis') else None,
                    'is_pathology_report': document.is_pathology_report if hasattr(document, 'is_pathology_report') else False,
                }
                
                # Check if this is a modal request
                is_modal = request.GET.get('format') == 'modal'
                
                if is_modal or request.htmx:
                    # Return the form for HTMX or modal requests
                    return render(request, 'medical/partials/document_review_form.html', context)
                else:
                    # Return the full page for regular requests
                    context.update({
                        'patient': document.patient,
                        'document_url': document_url,
                        'has_extracted_text': hasattr(document, 'extracted_text') and document.extracted_text,
                    })
                    return render(request, 'medical/review_document.html', context)
                
            # If we get here, we have a valid cancer type and can proceed
            # Log current values before changes
            logger.info(f"BEFORE CHANGES - Document {document.id} current values:")
            logger.info(f"  title: '{document.title}'")
            logger.info(f"  document_type: '{document.document_type}'")
            logger.info(f"  description: '{document.description}'")
            logger.info(f"  patient_notes: '{document.patient_notes}'")
            logger.info(f"  cancer_type: {document.cancer_type.id if document.cancer_type else 'None'}")
            
            # Log new values from form
            logger.info(f"NEW VALUES FROM FORM:")
            logger.info(f"  title: '{form.cleaned_data.get('title')}'")
            logger.info(f"  document_type: '{form.cleaned_data.get('document_type')}'")
            logger.info(f"  description: '{form.cleaned_data.get('description')}'")
            logger.info(f"  patient_notes: '{form.cleaned_data.get('patient_notes')}'")
            logger.info(f"  cancer_type: {valid_cancer_type.id if valid_cancer_type else 'None'}")
            
            # Update fields on the document
            document.title = form.cleaned_data.get('title')
            document.document_type = form.cleaned_data.get('document_type')
            document.description = form.cleaned_data.get('description')
            document.patient_notes = form.cleaned_data.get('patient_notes')
            document.cancer_type = valid_cancer_type
            
            # If language was selected, update it
            language = form.cleaned_data.get('language')
            if language:
                document.language = language
            
            # Save document changes
            document.save()
            
            # Try to get AI analysis if it exists
            ai_analysis = None
            if hasattr(document, 'ai_analysis_json') and document.ai_analysis_json:
                try:
                    # Load from JSON string if it's a string
                    if isinstance(document.ai_analysis_json, str):
                        import json
                        ai_analysis = json.loads(document.ai_analysis_json)
                    else:
                        # Otherwise it's already a Python dict
                        ai_analysis = document.ai_analysis_json
                        
                    # Extract recommended treatment if available
                    if 'recommended_treatment' in ai_analysis and ai_analysis['recommended_treatment'] != "Not specified":
                        document.recommended_treatment = ai_analysis['recommended_treatment']
                        # Save again with the new field
                        document.save(update_fields=['recommended_treatment'])
                except Exception as e:
                    logger.error(f"Error parsing AI analysis JSON: {str(e)}")
            
            # All validations passed, now we can safely create or update the medical record
            # Look for an existing patient record, but don't create it automatically
            if patient:  # Only proceed if we have a patient
                try:
                    patient_record = PatientRecord.objects.get(patient=patient)
                    record_created = False
                    # Update the cancer type
                    patient_record.cancer_type = valid_cancer_type
                except PatientRecord.DoesNotExist:
                    # Create a new patient record only now during save
                    patient_record = PatientRecord(
                        patient=patient,
                        diagnosis_date=datetime.date.today(),
                        cancer_type=valid_cancer_type
                    )
                    record_created = True
                    logger.info(f"Creating new patient record for patient {patient.id} during save")
                
                # Link this document to the patient record
                document.patient_record = patient_record
                document.save(update_fields=['patient_record'])
                
                # If AI detected stage information or recommended treatment, add it to the record
                if ai_analysis:
                    # Get or create the stage based on FIGO stage or pathologic stage
                    stage_text = ai_analysis.get('figo_stage') or ai_analysis.get('final_pathologic_stage')
                    if stage_text and stage_text != "Not specified":
                        try:
                            patient_record.cancer_stage_text = stage_text[:50]  # Limit to model's max length
                            logger.info(f"Applied cancer stage '{stage_text}' to patient record from AI analysis")
                        except Exception as e:
                            # If we can't apply the stage for some reason, log it
                            logger.error(f"Could not apply cancer stage '{stage_text}': {str(e)}")

                    # Copy recommended treatment from AI analysis to patient record
                    recommended_treatment = ai_analysis.get('recommended_treatment')
                    if recommended_treatment and recommended_treatment != "Not specified":
                        try:
                            patient_record.recommended_treatment = recommended_treatment
                            logger.info(f"Applied recommended treatment to patient record from AI analysis")
                        except Exception as e:
                            # If we can't apply the recommended treatment for some reason, log it
                            logger.error(f"Could not apply recommended treatment: {str(e)}")

                # Save the patient record with all changes
                try:
                    patient_record.save()
                    # Log the creation or update
                    if record_created:
                        logger.info(f"Created new patient record for patient {patient.id} with cancer type {valid_cancer_type.name}")
                    else:
                        logger.info(f"Updated patient record for patient {patient.id} with cancer type {valid_cancer_type.name}")
                except Exception as e:
                    logger.error(f"Error saving patient record: {str(e)}")
                    messages.error(request, _('Error updating patient record. Please try again.'))
                    return render(request, 'medical/partials/document_review_form.html', {
                        'form': form,
                        'document': document,
                        'ai_analysis': ai_analysis,
                        'is_pathology_report': document.is_pathology_report if hasattr(document, 'is_pathology_report') else False,
                    })
            
            messages.success(request, _('Document information updated and finalized.'))
            
            # Check if this is a modal request (iframe)
            is_modal = request.GET.get('format') == 'modal'
            
            # For modal requests in any context (HTMX or regular), return a simple HTML page with postMessage
            if is_modal:
                html_content = "<!DOCTYPE html><html><head><title>Document Saved</title></head><body><script>window.parent.postMessage('document_saved', '*');</script></body></html>"
                return HttpResponse(html_content)
            
            # Handle HTMX requests (non-modal)
            if request.htmx:
                response = HttpResponse("Redirect")
                if patient:
                    if request.user.is_clinician():
                        response['HX-Redirect'] = reverse('medical:clinician_patient_detail', kwargs={'patient_id': patient.id})
                    else:
                        response['HX-Redirect'] = reverse('medical:admin_patient_detail', kwargs={'patient_id': patient.id})
                else:
                    response['HX-Redirect'] = reverse('medical:clinician_dashboard')
                return response
            
            # For regular POST requests (non-HTMX, non-modal)
            if patient:
                if request.user.is_clinician():
                    return redirect('medical:clinician_patient_detail', patient_id=patient.id)
                else:
                    return redirect('medical:admin_patient_detail', patient_id=patient.id)
            else:
                return redirect('medical:clinician_dashboard')
        else:
            # Form is not valid, display errors to the user
            # Prepare context for form with error messages from form validation
            context = {
                'form': form,
                'document': document,
                'ai_analysis': document.ai_analysis if hasattr(document, 'ai_analysis') else None,
                'is_pathology_report': document.is_pathology_report if hasattr(document, 'is_pathology_report') else False,
            }
            
            # Check if this is a modal request
            is_modal = request.GET.get('format') == 'modal'
            
            if is_modal or request.htmx:
                # Return the form for HTMX or modal requests
                return render(request, 'medical/partials/document_review_form.html', context)
            else:
                # Return the full page for regular requests
                context.update({
                    'patient': document.patient,
                    'document_url': document_url,
                    'has_extracted_text': hasattr(document, 'extracted_text') and document.extracted_text,
                })
                return render(request, 'medical/review_document.html', context)
    else:
        # GET request or other methods
        form = MedicalDocumentReviewForm(instance=document)
    
    # Check if AI fields exist in the database
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='medical_medicaldocument' AND column_name='extracted_text'")
        ai_fields_exist = bool(cursor.fetchone())
    except Exception:
        ai_fields_exist = False
    
    # Only try to access AI fields if they exist
    has_extracted_text = False
    is_pathology_report = False
    ai_analysis = None
    
    if ai_fields_exist:
        try:
            # Try to access each field safely
            cursor = connection.cursor()
            sql = "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='medical_medicaldocument' AND column_name IN ('extracted_text', 'is_pathology_report', 'ai_analysis_json')"
            cursor.execute(sql)
            column_count = cursor.fetchone()[0]
            columns_exist = (column_count == 3)
            
            if columns_exist:
                cursor.execute(
                    "SELECT extracted_text, is_pathology_report, ai_analysis_json FROM medical_medicaldocument WHERE id = %s",
                    [document_id]
                )
                result = cursor.fetchone()
                if result:
                    extracted_text, is_pathology, ai_json = result
                    has_extracted_text = bool(extracted_text)
                    is_pathology_report = bool(is_pathology)
                    if ai_json:
                        try:
                            import json
                            ai_analysis = json.loads(ai_json)
                        except:
                            ai_analysis = None
        except Exception as e:
            logger.error(f"Error accessing AI fields: {str(e)}")
    
    # Prepare the context for rendering
    context = {
        'form': form,
        'document': document,
        'patient': document.patient,
        'document_url': document_url,
        'has_extracted_text': has_extracted_text,
        'is_pathology_report': is_pathology_report,
        'ai_analysis': ai_analysis,
    }
    
    # Check if we should return just the form (for modal editing)
    form_only = request.GET.get('format') == 'form'
    is_modal = request.GET.get('format') == 'modal'
    
    if form_only:
        # Return just the form template
        return render(request, 'medical/partials/document_review_form.html', context)
    elif is_modal:
        # Ensure all boolean values are converted to JavaScript compatible format
        if 'is_pathology_report' in context:
            context['is_pathology_report_js'] = 'true' if context['is_pathology_report'] else 'false'
        
        # Return the modal template that wraps the form partial
        return render(request, 'medical/modal_form.html', context)
    elif request.htmx:
        # Return the HTMX partial version
        return render(request, 'medical/partials/document_review_form.html', context)
    else:
        # Return the full page
        return render(request, 'medical/review_document.html', context)
# Administrator Views
@login_required
@role_required(['administrator'])
def admin_medical_dashboard(request):
    """
    Administrator medical dashboard view.
    """
    # Get counts
    patient_count = User.objects.filter(role__name='patient').count()
    clinician_count = User.objects.filter(role__name='clinician').count()
    admin_count = User.objects.filter(role__name='administrator').count()
    document_count = MedicalDocument.objects.count()
    record_count = PatientRecord.objects.count()
    cancer_type_count = CancerType.objects.count()
    
    # Get pending doctor assignment requests
    pending_doctor_requests = DoctorAssignmentRequest.objects.filter(status='pending').select_related('patient', 'doctor').order_by('-requested_at')[:5]
    
    # If this is an HTMX request and we're targeting just the doctor requests container,
    # return only that partial
    if request.htmx and request.htmx.target == 'pendingDoctorRequestsContainer':
        context = {
            'pending_doctor_requests': pending_doctor_requests,
        }
        return render(request, 'medical/admin/partials/doctor_requests_list.html', context)
    
    # Calculate user activity status counts
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True, is_email_verified=True).count()
    inactive_users = User.objects.filter(is_active=True, is_email_verified=False).count()
    suspended_users = User.objects.filter(is_active=False).count()
    
    # Calculate percentages for the user activity status chart
    active_percent = round((active_users / total_users) * 100) if total_users > 0 else 0
    inactive_percent = round((inactive_users / total_users) * 100) if total_users > 0 else 0
    suspended_percent = round((suspended_users / total_users) * 100) if total_users > 0 else 0
    
    # Ensure percentages add up to 100%
    if active_percent + inactive_percent + suspended_percent != 100 and total_users > 0:
        # Adjust the largest percentage to make the sum 100%
        if active_percent >= inactive_percent and active_percent >= suspended_percent:
            active_percent = 100 - inactive_percent - suspended_percent
        elif inactive_percent >= active_percent and inactive_percent >= suspended_percent:
            inactive_percent = 100 - active_percent - suspended_percent
        else:
            suspended_percent = 100 - active_percent - inactive_percent
    
    # Get chat session count from the last 24 hours (if chat app available)
    chat_session_count = 0
    try:
        from apps.chat.models import ChatSession
        from django.utils import timezone
        import datetime
        
        # Count chat sessions in the last 24 hours
        yesterday = timezone.now() - datetime.timedelta(days=1)
        chat_session_count = ChatSession.objects.filter(created_at__gte=yesterday).count()
    except (ImportError, AttributeError):
        # Chat app may not be set up or model structure is different
        pass
    
    # Get recent user registrations (last 10)
    recent_users = User.objects.all().order_by('-date_joined')[:10]
    
    # Registration trend data for the chart (last 7 days)
    registration_dates = []
    registration_counts = []
    
    # Generate data for the last 7 days
    for i in range(6, -1, -1):
        date = timezone.now().date() - datetime.timedelta(days=i)
        count = User.objects.filter(date_joined__date=date).count()
        
        # Format date as "Jan 01" for display
        formatted_date = date.strftime("%b %d")
        
        registration_dates.append(formatted_date)
        registration_counts.append(count)
    
    # Record types data for the chart
    from django.db.models import Count, Sum, F, Value, IntegerField
    from django.db.models.functions import Coalesce
    import json
    
    # Get organ cancer types only
    organ_cancer_types = CancerType.objects.filter(is_organ=True)
    
    # Prepare data structure for chart
    chart_data = []
    
    for organ in organ_cancer_types:
        # Count patients directly assigned to this organ type
        direct_patients = PatientRecord.objects.filter(cancer_type=organ).count()
        
        # Count patients assigned to subtypes of this organ
        subtype_patients = 0
        for subtype in organ.subtypes.all():
            subtype_patients += PatientRecord.objects.filter(cancer_type=subtype).count()
        
        # Total patient count
        total_patients = direct_patients + subtype_patients
        
        # Only include in chart if there are patients
        if total_patients > 0:
            chart_data.append((organ.name, total_patients))
    
    # Sort by total patient count (descending)
    chart_data.sort(key=lambda x: x[1], reverse=True)
    
    # Take top 5 for display
    top_chart_data = chart_data[:5]
    
    record_types = [ct[0] for ct in top_chart_data]
    record_type_counts = [ct[1] for ct in top_chart_data]
    
    # If there's no data, provide some default values to prevent JS errors
    if not record_types:
        record_types = ["No Data"]
        record_type_counts = [0]
        
    # Get only organ type cancer types with pagination and sorting support
    all_cancer_types = CancerType.objects.filter(is_organ=True)

    # Process sorting parameters that might be passed from the dashboard
    sort_by = request.GET.get('sort', 'name')  # Default sort by name
    sort_order = request.GET.get('order', 'asc')  # Default ascending order

    # Map sorting columns if needed
    if sort_by == 'subtypes':
        # Annotate with subtypes count for sorting
        all_cancer_types = all_cancer_types.annotate(subtypes_count=Count('subtypes', distinct=True))

        # Prepare sort parameter
        sort_param = f"-subtypes_count" if sort_order == 'desc' else "subtypes_count"
        all_cancer_types = all_cancer_types.order_by(sort_param)
    elif sort_by == 'patient_count':
        # We'll handle patient count sorting manually after calculating the count
        pass
    else:
        # For other columns, do standard sorting
        sort_param = f"-{sort_by}" if sort_order == 'desc' else sort_by
        all_cancer_types = all_cancer_types.order_by(sort_param)
    
    # Now that we have the initial cancer type list and sorting parameters, let's process the patient counts

    # Annotate with direct patient counts
    all_cancer_types = list(all_cancer_types)  # Convert to list for manual processing

    # Calculate patient counts for each cancer type
    for ct in all_cancer_types:
        # Direct patient count
        direct_count = PatientRecord.objects.filter(cancer_type=ct).count()

        # Count patients from subtypes
        subtypes = ct.subtypes.all()
        subtype_count = sum(PatientRecord.objects.filter(cancer_type=subtype).count() for subtype in subtypes)

        # Set the total patient count
        ct.patient_count = direct_count + subtype_count

        # Also separately track direct and subtype counts for analytics
        ct.direct_patient_count = direct_count
        ct.subtype_patient_count = subtype_count

    # If sorting by patient_count, manually sort the list
    if sort_by == 'patient_count':
        all_cancer_types.sort(
            key=lambda x: x.patient_count,
            reverse=(sort_order == 'desc')
        )
    
    # Sorting has already been applied above
    
    # Pagination
    items_per_page = int(request.GET.get('items_per_page', 5))  # Default 5 items per page
    paginator = Paginator(all_cancer_types, items_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Add or ensure patient count for displayed items
    for cancer_type in page_obj:
        # If we didn't use the annotation (sort_by != 'patient_count'), we need to add the count
        if not hasattr(cancer_type, 'patient_count') or sort_by != 'patient_count':
            # Count patients directly from PatientRecord
            cancer_type.patient_count = PatientRecord.objects.filter(cancer_type=cancer_type).count()
            
            # Also count patients in subtypes
            for subtype in cancer_type.subtypes.all():
                cancer_type.patient_count += PatientRecord.objects.filter(cancer_type=subtype).count()

    context = {
        'patient_count': patient_count,
        'clinician_count': clinician_count,
        'admin_count': admin_count,
        'document_count': document_count,
        'record_count': record_count,
        'cancer_type_count': cancer_type_count,
        'chat_session_count': chat_session_count,
        'recent_users': recent_users,
        'registration_dates': json.dumps(registration_dates),
        'registration_counts': json.dumps(registration_counts),
        'record_types': json.dumps(record_types),
        'record_type_counts': json.dumps(record_type_counts),
        'active_users': active_users,
        'inactive_users': inactive_users,
        'suspended_users': suspended_users,
        'active_percent': active_percent,
        'inactive_percent': inactive_percent,
        'suspended_percent': suspended_percent,
        'all_cancer_types': all_cancer_types,
        'pending_doctor_requests': pending_doctor_requests,
        'current_sort': sort_by,  # Pass sorting parameters
        'current_order': sort_order,
    }

    return render(request, 'medical/admin/dashboard.html', context)


@login_required
@role_required(['administrator'])
def admin_patient_list(request):
    """
    Administrator view for listing patients.
    """
    patients = User.objects.filter(role__name='patient').select_related('role', 'language', 'assigned_doctor')

    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(patients, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all clinicians for assignment dropdown
    clinicians = User.objects.filter(role__name='clinician')

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'clinicians': clinicians,
    }

    if request.htmx:
        return render(request, 'medical/admin/partials/patient_list.html', context)

    return render(request, 'medical/admin/patient_list.html', context)


@login_required
@role_required(['administrator'])
def admin_clinician_list(request):
    """
    Administrator view for listing clinicians.
    """
    clinicians = User.objects.filter(role__name='clinician').select_related('role', 'language')

    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        clinicians = clinicians.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(clinicians, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }

    if request.htmx:
        return render(request, 'medical/admin/partials/clinician_list.html', context)

    return render(request, 'medical/admin/clinician_list.html', context)


@login_required
@role_required(['administrator'])
def admin_patient_detail(request, patient_id):
    """
    Administrator view for patient details.
    """
    # Use select_related to efficiently load the language object in a single query
    patient = get_object_or_404(
        User.objects.select_related('language'),
        id=patient_id,
        role__name='patient'
    )

    # Get patient record if exists
    medical_record = None
    try:
        medical_record = PatientRecord.objects.get(patient=patient)
    except PatientRecord.DoesNotExist:
        # No record exists yet
        pass

    # Try to get only the fields that are guaranteed to exist to avoid DB errors
    try:
        # Check if new AI fields exist in the database
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='medical_medicaldocument' AND column_name='extracted_text'")
        ai_fields_exist = bool(cursor.fetchone())
        
        # Only request fields that exist
        if ai_fields_exist:
            documents = MedicalDocument.objects.filter(patient=patient).order_by('-uploaded_at')
        else:
            # Only select fields that existed before the AI fields were added
            documents = MedicalDocument.objects.filter(patient=patient).only(
                'id', 'patient', 'title', 'document_type', 'cancer_type', 'description', 
                'patient_notes', 'file', 'file_hash', 'language', 'uploaded_by', 'uploaded_at'
            ).order_by('-uploaded_at')
    except Exception:
        # Fallback to a safer query with defer
        documents = MedicalDocument.objects.filter(patient=patient).defer(
            'extracted_text', 'is_pathology_report', 'ai_analysis_json', 'analysis_timestamp'
        ).order_by('-uploaded_at')

    # Get all clinicians for assignment
    clinicians = User.objects.filter(role__name='clinician')

    context = {
        'patient': patient,
        'medical_record': medical_record,
        'documents': documents,
        'clinicians': clinicians,
    }

    return render(request, 'medical/admin/patient_detail.html', context)


@login_required
@role_required(['administrator'])
def admin_user_modal(request, user_id):
    """
    Administrator view for showing user details in a modal.
    This view works for any user type (patient, clinician, admin).
    """
    user = get_object_or_404(User, id=user_id)
    
    # Get specialty info for clinicians
    effective_specialty = None
    if user.is_clinician():
        effective_specialty = user.specialty_name or request.session.get('specialty')
    
    # Get patient-specific info if the user is a patient
    medical_record = None
    documents = []
    clinicians = []
    
    if user.is_patient():
        try:
            medical_record = PatientRecord.objects.get(patient=user)
        except PatientRecord.DoesNotExist:
            pass
        
        documents = MedicalDocument.objects.filter(patient=user).order_by('-uploaded_at')[:5]
        clinicians = User.objects.filter(role__name='clinician')
    
    context = {
        'user_detail': user,
        'medical_record': medical_record,
        'documents': documents,
        'clinicians': clinicians,
        'effective_specialty': effective_specialty
    }
    
    if request.htmx:
        # Return just the modal content
        return render(request, 'medical/admin/partials/user_modal.html', context)
    
    # Full page fallback
    return render(request, 'medical/admin/user_detail.html', context)


@login_required
@role_required(['administrator'])
def admin_assign_doctor(request, patient_id):
    """
    Administrator view for assigning a doctor to a patient.
    """
    patient = get_object_or_404(User, id=patient_id, role__name='patient')

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        if doctor_id:
            doctor = get_object_or_404(User, id=doctor_id, role__name='clinician')

            # Assign doctor
            patient.assigned_doctor = doctor
            patient.save()

            messages.success(request, _('Doctor assigned successfully.'))

            if request.htmx:
                return HttpResponse(
                    _("Doctor assigned successfully."),
                    headers={"HX-Trigger": "doctorAssigned"}
                )
        else:
            # Remove doctor assignment
            patient.assigned_doctor = None
            patient.save()

            messages.success(request, _('Doctor assignment removed.'))

            if request.htmx:
                return HttpResponse(
                    _("Doctor assignment removed."),
                    headers={"HX-Trigger": "doctorAssigned"}
                )

        return redirect('medical:admin_patient_detail', patient_id=patient_id)

    # Get all clinicians
    clinicians = User.objects.filter(role__name='clinician')

    context = {
        'patient': patient,
        'clinicians': clinicians,
    }

    if request.htmx:
        return render(request, 'medical/admin/partials/assign_doctor_form.html', context)

    return render(request, 'medical/admin/assign_doctor.html', context)


@login_required
@role_required(['administrator'])
def admin_cancer_types(request):
    """
    Administrator view for managing cancer types.
    """
    # Get all cancer types with pagination and sorting support
    all_cancer_types = CancerType.objects.all()
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        from django.db.models import Q
        all_cancer_types = all_cancer_types.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Set filter parameters
    filter_type = request.GET.get('type', 'all')  # all, organ, or subtype
    if filter_type == 'organ':
        all_cancer_types = all_cancer_types.filter(is_organ=True, parent__isnull=True)
    elif filter_type == 'subtype':
        all_cancer_types = all_cancer_types.filter(is_organ=False, parent__isnull=False)
    
    # Get parent cancer type for filtering
    parent_filter = request.GET.get('parent_filter')
    if parent_filter:
        all_cancer_types = all_cancer_types.filter(parent_id=parent_filter)
    
    # Handle sorting
    sort_by = request.GET.get('sort', 'name')  # Default sort by name
    sort_order = request.GET.get('order', 'asc')  # Default ascending order
    
    # Validate sort column
    valid_sort_columns = ['name', 'description', 'subtypes_count', 'patient_count', 'subtypes', 'is_organ']

    # Map some alternative column names to their actual database columns
    column_mapping = {
        'subtypes': 'subtypes_count',
    }

    # Apply mapping if needed
    if sort_by in column_mapping:
        sort_by = column_mapping[sort_by]

    if sort_by not in valid_sort_columns:
        sort_by = 'name'  # Default to name if invalid
    
    # Special handling for patient_count and subtypes_count sorting
    from django.db.models import Count, Case, When, IntegerField
    
    # First get subtypes count
    all_cancer_types = all_cancer_types.annotate(
        subtypes_count=Count('subtypes', distinct=True),
    )

    # Convert to a list so we can manually process
    all_cancer_types = list(all_cancer_types)

    # Calculate actual patient counts for each cancer type
    print("CALCULATING ACTUAL PATIENT COUNTS")
    for ct in all_cancer_types:
        # Get direct patients (linked directly to this cancer type)
        direct_patients = PatientRecord.objects.filter(cancer_type=ct).count()
        ct.direct_patient_count = direct_patients

        # Initialize the total count with direct patients
        total_patients = direct_patients

        # If this is an organ type, also count patients from all subtypes
        if ct.is_organ:
            # Get all subtypes
            subtypes = ct.subtypes.all()

            # Count patients from all subtypes
            subtype_patients = PatientRecord.objects.filter(cancer_type__in=subtypes).count()
            ct.subtype_patient_count = subtype_patients

            # Add subtype patients to the total
            total_patients += subtype_patients
        else:
            ct.subtype_patient_count = 0

        # Set the total patient count
        ct.patient_count = total_patients

        # Log counts for debugging
        print(f"Cancer type: {ct.name}, Direct: {ct.direct_patient_count}, Subtypes: {ct.subtype_patient_count}, Total: {ct.patient_count}")

    # Debug - print counts to console for verification
    print("\n\n====== CANCER TYPE COUNTS DEBUG ======")
    print(f"Total cancer types: {len(all_cancer_types)}")

    # Check if we have any PatientRecord objects at all
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM medical_patientrecord")
        total_records = cursor.fetchone()[0]
    print(f"Total patient records in the database: {total_records}")

    # If no patient records exist, create a test record for first cancer type for debug purposes
    if total_records == 0 and len(all_cancer_types) > 0:
        print("No patient records found - creating a test record for debugging")
        try:
            from apps.accounts.models import User
            # Find an existing patient user
            patient_user = User.objects.filter(roles__name='patient').first()

            if patient_user:
                # Create a test patient record
                test_cancer_type = all_cancer_types[0]
                test_record, created = PatientRecord.objects.get_or_create(
                    patient=patient_user,
                    defaults={'cancer_type': test_cancer_type}
                )
                if created:
                    print(f"Created test patient record with ID {test_record.id} for user {patient_user.username}")
                    print(f"Assigned to cancer type: {test_cancer_type.name} (ID: {test_cancer_type.id})")
                    # Recalculate the count for this cancer type
                    direct_patients = PatientRecord.objects.filter(cancer_type=test_cancer_type).count()
                    test_cancer_type.direct_patient_count = direct_patients
                    test_cancer_type.patient_count = direct_patients
                    print(f"Updated patient count for {test_cancer_type.name}: {test_cancer_type.patient_count}")
                else:
                    print(f"Patient record already exists for user {patient_user.username}")
            else:
                print("No patient users found in the system - cannot create test record")
        except Exception as e:
            print(f"Error creating test patient record: {str(e)}")

    # Print all cancer types and their patients
    for ct in all_cancer_types:
        direct_count = ct.direct_patient_count if hasattr(ct, 'direct_patient_count') else 0
        subtype_count = ct.subtype_patient_count if hasattr(ct, 'subtype_patient_count') else 0
        # Force calculation of get_patient_count for verification
        fallback_count = ct.get_patient_count

        print(f"Cancer type: {ct.name}, ID: {ct.id}")
        print(f"  - Is organ: {ct.is_organ}, Parent: {ct.parent.name if ct.parent else 'None'}")
        print(f"  - Direct patients: {direct_count}")
        print(f"  - Subtype patients: {subtype_count}")
        print(f"  - Calculated patient_count: {ct.patient_count}")
        print(f"  - get_patient_count method: {fallback_count}")

        # If this is an organ type, print info about its subtypes
        if ct.is_organ:
            print(f"  - Subtypes: {ct.subtypes.count()}")
            for subtype in ct.subtypes.all():
                subtype_patients = subtype.patients.count()
                print(f"    - Subtype: {subtype.name}, Direct patients: {subtype_patients}")

        # List all patient records directly attached to this cancer type
        direct_patients = ct.patients.all()
        if direct_patients.exists():
            print(f"  - Direct patient records:")
            for i, patient in enumerate(direct_patients, 1):
                print(f"    {i}. Patient ID: {patient.id}, User: {patient.patient.username}")

    print("====== END DEBUG ======\n\n")

    # Add parent-type information for sorting
    for ct in all_cancer_types:
        if ct.is_organ:
            ct.is_parent_type = 0
        elif ct.parent is not None:
            ct.is_parent_type = 1
        else:
            ct.is_parent_type = 2

    # Sort the list of cancer types manually
    if sort_by != 'patient_count':
        if sort_order == 'desc':
            all_cancer_types.sort(key=lambda x: (x.is_parent_type, getattr(x, sort_by, ""), -x.id), reverse=True)
        else:
            all_cancer_types.sort(key=lambda x: (x.is_parent_type, getattr(x, sort_by, ""), x.id))
    else:
        # Sort by is_parent_type first, then by patient_count
        if sort_order == 'desc':
            all_cancer_types.sort(key=lambda x: (x.is_parent_type, -x.patient_count))
        else:
            all_cancer_types.sort(key=lambda x: (x.is_parent_type, x.patient_count))
    
    # Pagination
    items_per_page = int(request.GET.get('items_per_page', 5))  # Default 5 items per page
    paginator = Paginator(all_cancer_types, items_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Check if editing an existing cancer type
    edit_id = request.GET.get('edit')
    if edit_id and request.method == 'GET':
        try:
            cancer_type = CancerType.objects.get(id=edit_id)
            form = CancerTypeForm(instance=cancer_type)
            
            if request.htmx:
                context = {
                    'form': form,
                    'organ_cancer_types': CancerType.objects.filter(is_organ=True),
                }
                return render(request, 'medical/admin/partials/cancer_type_form.html', context)
        except CancerType.DoesNotExist:
            pass

    # Handle form submission (create or update)
    if request.method == 'POST':
        instance_id = request.POST.get('id')
        parent_id = request.POST.get('parent')
        is_organ = request.POST.get('is_organ') == 'on'
        
        # Validate: if is_organ is True, parent must be None
        if is_organ and parent_id:
            if request.htmx:
                return HttpResponse("Organ-level types cannot have a parent. Please uncheck 'Is organ-level' or remove the parent selection.", status=400)
            messages.error(request, _("Organ-level types cannot have a parent. Please uncheck 'Is organ-level' or remove the parent selection."))
            return redirect('medical:admin_cancer_types')
            
        # Validate: if is_organ is False, parent must be set
        if not is_organ and not parent_id:
            if request.htmx:
                return HttpResponse("Subtype must have a parent organ. Please select a parent or check 'Is organ-level'.", status=400)
            messages.error(request, _("Subtype must have a parent organ. Please select a parent or check 'Is organ-level'."))
            return redirect('medical:admin_cancer_types')
        
        if instance_id:
            # Update existing cancer type
            try:
                cancer_type = CancerType.objects.get(id=instance_id)
                form = CancerTypeForm(request.POST, instance=cancer_type)
                is_new = False
            except CancerType.DoesNotExist:
                form = CancerTypeForm(request.POST)
                is_new = True
        else:
            # Create new cancer type
            form = CancerTypeForm(request.POST)
            is_new = True
            
        if form.is_valid():
            cancer_type = form.save()
            
            message = _('Cancer type added successfully.') if is_new else _('Cancer type updated successfully.')
            messages.success(request, message)

            if request.htmx:
                # Return the new/updated item
                context = {
                    'cancer_type': cancer_type,
                    'just_added': True,
                }
                return render(request, 'medical/admin/partials/cancer_type_item.html', context)
            return redirect('medical:admin_cancer_types')
    else:
        # Create a new form 
        if not edit_id:
            # Handle pre-selecting parent if requested
            initial = {}
            parent_id = request.GET.get('parent')
            
            if parent_id:
                try:
                    parent = CancerType.objects.get(id=parent_id)
                    initial['parent'] = parent
                    initial['is_organ'] = False  # It's a subtype if parent is specified
                except CancerType.DoesNotExist:
                    pass
            
            form = CancerTypeForm(initial=initial)

    # Handle delete requests
    delete_id = request.GET.get('delete')
    # Check for _method=DELETE in POST for form-based deletion
    is_delete_request = (
        delete_id and 
        (request.method == 'DELETE' or 
         (request.method == 'POST' and request.POST.get('_method') == 'DELETE'))
    )
    
    if is_delete_request:
        try:
            cancer_type = CancerType.objects.get(id=delete_id)
            
            # Check if there are no patients with this cancer type
            if PatientRecord.objects.filter(cancer_type=cancer_type).count() == 0:
                # Check if this is an organ type with subtypes
                if cancer_type.is_organ and cancer_type.subtypes.exists():
                    messages.error(request, _('Cannot delete an organ-level cancer type that has subtypes.'))
                else:
                    cancer_type.delete()
                    messages.success(request, _('Cancer type deleted successfully.'))
                    
                    if request.htmx:
                        return HttpResponse('')  # Return empty response to remove the row
            else:
                messages.error(request, _('Cannot delete a cancer type that is assigned to patients.'))
        except CancerType.DoesNotExist:
            pass
        
        # Always redirect after successful form submission
        return redirect('medical:admin_cancer_types')

    # Handle form toggle
    show_form = request.GET.get('form')
    
    # Get all organ-level cancer types for the parent dropdown
    organ_cancer_types = CancerType.objects.filter(is_organ=True)
    
    context = {
        'cancer_types': page_obj,
        'paginator': paginator,
        'page_obj': page_obj,
        'form': form,
        'show_form': show_form != '0' if show_form is not None else True,
        'current_sort': sort_by,
        'current_order': sort_order,
        'items_per_page': items_per_page,
        'filter_type': filter_type,
        'parent_filter': parent_filter,
        'organ_cancer_types': organ_cancer_types,
        'search_query': search_query,
        'all_cancer_types': all_cancer_types,  # Add all_cancer_types to context for dashboard sorting
    }

    if request.htmx and 'form' in request.GET:
        # Make sure organ_cancer_types is always in the context
        if 'organ_cancer_types' not in context:
            context['organ_cancer_types'] = CancerType.objects.filter(is_organ=True)
        return render(request, 'medical/admin/partials/cancer_type_form.html', context)

    return render(request, 'medical/admin/cancer_types.html', context)


@login_required
@role_required(['administrator'])
def admin_cancer_stages(request):
    """
    Administrator view for managing cancer stages.
    """
    cancer_stages = CancerStage.objects.all().order_by('name')

    if request.method == 'POST':
        form = CancerStageForm(request.POST)
        if form.is_valid():
            form.save()

            messages.success(request, _('Cancer stage added successfully.'))

            if request.htmx:
                # Return the new item for appending to the list
                context = {
                    'cancer_stage': form.instance,
                    'just_added': True,
                }
                return render(request, 'medical/admin/partials/cancer_stage_item.html', context)
            return redirect('medical:admin_cancer_stages')
    else:
        form = CancerStageForm()

    context = {
        'cancer_stages': cancer_stages,
        'form': form,
    }

    if request.htmx and 'form' in request.GET:
        return render(request, 'medical/admin/partials/cancer_stage_form.html', context)

    return render(request, 'medical/admin/cancer_stages.html', context)


@login_required
@role_required(['administrator'])
def admin_faqs(request):
    """
    Administrator view for managing FAQs.
    """
    faqs = FAQ.objects.all().order_by('category', 'question_key')

    if request.method == 'POST':
        form = FAQForm(request.POST)
        if form.is_valid():
            form.save()

            messages.success(request, _('FAQ added successfully.'))

            if request.htmx:
                # Return the new item for appending to the list
                context = {
                    'faq': form.instance,
                    'just_added': True,
                }
                return render(request, 'medical/admin/partials/faq_item.html', context)
            return redirect('medical:admin_faqs')
    else:
        form = FAQForm()

    context = {
        'faqs': faqs,
        'form': form,
    }

    if request.htmx and 'form' in request.GET:
        return render(request, 'medical/admin/partials/faq_form.html', context)

    return render(request, 'medical/admin/faqs.html', context)


@login_required
@role_required(['administrator'])
def process_doctor_request(request, request_id):
    """
    View for administrators to approve or reject doctor assignment requests.
    """
    assignment_request = get_object_or_404(DoctorAssignmentRequest, id=request_id, status='pending')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            assignment_request.approve(admin_user=request.user)
            success_message = _('Doctor assignment request approved.')
            messages.success(request, success_message)
        elif action == 'reject':
            assignment_request.reject(admin_user=request.user, notes=notes)
            success_message = _('Doctor assignment request rejected.')
            messages.success(request, success_message)
        
        # Handle HTMX requests
        if request.htmx:
            context = {
                'assignment_request': assignment_request,
                'success': True,
                'action': action,
                'success_message': success_message
            }
            return render(request, 'medical/admin/partials/process_doctor_request_success.html', context)
        
        # Non-HTMX requests get redirected to the dashboard
        return redirect('medical:admin_dashboard')
    
    context = {
        'assignment_request': assignment_request
    }
    
    if request.htmx:
        return render(request, 'medical/admin/partials/process_doctor_request_form.html', context)
    
    return render(request, 'medical/admin/process_doctor_request.html', context)


@login_required
@role_required(['administrator'])
def admin_faq_translations(request, faq_id):
    """
    Administrator view for managing FAQ translations.
    """
    faq = get_object_or_404(FAQ, id=faq_id)
    translations = FAQTranslation.objects.filter(faq=faq).select_related('language')

    if request.method == 'POST':
        form = FAQTranslationForm(request.POST)
        if form.is_valid():
            # Check if translation already exists for this language
            language = form.cleaned_data['language']
            try:
                # Update existing translation
                translation = FAQTranslation.objects.get(faq=faq, language=language)
                translation.question = form.cleaned_data['question']
                translation.answer = form.cleaned_data['answer']
                translation.save()
                is_new = False
            except FAQTranslation.DoesNotExist:
                # Create new translation
                translation = form.save(commit=False)
                translation.faq = faq
                translation.save()
                is_new = True

            messages.success(request, _('FAQ translation saved successfully.'))

            if request.htmx:
                # Return the new/updated item
                context = {
                    'translation': translation,
                    'just_added': is_new,
                }
                return render(request, 'medical/admin/partials/faq_translation_item.html', context)
            return redirect('medical:admin_faq_translations', faq_id=faq_id)
    else:
        form = FAQTranslationForm()

    context = {
        'faq': faq,
        'translations': translations,
        'form': form,
    }

    if request.htmx and 'form' in request.GET:
        return render(request, 'medical/admin/partials/faq_translation_form.html', context)

    return render(request, 'medical/admin/faq_translations.html', context)

@login_required
def update_document_data(request, document_id):
    """API endpoint to update document data directly via AJAX."""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    # Check if the user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    # Get the document
    document = get_object_or_404(MedicalDocument, id=document_id)
    
    # Security check - only the patient, the assigned doctor, or an admin can view
    if not (hasattr(request.user, 'is_administrator') and request.user.is_administrator() or 
            request.user == document.uploaded_by or 
            (document.patient and document.patient.assigned_doctor == request.user)):
        return JsonResponse({"error": "Access denied"}, status=403)
    
    # Parse JSON data from the request
    try:
        import json
        data = json.loads(request.body)
        
        # Extract fields
        title = data.get('title')
        document_type = data.get('document_type')
        description = data.get('description')
        patient_notes = data.get('patient_notes')
        cancer_type_id = data.get('cancer_type')
        
        # Validate required fields
        if not all([title, document_type, description, patient_notes, cancer_type_id]):
            return JsonResponse({
                "error": "Missing required fields",
                "missing": [f for f, v in {
                    'title': title,
                    'document_type': document_type,
                    'description': description,
                    'patient_notes': patient_notes,
                    'cancer_type': cancer_type_id
                }.items() if not v]
            }, status=400)
        
        # Validate cancer type
        try:
            cancer_type = CancerType.objects.get(id=cancer_type_id)
        except CancerType.DoesNotExist:
            return JsonResponse({"error": f"Cancer type with ID {cancer_type_id} does not exist"}, status=400)
        
        # Log the data we're about to save
        logger.info(f"API UPDATE: Document {document_id} data from AJAX request:")
        logger.info(f"  title: '{title}'")
        logger.info(f"  document_type: '{document_type}'")
        logger.info(f"  description: '{description}'")
        logger.info(f"  patient_notes: '{patient_notes}'")
        logger.info(f"  cancer_type: {cancer_type_id}")
        
        # Try a direct database update using raw SQL
        try:
            from django.db import connection
            cursor = connection.cursor()
            
            # Get table name from model meta
            table_name = MedicalDocument._meta.db_table
            
            # Execute the SQL update
            cursor.execute(
                f"""
                UPDATE {table_name}
                SET
                    title = %s,
                    document_type = %s,
                    description = %s,
                    patient_notes = %s,
                    cancer_type_id = %s
                WHERE id = %s
                """,
                [
                    title,
                    document_type,
                    description,
                    patient_notes,
                    cancer_type_id,
                    str(document.id)
                ]
            )
            
            # Check result
            rows_affected = cursor.rowcount
            if rows_affected != 1:
                return JsonResponse({"error": f"Update affected {rows_affected} rows instead of 1"}, status=500)
            
            # Also update the object for consistency
            document.title = title
            document.document_type = document_type
            document.description = description
            document.patient_notes = patient_notes
            document.cancer_type = cancer_type
            
            # Get fresh data to verify the update
            cursor.execute(
                f"""
                SELECT title, document_type, description, patient_notes, cancer_type_id
                FROM {table_name}
                WHERE id = %s
                """,
                [str(document.id)]
            )
            
            db_data = cursor.fetchone()
            if not db_data:
                return JsonResponse({"error": "Failed to verify update - document not found"}, status=500)
            
            # Verify all fields match
            db_title, db_doctype, db_description, db_notes, db_cancer_type_id = db_data
            
            # Return success response with verified data
            return JsonResponse({
                "success": True,
                "message": "Document updated successfully",
                "data": {
                    "id": str(document.id),
                    "title": db_title,
                    "document_type": db_doctype,
                    "description": db_description,
                    "patient_notes": db_notes,
                    "cancer_type": db_cancer_type_id,
                }
            })
            
        except Exception as e:
            logger.error(f"Error during direct SQL update: {str(e)}")
            return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in update_document_data: {str(e)}")
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

@login_required
def get_document_data(request, document_id):
    """API endpoint to get document data for verification purposes."""
    # Use a direct database query to ensure we get the most up-to-date data
    from django.db import connection

    # First check if the user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    # Get the document
    document = get_object_or_404(MedicalDocument, id=document_id)

    # Security check - only the patient, the assigned doctor, or an admin can view
    if not (hasattr(request.user, 'is_administrator') and request.user.is_administrator() or
            request.user == document.patient or
            (document.patient and document.patient.assigned_doctor == request.user)):
        return JsonResponse({"error": "Access denied"}, status=403)

    # Log request details
    logger.info(f"Document data request for ID {document_id} by user {request.user.id}")

    try:
        # Fetch the document data directly from the database to bypass any caching
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, title, document_type, description, patient_notes, cancer_type_id, uploaded_at
            FROM medical_medicaldocument
            WHERE id = %s
            """,
            [str(document_id)]
        )
        doc_data = cursor.fetchone()

        if not doc_data:
            logger.error(f"Document {document_id} not found in database during verification")
            return JsonResponse({"error": "Document not found"}, status=404)

        # Unpack the query results
        id_str, title, document_type, description, patient_notes, cancer_type_id, uploaded_at = doc_data

        # Ensure we don't have None values in strings
        title = title or ""
        document_type = document_type or ""
        description = description or ""
        patient_notes = patient_notes or ""

        # Log what we're returning
        logger.info(f"Returning verification data for document {document_id}:")
        logger.info(f"  title: '{title}'")
        logger.info(f"  document_type: '{document_type}'")
        logger.info(f"  description: '{description}'")
        logger.info(f"  patient_notes: '{patient_notes}'")
        logger.info(f"  cancer_type: {cancer_type_id if cancer_type_id else 'None'}")

        # Additional step: Ensure patient record exists if cancer_type_id is present
        patient_record_created = False
        treatment_copied = False
        if document.patient and cancer_type_id:
            patient = document.patient

            # Get recommended_treatment if it exists on the document
            recommended_treatment = None
            try:
                # Check if the field exists in the database schema
                cursor = connection.cursor()
                cursor.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name='medical_medicaldocument' AND column_name='recommended_treatment'
                    """
                )
                if cursor.fetchone():
                    # Get the recommended_treatment value directly from the field
                    cursor.execute(
                        """
                        SELECT recommended_treatment FROM medical_medicaldocument WHERE id = %s
                        """,
                        [str(document_id)]
                    )
                    result = cursor.fetchone()
                    if result and result[0]:
                        recommended_treatment = result[0]
                        logger.info(f"Found recommended_treatment from field: {recommended_treatment}")

                # If no recommended_treatment value was found, try to extract it from ai_analysis_json
                if not recommended_treatment or (isinstance(recommended_treatment, str) and recommended_treatment.strip() == ""):
                    # Check if ai_analysis_json field exists
                    cursor.execute(
                        """
                        SELECT column_name FROM information_schema.columns
                        WHERE table_name='medical_medicaldocument' AND column_name='ai_analysis_json'
                        """
                    )
                    if cursor.fetchone():
                        # Get the ai_analysis_json
                        cursor.execute(
                            """
                            SELECT ai_analysis_json FROM medical_medicaldocument WHERE id = %s
                            """,
                            [str(document_id)]
                        )
                        result = cursor.fetchone()
                        if result and result[0]:
                            try:
                                import json
                                # Convert from JSON if it's a string
                                ai_data = None
                                if isinstance(result[0], str):
                                    ai_data = json.loads(result[0])
                                else:
                                    ai_data = result[0]

                                # Extract recommended_treatment if available
                                if ai_data and 'recommended_treatment' in ai_data and ai_data['recommended_treatment'] != "Not specified":
                                    recommended_treatment = ai_data['recommended_treatment']
                                    logger.info(f"Extracted recommended_treatment from AI analysis: {recommended_treatment}")

                                    # Update the document field with this value
                                    cursor.execute(
                                        """
                                        UPDATE medical_medicaldocument
                                        SET recommended_treatment = %s
                                        WHERE id = %s
                                        """,
                                        [recommended_treatment, str(document_id)]
                                    )
                                    logger.info(f"Updated document recommended_treatment field with value from AI analysis")
                            except Exception as e:
                                logger.error(f"Error parsing AI analysis JSON: {str(e)}")
            except Exception as e:
                logger.error(f"Error checking for recommended_treatment: {str(e)}")

            try:
                # Check if patient record exists
                patient_record = PatientRecord.objects.get(patient=patient)
                # Update cancer type if needed
                if cancer_type_id and patient_record.cancer_type_id != cancer_type_id:
                    patient_record.cancer_type_id = cancer_type_id
                    patient_record.save(update_fields=['cancer_type'])
                    logger.info(f"Updated cancer type for patient {patient.id} to {cancer_type_id}")

                # Also copy recommended_treatment if available
                if recommended_treatment:
                    try:
                        # Check if field exists in the schema
                        cursor.execute(
                            """
                            SELECT column_name FROM information_schema.columns
                            WHERE table_name='medical_patientrecord' AND column_name='recommended_treatment'
                            """
                        )
                        if cursor.fetchone():
                            # Update the field via raw SQL to be safe
                            cursor.execute(
                                """
                                UPDATE medical_patientrecord
                                SET recommended_treatment = %s
                                WHERE id = %s
                                """,
                                [recommended_treatment, patient_record.id]
                            )
                            treatment_copied = True
                            logger.info(f"Copied recommended_treatment to patient record: {recommended_treatment}")
                    except Exception as e:
                        logger.error(f"Error copying recommended_treatment to record: {str(e)}")

            except PatientRecord.DoesNotExist:
                # Create new patient record
                try:
                    cancer_type = CancerType.objects.get(id=cancer_type_id)

                    # Check if recommended_treatment field exists in schema
                    has_treatment_field = False
                    try:
                        cursor.execute(
                            """
                            SELECT column_name FROM information_schema.columns
                            WHERE table_name='medical_patientrecord' AND column_name='recommended_treatment'
                            """
                        )
                        has_treatment_field = bool(cursor.fetchone())
                    except Exception as e:
                        logger.error(f"Error checking patientrecord schema: {str(e)}")

                    # Create record differently based on schema
                    if has_treatment_field and recommended_treatment:
                        # Use raw SQL to create the record with treatment, including a UUID for the ID
                        import uuid
                        new_uuid = uuid.uuid4()

                        # Include all required fields with NOT NULL constraints
                        # Check if we can extract cancer stage from AI analysis
                        cancer_stage_text = ''
                        try:
                            # Try to get stage from recommended_treatment string if it contains "Stage"
                            if 'Stage' in recommended_treatment:
                                import re
                                stage_match = re.search(r'Stage\s+([^\s:]+)', recommended_treatment)
                                if stage_match:
                                    cancer_stage_text = f"Stage {stage_match.group(1)}"
                                    logger.info(f"Extracted cancer stage from treatment: {cancer_stage_text}")
                        except Exception as e:
                            logger.error(f"Error extracting cancer stage: {str(e)}")

                        cursor.execute(
                            """
                            INSERT INTO medical_patientrecord
                            (id, patient_id, diagnosis_date, cancer_type_id, recommended_treatment,
                             stage_grouping, vital_status, notes, created_at, updated_at, cancer_stage_text)
                            VALUES (%s, %s, %s, %s, %s,
                                   '', TRUE, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s)
                            RETURNING id
                            """,
                            [str(new_uuid), patient.id, datetime.date.today(), cancer_type.id,
                             recommended_treatment, cancer_stage_text]
                        )
                        record_id = cursor.fetchone()[0]
                        patient_record = PatientRecord.objects.get(id=record_id)
                        treatment_copied = True
                        logger.info(f"Created patient record with treatment: {recommended_treatment}")
                    else:
                        # Create normally via ORM
                        patient_record = PatientRecord(
                            patient=patient,
                            diagnosis_date=datetime.date.today(),
                            cancer_type=cancer_type
                        )
                        if has_treatment_field and recommended_treatment:
                            patient_record.recommended_treatment = recommended_treatment
                            treatment_copied = True
                        patient_record.save()

                    # Link document to patient record
                    document.patient_record = patient_record
                    document.save(update_fields=['patient_record'])

                    patient_record_created = True
                    logger.info(f"Created new patient record during API verification for patient {patient.id}")
                except Exception as e:
                    logger.error(f"Error creating patient record: {str(e)}")

        # Return only the fields needed for verification
        data = {
            "id": id_str,
            "title": title,
            "document_type": document_type,
            "description": description,
            "patient_notes": patient_notes,
            "cancer_type": cancer_type_id,
            "last_modified": uploaded_at.isoformat() if uploaded_at else None,
            "patient_record_created": patient_record_created,
            "treatment_copied": treatment_copied
        }

        # Add cache-busting headers to ensure fresh data
        response = JsonResponse(data)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'

        return response

    except Exception as e:
        logger.error(f"Error retrieving document data for verification: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
