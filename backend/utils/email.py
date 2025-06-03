from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_templated_email(template_name, context, subject, recipient_list, from_email=None):
    """
    Send an email using a Django template.
    
    Args:
        template_name (str): Path to the email template
        context (dict): Context data for the template
        subject (str): Email subject
        recipient_list (list): List of recipients
        from_email (str, optional): Sender email. Defaults to settings.DEFAULT_FROM_EMAIL.
    
    Returns:
        bool: True if the email was sent successfully
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=recipient_list
    )
    email.attach_alternative(html_content, "text/html")
    
    try:
        sent = email.send()
        return sent > 0
    except Exception as e:
        # Log error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending email: {e}")
        return False


def send_verification_email(user, verification_url):
    """
    Send account verification email to a new user.
    
    Args:
        user: User model instance
        verification_url: URL for email verification
    
    Returns:
        bool: True if the email was sent successfully
    """
    context = {
        'user': user,
        'verification_url': verification_url,
    }
    
    return send_templated_email(
        template_name='email/verify_email.html',
        context=context,
        subject='Verify Your Email Address',
        recipient_list=[user.email]
    )


def send_password_reset_email(user, reset_url):
    """
    Send password reset email to a user.
    
    Args:
        user: User model instance
        reset_url: URL for password reset
    
    Returns:
        bool: True if the email was sent successfully
    """
    context = {
        'user': user,
        'reset_url': reset_url,
    }
    
    return send_templated_email(
        template_name='email/password_reset.html',
        context=context,
        subject='Reset Your Password',
        recipient_list=[user.email]
    )