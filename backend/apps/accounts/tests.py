"""
Tests for the accounts app.
"""
from datetime import timedelta
import uuid

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Role, Language, EmailVerification, PasswordReset

User = get_user_model()

# Simple test to verify test discovery
class SimpleTest(TestCase):
    """Simple test to verify the testing infrastructure"""
    
    def test_basic_addition(self):
        """Test that 1 + 1 equals 2"""
        self.assertEqual(1 + 1, 2)


class UserModelTests(TestCase):
    """
    Tests for the User model.
    """

    def setUp(self):
        """
        Set up test data.
        """
        # Create roles
        self.patient_role = Role.objects.create(name=Role.PATIENT)
        self.doctor_role = Role.objects.create(name=Role.CLINICIAN)
        self.admin_role = Role.objects.create(name=Role.ADMINISTRATOR)

        # Create languages
        self.english = Language.objects.create(code=Language.ENGLISH)
        self.spanish = Language.objects.create(code=Language.SPANISH)

        # Create users
        self.patient = User.objects.create_user(
            email='patient@example.com',
            username='patient',
            password='SecurePassword123!',
            first_name='Patient',
            last_name='User',
            role=self.patient_role,
            language=self.english,
            is_email_verified=True
        )

        self.doctor = User.objects.create_user(
            email='doctor@example.com',
            username='doctor',
            password='SecurePassword123!',
            first_name='Doctor',
            last_name='User',
            role=self.doctor_role,
            language=self.english,
            is_email_verified=True
        )

        self.admin = User.objects.create_user(
            email='admin@example.com',
            username='admin',
            password='SecurePassword123!',
            first_name='Admin',
            last_name='User',
            role=self.admin_role,
            language=self.english,
            is_email_verified=True
        )

    def test_user_role_methods(self):
        """
        Test the role checking methods on the User model.
        """
        self.assertTrue(self.patient.is_patient())
        self.assertFalse(self.patient.is_clinician())
        self.assertFalse(self.patient.is_administrator())

        self.assertFalse(self.doctor.is_patient())
        self.assertTrue(self.doctor.is_clinician())
        self.assertFalse(self.doctor.is_administrator())

        self.assertFalse(self.admin.is_patient())
        self.assertFalse(self.admin.is_clinician())
        self.assertTrue(self.admin.is_administrator())

    def test_user_str_method(self):
        """
        Test the __str__ method on the User model.
        """
        self.assertEqual(str(self.patient), 'Patient User (patient@example.com)')

    def test_get_full_name(self):
        """
        Test the get_full_name method on the User model.
        """
        self.assertEqual(self.patient.get_full_name(), 'Patient User')

    def test_get_role_display(self):
        """
        Test the get_role_display method on the User model.
        """
        self.assertEqual(self.patient.get_role_display(), str(self.patient_role))

        # Test user with no role
        user_no_role = User.objects.create_user(
            email='no_role@example.com',
            username='no_role',
            password='SecurePassword123!'
        )
        self.assertEqual(user_no_role.get_role_display(), 'No role assigned')


class AuthenticationTests(TestCase):
    """
    Tests for authentication views.
    """

    def setUp(self):
        """
        Set up test data.
        """
        self.client = Client()

        # Create roles
        self.patient_role = Role.objects.create(name=Role.PATIENT)

        # Create languages
        self.english = Language.objects.create(code=Language.ENGLISH)

        # Create verified user
        self.verified_user = User.objects.create_user(
            email='verified@example.com',
            username='verified',
            password='SecurePassword123!',
            first_name='Verified',
            last_name='User',
            role=self.patient_role,
            language=self.english,
            is_email_verified=True
        )

        # Create unverified user
        self.unverified_user = User.objects.create_user(
            email='unverified@example.com',
            username='unverified',
            password='SecurePassword123!',
            first_name='Unverified',
            last_name='User',
            role=self.patient_role,
            language=self.english,
            is_email_verified=False
        )

        # Create email verification
        self.token = uuid.uuid4().hex
        EmailVerification.objects.create(
            user=self.unverified_user,
            token=self.token,
            expires_at=timezone.now() + timedelta(days=1)
        )

    def test_login_success(self):
        """
        Test successful login.
        """
        response = self.client.post(reverse('login'), {
            'username': 'verified@example.com',
            'password': 'SecurePassword123!',
        })

        # Check redirect
        self.assertRedirects(response, reverse('dashboard_redirect'))

        # Check user is logged in
        user = response.wsgi_request.user
        self.assertTrue(user.is_authenticated)

        # Check JWT cookie
        self.assertIn('access_token', response.cookies)

    def test_login_unverified_user(self):
        """
        Test login with unverified user.
        """
        response = self.client.post(reverse('login'), {
            'username': 'unverified@example.com',
            'password': 'SecurePassword123!',
        })

        # Check for error message
        self.assertContains(response, 'Please verify your email')

        # Check user is not logged in
        user = response.wsgi_request.user
        self.assertFalse(user.is_authenticated)

    def test_login_invalid_credentials(self):
        """
        Test login with invalid credentials.
        """
        response = self.client.post(reverse('login'), {
            'username': 'verified@example.com',
            'password': 'WrongPassword123!',
        })

        # Check for error message
        self.assertContains(response, 'Please enter a correct email and password')

        # Check user is not logged in
        user = response.wsgi_request.user
        self.assertFalse(user.is_authenticated)

    def test_logout(self):
        """
        Test logout.
        """
        # Login first
        self.client.login(username='verified@example.com', password='SecurePassword123!')

        # Logout
        response = self.client.get(reverse('logout'))

        # Check redirect
        self.assertRedirects(response, reverse('login'))

        # Check user is logged out
        user = response.wsgi_request.user
        self.assertFalse(user.is_authenticated)

        # Check JWT cookie is removed
        self.assertEqual(response.cookies['access_token'].value, '')

    def test_email_verification(self):
        """
        Test email verification.
        """
        # Before verification
        self.assertFalse(self.unverified_user.is_email_verified)

        # Perform verification
        response = self.client.get(reverse('verify_email', kwargs={'token': self.token}))

        # Check for success message
        self.assertContains(response, 'successfully verified')

        # Refresh user from database
        self.unverified_user.refresh_from_db()

        # Check user is now verified
        self.assertTrue(self.unverified_user.is_email_verified)

        # Check verification record is marked as verified
        verification = EmailVerification.objects.get(token=self.token)
        self.assertTrue(verification.verified)

    def test_email_verification_invalid_token(self):
        """
        Test email verification with invalid token.
        """
        # Attempt verification with invalid token
        response = self.client.get(reverse('verify_email', kwargs={'token': 'invalid-token'}))

        # Check for 404 error
        self.assertEqual(response.status_code, 404)

        # Refresh user from database
        self.unverified_user.refresh_from_db()

        # Check user is still not verified
        self.assertFalse(self.unverified_user.is_email_verified)


class PasswordResetTests(TestCase):
    """
    Tests for password reset functionality.
    """

    def setUp(self):
        """
        Set up test data.
        """
        self.client = Client()

        # Create roles
        self.patient_role = Role.objects.create(name=Role.PATIENT)

        # Create languages
        self.english = Language.objects.create(code=Language.ENGLISH)

        # Create user
        self.user = User.objects.create_user(
            email='user@example.com',
            username='user',
            password='OldPassword123!',
            first_name='Test',
            last_name='User',
            role=self.patient_role,
            language=self.english,
            is_email_verified=True
        )

        # Create password reset
        self.token = uuid.uuid4().hex
        PasswordReset.objects.create(
            user=self.user,
            token=self.token,
            expires_at=timezone.now() + timedelta(days=1)
        )

    def test_password_reset_request(self):
        """
        Test password reset request.
        """
        response = self.client.post(reverse('password_reset'), {
            'email': 'user@example.com',
        })

        # Check redirect or success message
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reset link has been sent')

        # Check that a password reset was created
        self.assertTrue(PasswordReset.objects.filter(user=self.user).exists())

    def test_password_reset_confirm(self):
        """
        Test password reset confirmation.
        """
        # Submit new password
        response = self.client.post(
            reverse('password_reset_confirm', kwargs={'token': self.token}),
            {
                'password1': 'NewPassword123!',
                'password2': 'NewPassword123!',
            }
        )

        # Check for success message
        self.assertContains(response, 'password has been reset')

        # Check that the password was updated
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPassword123!'))

        # Check that the reset is marked as used
        reset = PasswordReset.objects.get(token=self.token)
        self.assertTrue(reset.used)

    def test_password_reset_invalid_token(self):
        """
        Test password reset with invalid token.
        """
        # Attempt reset with invalid token
        response = self.client.get(
            reverse('password_reset_confirm', kwargs={'token': 'invalid-token'})
        )

        # Check for 404 error
        self.assertEqual(response.status_code, 404)