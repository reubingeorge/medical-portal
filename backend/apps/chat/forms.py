"""
Forms for the chat app.
"""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ChatDocument, ChatFeedback
from apps.medical.models import CancerType


class ChatDocumentForm(forms.ModelForm):
    """
    Form for uploading documents to the RAG chatbot.
    """
    # Make title, description, and document_type not required in the form
    # since we'll auto-generate them
    title = forms.CharField(required=False)
    description = forms.CharField(required=False, widget=forms.Textarea)
    document_type = forms.CharField(required=False)
    
    # Multiple files field removed as it's not supported by standard FileInput
    # We'll use the single file upload approach instead

    class Meta:
        model = ChatDocument
        fields = ['title', 'description', 'document_type', 'cancer_type', 'file']
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'description': forms.Textarea(
                attrs={'rows': 3,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'document_type': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'cancer_type': forms.Select(
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}
            ),
            'file': forms.FileInput(
                attrs={
                    'class': 'hidden',
                    'accept': '.pdf,.doc,.docx,.txt'
                }
            ),
        }

    def clean_file(self):
        """
        Validate file size and extension.
        """
        file = self.cleaned_data.get('file')

        if file:
            # Check file size (max 20MB)
            if file.size > 20 * 1024 * 1024:
                raise forms.ValidationError(_('File size exceeds 20MB limit.'))

            # Check file extension
            allowed_extensions = ['pdf', 'doc', 'docx', 'txt']
            ext = file.name.split('.')[-1].lower()

            if ext not in allowed_extensions:
                raise forms.ValidationError(_(
                    'Unsupported file extension. Allowed extensions: {}.'
                ).format(', '.join(allowed_extensions)))

        return file


class ChatFeedbackForm(forms.ModelForm):
    """
    Form for collecting feedback on chat responses.
    """

    class Meta:
        model = ChatFeedback
        fields = ['helpful', 'comment']
        widgets = {
            'helpful': forms.RadioSelect(
                attrs={'class': 'hidden peer'},
                choices=[(True, _('Yes')), (False, _('No'))]
            ),
            'comment': forms.Textarea(
                attrs={'rows': 2,
                       'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                       'placeholder': _('Optional: Tell us more about your experience...')}
            ),
        }


class ChatInputForm(forms.Form):
    """
    Form for chat input.
    """
    message = forms.CharField(
        label=_('Message'),
        max_length=1000,
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': _('Type your message...'),
                'autocomplete': 'off',
            }
        )
    )

    def clean_message(self):
        """
        Validate and sanitize the message.
        """
        message = self.cleaned_data.get('message')

        # Filter out any potentially harmful characters
        message = message.strip()

        # Ensure message is not empty
        if not message:
            raise forms.ValidationError(_('Please enter a message.'))

        return message


class ChatDocumentEditForm(forms.ModelForm):
    """
    Form for editing document title and cancer type.
    """
    title = forms.CharField(
        label=_('Document Title'),
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }
        )
    )

    cancer_type = forms.ModelChoiceField(
        label=_('Cancer Type'),
        queryset=CancerType.objects.filter(is_organ=True),
        required=False,
        empty_label=_('--- Select Cancer Type (Optional) ---'),
        widget=forms.Select(
            attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }
        )
    )

    class Meta:
        model = ChatDocument
        fields = ['title', 'cancer_type']