"""
Forms for the accounts app.
"""
from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import date

from .models import Role, Language

User = get_user_model()


class SignupForm(UserCreationForm):
    """
    Form for user registration.
    """
    email = forms.EmailField(
        label=_('Email'),
        max_length=255,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Enter your email'),
        })
    )

    first_name = forms.CharField(
        label=_('First Name'),
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Enter your first name'),
        })
    )

    last_name = forms.CharField(
        label=_('Last Name'),
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Enter your last name'),
        })
    )

    date_of_birth = forms.DateField(
        label=_('Date of Birth'),
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'max': date.today().isoformat(),
        })
    )

    gender = forms.ChoiceField(
        label=_('Gender'),
        choices=User.GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
        })
    )

    phone_number = forms.CharField(
        label=_('Phone Number'),
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Enter your phone number'),
        })
    )

    language_code = forms.ChoiceField(
        label=_('Preferred Language'),
        choices=[('', _('Select language'))] + Language.LANGUAGE_CHOICES,
        required=True,
        initial=Language.ENGLISH,  # Set English as default
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
        })
    )
    
    role_name = forms.ChoiceField(
        label=_('Role'),
        choices=[
            ('', _('Select role')),
            (Role.PATIENT, _('Patient')),
            (Role.CLINICIAN, _('Clinician')),
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
        })
    )

    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Create a password'),
        })
    )

    password2 = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Confirm your password'),
        })
    )

    terms = forms.BooleanField(
        label=_('I agree to the Terms and Privacy Policy'),
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500',
        })
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'date_of_birth',
                  'gender', 'phone_number', 'language_code', 'role_name',
                  'password1', 'password2', 'terms']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set username field to use email
        self.fields['username'] = forms.CharField(required=False)

    def clean_date_of_birth(self):
        """
        Validate that the birth date is not in the future and user is at least 18.
        """
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = date.today()
            # Check if the birth date is in the future
            if dob > today:
                raise ValidationError(_('Date of birth cannot be in the future.'))

            # Calculate age
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

            # Check if the user is at least 18 years old
            if age < 18:
                raise ValidationError(_('You must be at least 18 years old to register.'))

        return dob

    def clean_email(self):
        """
        Validate that the email is unique.
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('This email is already registered.'))
        return email
        
    def clean_role_name(self):
        """
        Validate that the user is not trying to register as an administrator.
        """
        role_name = self.cleaned_data.get('role_name')
        if role_name == Role.ADMINISTRATOR:
            raise ValidationError(_('You cannot register as an administrator.'))
        return role_name

    def clean(self):
        """
        Set username to email and add patient role.
        """
        cleaned_data = super().clean()
        email = cleaned_data.get('email')

        # Set username to email if email is valid
        if email:
            cleaned_data['username'] = email

        return cleaned_data

    def save(self, commit=True):
        """
        Save the user with the selected role and language.
        """
        user = super().save(commit=False)
        user.username = self.cleaned_data.get('email')

        # Set language preference
        language_code = self.cleaned_data.get('language_code')
        if language_code:
            try:
                # Try to get the language first
                language = Language.objects.get(code=language_code)
            except Language.DoesNotExist:
                # If it doesn't exist, create it from the predefined choices
                language, _ = Language.objects.get_or_create(
                    code=language_code,
                    defaults={'code': language_code}
                )
            user.language = language
        else:
            # Default to English if no language is selected
            try:
                default_language = Language.objects.get(code=Language.ENGLISH)
                user.language = default_language
            except Language.DoesNotExist:
                default_language, _ = Language.objects.get_or_create(
                    code=Language.ENGLISH,
                    defaults={'code': Language.ENGLISH}
                )
                user.language = default_language

        # Set user role based on selection
        role_name = self.cleaned_data.get('role_name')
        if role_name:
            role, _ = Role.objects.get_or_create(name=role_name)
            user.role = role

        if commit:
            user.save()

        return user


class LoginForm(AuthenticationForm):
    """
    Form for user login.
    """
    username = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Enter your email'),
            'autofocus': True,
        })
    )

    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Enter your password'),
        })
    )

    remember_me = forms.BooleanField(
        label=_('Remember me'),
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500',
        })
    )

    error_messages = {
        'invalid_login': _('Please enter a correct email and password.'),
        'inactive': _('This account is inactive. Please verify your email.'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = _('Email')

    def clean(self):
        """
        Override to check email verification status.
        """
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            # Check if the user exists first
            try:
                user = User.objects.get(email=username)

                # If user isn't verified, but the password is correct
                if not user.is_email_verified:
                    # Check if password is valid before giving verification message
                    if user.check_password(password):
                        raise forms.ValidationError(
                            _('Please verify your email address before logging in.'),
                            code='unverified_email'
                        )
            except User.DoesNotExist:
                # Continue with regular authentication, which will fail anyway
                pass

            # Perform regular authentication
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )

            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login'
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class PasswordResetForm(forms.Form):
    """
    Form for password reset request.
    """
    email = forms.EmailField(
        label=_('Email'),
        max_length=255,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Enter your email'),
        })
    )

    def clean_email(self):
        """
        Validate that the email exists in the system.
        """
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise ValidationError(_('There is no user registered with this email address.'))
        return email


class PasswordResetConfirmForm(forms.Form):
    """
    Form for confirming password reset.
    """
    password1 = forms.CharField(
        label=_('New Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Enter new password'),
        })
    )

    password2 = forms.CharField(
        label=_('Confirm New Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': _('Confirm new password'),
        })
    )

    def clean_password2(self):
        """
        Validate that the passwords match.
        """
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError(_("The two password fields didn't match."))

        return password2


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user profile.
    """
    CANCER_SPECIALTIES = [
        ('', '-- Select specialty --'),
        ('Breast Cancer', 'Breast Cancer'),
        ('Lung Cancer', 'Lung Cancer'),
        ('Colorectal Cancer', 'Colorectal Cancer'),
        ('Prostate Cancer', 'Prostate Cancer'),
        ('Skin Cancer', 'Skin Cancer'),
        ('Brain Cancer', 'Brain Cancer'),
        ('Liver Cancer', 'Liver Cancer'),
        ('Pancreatic Cancer', 'Pancreatic Cancer'),
        ('Kidney Cancer', 'Kidney Cancer'),
        ('Blood Cancer', 'Blood Cancer'),
        ('Thyroid Cancer', 'Thyroid Cancer'),
        ('Uterine Cancer', 'Uterine Cancer'),
        ('Ovarian Cancer', 'Ovarian Cancer'),
        ('Bladder Cancer', 'Bladder Cancer'),
    ]
    
    specialty_name = forms.ChoiceField(
        label=_('Cancer Specialty'),
        choices=CANCER_SPECIALTIES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'id': 'specialty_select',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'gender', 'language', 'specialty_name']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'language': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Only show the specialty field for clinicians
        if self.instance and hasattr(self.instance, 'role') and self.instance.role:
            if not self.instance.is_clinician():
                if 'specialty_name' in self.fields:
                    del self.fields['specialty_name']