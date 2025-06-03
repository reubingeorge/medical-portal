"""
Forms for the medical app.
"""
from django import forms
from django.db import models
from django.utils.translation import gettext_lazy as _
import os

from .models import (
    PatientRecord, MedicalDocument, ClinicianReview,
    PatientFeedback, CancerType, FAQ, FAQTranslation
)
from .utils import is_valid_pdf


class PatientRecordForm(forms.ModelForm):
    """
    Form for patient medical records.
    """
    # Added field for organ selection
    cancer_organ = forms.ModelChoiceField(
        queryset=CancerType.objects.filter(is_organ=True),
        required=False,
        label=_('Cancer Organ Type'),
        widget=forms.Select(
            attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'id': 'id_cancer_organ',
            }
        )
    )

    # The cancer_stage_text is now directly in the model
    
    class Meta:
        model = PatientRecord
        fields = [
            'cancer_type', 'diagnosis_date', 'cancer_stage_text',
            'stage_grouping', 'recommended_treatment', 'notes'
        ]
        widgets = {
            'diagnosis_date': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d'
            ),
            'recommended_treatment': forms.Textarea(
                attrs={'rows': 4,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'notes': forms.Textarea(
                attrs={'rows': 4,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'cancer_type': forms.Select(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                    'id': 'id_cancer_type',
                }
            ),
            'stage_grouping': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'cancer_stage_text': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                    'placeholder': _('e.g., Stage I, Stage II, etc.')}
            ),
        }
        
    def __init__(self, *args, **kwargs):
        super(PatientRecordForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        
        # Initially, cancer_type dropdown should be empty until an organ is selected
        self.fields['cancer_type'].queryset = CancerType.objects.none()
        self.fields['cancer_type'].required = True
        self.fields['cancer_organ'].required = True
        
        # No need to set initial value for cancer_stage_text as it's now part of the model
        
        # If we have an instance and it has a cancer type
        if instance and instance.cancer_type:
            if not instance.cancer_type.is_organ:
                # It's a subtype - set the parent organ in the organ dropdown
                self.initial['cancer_organ'] = instance.cancer_type.parent
                
                # Set the cancer_type queryset to include subtypes of the selected organ
                self.fields['cancer_type'].queryset = CancerType.objects.filter(
                    parent=instance.cancer_type.parent
                )
            else:
                # It's an organ type itself
                self.initial['cancer_organ'] = instance.cancer_type
                
                # Get subtypes for this organ
                subtypes = CancerType.objects.filter(parent=instance.cancer_type)
                
                if subtypes.exists():
                    # Show the subtypes in the cancer_type dropdown
                    self.fields['cancer_type'].queryset = subtypes
                else:
                    # No subtypes, so we'll need to use the organ as the cancer type too
                    self.fields['cancer_type'].queryset = CancerType.objects.filter(id=instance.cancer_type.id)
                    
        # Help text for the dropdowns
        self.fields['cancer_organ'].help_text = _("Select the primary organ affected by cancer")
        self.fields['cancer_type'].help_text = _("Select the specific cancer type within the organ")
    
    # No need for a custom save method as cancer_stage_text is now handled by the model


class MedicalDocumentForm(forms.ModelForm):
    """
    Form for uploading medical documents.
    AI will automatically fill out all fields from the document content.
    """
    class Meta:
        model = MedicalDocument
        fields = ['file']
        widgets = {
            'file': forms.FileInput(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                    'accept': '.pdf'
                }
            ),
        }

    def clean_file(self):
        """
        Validate file is a valid PDF document.
        """
        file = self.cleaned_data.get('file')

        if not file:
            raise forms.ValidationError(_('Please select a file to upload.'))
            
        # Check if it's a valid PDF
        if not is_valid_pdf(file):
            raise forms.ValidationError(_('Please upload a valid PDF document (maximum size: 20MB).'))

        return file


class MedicalDocumentReviewForm(forms.ModelForm):
    """
    Form for reviewing AI-analyzed medical documents and making adjustments.
    """
    # Added field for organ selection
    cancer_organ = forms.ModelChoiceField(
        queryset=CancerType.objects.filter(is_organ=True),
        required=False,
        label=_('Cancer Organ Type'),
        widget=forms.Select(
            attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'id': 'id_cancer_organ',
                'onchange': 'updateCancerTypes(this.value)',
            }
        )
    )
    
    def clean(self):
        """Validate the entire form and make sure all cancer type selections are valid"""
        cleaned_data = super().clean()
        
        # Get the selected organ and cancer type
        cancer_organ = cleaned_data.get('cancer_organ')
        cancer_type = cleaned_data.get('cancer_type')
        
        # If an organ is selected but no subtype, that might be ok in some cases
        # but we should validate that the organ exists
        if cancer_organ and not cancer_type:
            try:
                # Verify the organ exists
                CancerType.objects.get(id=cancer_organ.id, is_organ=True)
            except CancerType.DoesNotExist:
                self.add_error('cancer_organ', _("The selected organ type is not valid."))
        
        # If a cancer type is selected, validate it thoroughly
        if cancer_type:
            try:
                # Verify the cancer type exists and get a fresh instance
                valid_type = CancerType.objects.get(id=cancer_type.id)
                
                # Replace the selected instance with the valid one
                cleaned_data['cancer_type'] = valid_type
                
                # If it's a subtype, also validate its parent
                if not valid_type.is_organ and valid_type.parent:
                    try:
                        # Verify the parent exists
                        CancerType.objects.get(id=valid_type.parent.id, is_organ=True)
                    except CancerType.DoesNotExist:
                        self.add_error('cancer_type', _("The selected cancer type has an invalid parent organ."))
            except CancerType.DoesNotExist:
                self.add_error('cancer_type', _("The selected cancer type is not valid. Please select another option."))
        
        return cleaned_data
    
    class Meta:
        model = MedicalDocument
        fields = [
            'title', 'document_type', 'cancer_type',
            'description', 'patient_notes', 'recommended_treatment', 'language'
        ]
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'document_type': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'description': forms.Textarea(
                attrs={'rows': 3,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'patient_notes': forms.Textarea(
                attrs={'rows': 4,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'recommended_treatment': forms.Textarea(
                attrs={'rows': 4,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'cancer_type': forms.Select(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                    'id': 'id_cancer_type'
                }
            ),
            'language': forms.Select(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
        }
        
    def __init__(self, *args, **kwargs):
        super(MedicalDocumentReviewForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        
        # First, ensure we have a valid queryset that only includes existing cancer types
        # This prevents invalid IDs from being included in the dropdown options
        try:
            # Get all valid cancer types
            all_cancer_types = CancerType.objects.all()
            all_organ_types = CancerType.objects.filter(is_organ=True)
            
            # Update the queryset for both fields
            self.fields['cancer_type'].queryset = all_cancer_types
            self.fields['cancer_organ'].queryset = all_organ_types
            
            # Make cancer_type a required field for valid form submission
            self.fields['cancer_type'].required = True
            
            # Add required attribute to the widget
            self.fields['cancer_type'].widget.attrs['required'] = 'required'
        except Exception as e:
            print(f"Error setting up cancer type querysets: {e}")
        
        # If we have an instance with a cancer type
        if instance:
            # Try to get AI-predicted cancer organ type from the session
            request = self.initial.get('request')
            ai_analysis = None
            
            if hasattr(instance, 'ai_analysis_json') and instance.ai_analysis_json:
                try:
                    import json
                    ai_analysis = json.loads(instance.ai_analysis_json)
                except:
                    pass
            
            # If we have AI analysis with cancer_organ_type, try to match it
            organ_name = None
            if ai_analysis and 'cancer_organ_type' in ai_analysis and ai_analysis['cancer_organ_type'] != "Not specified":
                organ_name = ai_analysis['cancer_organ_type']
                
                # Try to find the organ by name
                try:
                    organ = CancerType.objects.filter(is_organ=True, name__iexact=organ_name).first()
                    if organ:
                        self.initial['cancer_organ'] = organ
                        
                        # Try to find the specific subtype
                        if 'cancer_type' in ai_analysis and ai_analysis['cancer_type'] != "Not specified":
                            cancer_subtype_name = ai_analysis['cancer_type']
                            # Look for the subtype by name or partial match
                            subtypes = CancerType.objects.filter(parent=organ)
                            
                            # Try exact match first
                            subtype = subtypes.filter(name__iexact=cancer_subtype_name).first()
                            if not subtype:
                                # Try partial match
                                for st in subtypes:
                                    if st.name.lower() in cancer_subtype_name.lower() or cancer_subtype_name.lower() in st.name.lower():
                                        subtype = st
                                        break
                                        
                            if subtype:
                                self.initial['cancer_type'] = subtype
                                
                        # Set the cancer_type dropdown to show subtypes of this organ
                        subtypes = CancerType.objects.filter(parent=organ)
                        if subtypes.exists():
                            self.fields['cancer_type'].queryset = subtypes
                        else:
                            # No subtypes, use the organ as the cancer type too
                            self.fields['cancer_type'].queryset = CancerType.objects.filter(id=organ.id)
                except Exception as e:
                    print(f"Error matching AI cancer organ type: {e}")
            
            # If we have an existing cancer type on the instance
            if instance.cancer_type:
                if instance.cancer_type.is_organ:
                    # It's an organ type
                    self.initial['cancer_organ'] = instance.cancer_type
                    
                    # Set the cancer_type dropdown to show subtypes of this organ
                    subtypes = CancerType.objects.filter(parent=instance.cancer_type)
                    if subtypes.exists():
                        self.fields['cancer_type'].queryset = subtypes
                    else:
                        # No subtypes, so we'll need to use the organ as the cancer type too
                        self.fields['cancer_type'].queryset = CancerType.objects.filter(id=instance.cancer_type.id)
                else:
                    # It's a subtype - set the parent organ in the organ dropdown
                    self.initial['cancer_organ'] = instance.cancer_type.parent
                    
                    # Set dropdown to show sibling subtypes
                    self.fields['cancer_type'].queryset = CancerType.objects.filter(
                        parent=instance.cancer_type.parent
                    )


class ClinicianReviewForm(forms.ModelForm):
    """
    Form for clinician reviews.
    """

    class Meta:
        model = ClinicianReview
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(
                attrs={'rows': 5,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
        }


class PatientFeedbackForm(forms.ModelForm):
    """
    Form for patient feedback.
    """

    class Meta:
        model = PatientFeedback
        fields = ['rating', 'comments']
        widgets = {
            'rating': forms.RadioSelect(
                attrs={'class': 'hidden peer'},
                choices=PatientFeedback.RATING_CHOICES
            ),
            'comments': forms.Textarea(
                attrs={'rows': 4,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                       'placeholder': _('Share your experience and suggestions...')}
            ),
        }


class CancerTypeForm(forms.ModelForm):
    """
    Form for cancer types.
    """

    class Meta:
        model = CancerType
        fields = ['name', 'description', 'parent', 'is_organ']
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'description': forms.Textarea(
                attrs={'rows': 3,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'parent': forms.Select(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'is_organ': forms.CheckboxInput(
                attrs={
                    'class': 'w-5 h-5 text-blue-600 rounded focus:ring-blue-500'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter parent choices to only include organ-level cancer types
        self.fields['parent'].queryset = CancerType.objects.filter(is_organ=True)
        
        # If editing an existing organ-level type, remove parent field
        instance = kwargs.get('instance')
        if instance and instance.is_organ:
            self.fields['parent'].widget = forms.HiddenInput()
            self.fields['parent'].required = False


# CancerStageForm removed since we're no longer using the CancerStage model


class FAQForm(forms.ModelForm):
    """
    Form for FAQs.
    """

    class Meta:
        model = FAQ
        fields = ['question_key', 'category']
        widgets = {
            'question_key': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'category': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
        }


class FAQTranslationForm(forms.ModelForm):
    """
    Form for FAQ translations.
    """

    class Meta:
        model = FAQTranslation
        fields = ['language', 'question', 'answer']
        widgets = {
            'language': forms.Select(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'question': forms.Textarea(
                attrs={'rows': 2,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'answer': forms.Textarea(
                attrs={'rows': 4,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
        }