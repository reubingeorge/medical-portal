"""
Tests for the audit app.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.signals import user_logged_in, user_logged_out

from .models import AuditLog
from .middleware import AuditMiddleware, get_current_user, get_client_ip
from .utils import get_changed_fields, anonymize_sensitive_data

User = get_user_model()


class AuditMiddlewareTests(TestCase):
    """
    Tests for the AuditMiddleware.
    """

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.middleware = AuditMiddleware(lambda request: None)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

    def test_process_request_anonymous(self):
        """Test middleware with anonymous user."""
        request = self.factory.get('/')
        request.user = User()  # Anonymous user

        self.middleware.process_request(request)

        self.assertIsNone(get_current_user())
        self.assertEqual(get_client_ip(), '127.0.0.1')

    def test_process_request_authenticated(self):
        """Test middleware with authenticated user."""
        request = self.factory.get('/')
        request.user = self.user

        self.middleware.process_request(request)

        self.assertEqual(get_current_user(), self.user)
        self.assertEqual(get_client_ip(), '127.0.0.1')

    def test_get_client_ip_with_forwarded_for(self):
        """Test IP resolution with X-Forwarded-For header."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '192.168.1.1, 10.0.0.1'

        ip = self.middleware.get_client_ip(request)

        self.assertEqual(ip, '192.168.1.1')


class AuditLogModelTests(TestCase):
    """
    Tests for the AuditLog model.
    """

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        self.audit_log = AuditLog.objects.create(
            user=self.user,
            action=AuditLog.CREATE,
            model_name='auth.User',
            object_id=str(self.user.pk),
            changes={'new': {'username': 'testuser', 'email': 'test@example.com'}},
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0'
        )

    def test_audit_log_creation(self):
        """Test creating an audit log entry."""
        self.assertEqual(self.audit_log.user, self.user)
        self.assertEqual(self.audit_log.action, AuditLog.CREATE)
        self.assertEqual(self.audit_log.model_name, 'auth.User')
        self.assertEqual(self.audit_log.object_id, str(self.user.pk))
        self.assertEqual(
            self.audit_log.changes,
            {'new': {'username': 'testuser', 'email': 'test@example.com'}}
        )
        self.assertEqual(self.audit_log.ip_address, '127.0.0.1')
        self.assertEqual(self.audit_log.user_agent, 'Mozilla/5.0')

    def test_audit_log_str(self):
        """Test the string representation of an audit log entry."""
        expected = f"Create - auth.User - {self.audit_log.timestamp}"
        self.assertEqual(str(self.audit_log), expected)


class SignalTests(TestCase):
    """
    Tests for the audit signals.
    """

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.middleware = AuditMiddleware(lambda request: None)

    def test_create_signal(self):
        """Test that creating a model generates an audit log."""
        # Set up middleware context
        request = self.factory.get('/')
        self.middleware.process_request(request)

        # Create a user - this should trigger the post_save signal
        user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='newpassword'
        )

        # Check if audit log was created
        logs = AuditLog.objects.filter(
            model_name='accounts.User',
            object_id=str(user.pk),
            action=AuditLog.CREATE
        )

        self.assertEqual(logs.count(), 1)
        self.assertIn('new@example.com', str(logs.first().changes))

    def test_update_signal(self):
        """Test that updating a model generates an audit log."""
        # Create a user
        user = User.objects.create_user(
            username='updateuser',
            email='update@example.com',
            password='updatepassword'
        )

        # Clear audit logs
        AuditLog.objects.all().delete()

        # Set up middleware context
        request = self.factory.get('/')
        self.middleware.process_request(request)

        # Update the user
        user.email = 'updated@example.com'
        user.save()

        # Check if audit log was created
        logs = AuditLog.objects.filter(
            model_name='accounts.User',
            object_id=str(user.pk),
            action=AuditLog.UPDATE
        )

        self.assertEqual(logs.count(), 1)
        self.assertIn('update@example.com', str(logs.first().changes))
        self.assertIn('updated@example.com', str(logs.first().changes))

    def test_delete_signal(self):
        """Test that deleting a model generates an audit log."""
        # Create a user
        user = User.objects.create_user(
            username='deleteuser',
            email='delete@example.com',
            password='deletepassword'
        )

        user_id = user.pk

        # Clear audit logs
        AuditLog.objects.all().delete()

        # Set up middleware context
        request = self.factory.get('/')
        self.middleware.process_request(request)

        # Delete the user
        user.delete()

        # Check if audit log was created
        logs = AuditLog.objects.filter(
            model_name='accounts.User',
            object_id=str(user_id),
            action=AuditLog.DELETE
        )

        self.assertEqual(logs.count(), 1)
        self.assertIn('delete@example.com', str(logs.first().changes))

    def test_login_signal(self):
        """Test that login generates an audit log."""
        # Create a user
        user = User.objects.create_user(
            username='loginuser',
            email='login@example.com',
            password='loginpassword'
        )

        # Clear audit logs
        AuditLog.objects.all().delete()

        # Set up middleware context
        request = self.factory.get('/')
        self.middleware.process_request(request)

        # Simulate login
        user_logged_in.send(sender=User, request=request, user=user)

        # Check if audit log was created
        logs = AuditLog.objects.filter(
            model_name='accounts.User',
            object_id=str(user.pk),
            action=AuditLog.LOGIN
        )

        self.assertEqual(logs.count(), 1)

    def test_logout_signal(self):
        """Test that logout generates an audit log."""
        # Create a user
        user = User.objects.create_user(
            username='logoutuser',
            email='logout@example.com',
            password='logoutpassword'
        )

        # Clear audit logs
        AuditLog.objects.all().delete()

        # Set up middleware context
        request = self.factory.get('/')
        self.middleware.process_request(request)

        # Simulate logout
        user_logged_out.send(sender=User, request=request, user=user)

        # Check if audit log was created
        logs = AuditLog.objects.filter(
            model_name='accounts.User',
            object_id=str(user.pk),
            action=AuditLog.LOGOUT
        )

        self.assertEqual(logs.count(), 1)


class UtilsTests(TestCase):
    """
    Tests for the audit utility functions.
    """

    def test_get_changed_fields(self):
        """Test detecting changed fields between two states."""
        old_state = {
            'username': 'olduser',
            'email': 'old@example.com',
            'password': 'hashed_old_password',
            'first_name': 'Old',
            'last_name': 'User'
        }

        new_state = {
            'username': 'newuser',
            'email': 'old@example.com',  # unchanged
            'password': 'hashed_new_password',  # should be ignored
            'first_name': 'New',
            'last_name': 'User'  # unchanged
        }

        changed = get_changed_fields(old_state, new_state)

        # Should detect username and first_name changes but ignore password
        self.assertEqual(set(changed), {'username', 'first_name'})

    def test_anonymize_sensitive_data(self):
        """Test anonymizing sensitive data in changes."""
        changes = {
            'original': {
                'username': 'olduser',
                'password': 'should_be_hashed_anyway',
                'credit_card': '1234-5678-9012-3456',
                'regular_field': 'regular_value'
            },
            'new': {
                'username': 'newuser',
                'password': 'new_should_be_hashed_anyway',
                'credit_card': '9876-5432-1098-7654',
                'regular_field': 'new_regular_value'
            }
        }

        anonymized = anonymize_sensitive_data(changes)

        # Check sensitive fields are anonymized
        self.assertEqual(anonymized['original']['password'], '********')
        self.assertEqual(anonymized['original']['credit_card'], '********')
        self.assertEqual(anonymized['new']['password'], '********')
        self.assertEqual(anonymized['new']['credit_card'], '********')

        # Check regular fields are unchanged
        self.assertEqual(anonymized['original']['username'], 'olduser')
        self.assertEqual(anonymized['original']['regular_field'], 'regular_value')
        self.assertEqual(anonymized['new']['username'], 'newuser')
        self.assertEqual(anonymized['new']['regular_field'], 'new_regular_value')