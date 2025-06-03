"""
Tests for account models.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import Role, Language

User = get_user_model()


class UserModelTest(TestCase):
    """Test for the User model."""

    def setUp(self):
        self.admin_role = Role.objects.create(name=Role.ADMINISTRATOR)
        self.english = Language.objects.create(code=Language.ENGLISH)
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='User',
            role=self.admin_role,
            language=self.english,
            is_email_verified=True
        )

    def test_user_creation(self):
        """Test user creation."""
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.first_name, 'Test')
        self.assertEqual(self.user.last_name, 'User')
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.is_email_verified)
        self.assertEqual(self.user.get_full_name(), 'Test User')