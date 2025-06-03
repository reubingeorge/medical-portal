"""
Utility functions for the medical app.

This module provides utility functions for the medical app, including database operations,
file validation, and other helper functions.
"""
import logging
from typing import Dict, Optional, List, Any, Union, Tuple, Set

from django.conf import settings
from django.db.models import Model, QuerySet
from django.db import connection

from apps.accounts.models import Language

logger = logging.getLogger(__name__)


def get_language_by_code(code: str) -> Optional[Language]:
    """
    Get Language model instance by ISO 639-1 code.
    
    Args:
        code: ISO 639-1 language code (e.g., 'en', 'es', 'fr')
        
    Returns:
        Language instance or None if not found
    """
    try:
        return Language.objects.get(code=code)
    except Language.DoesNotExist:
        try:
            # Try with default language
            return Language.objects.get(code='en')
        except Language.DoesNotExist:
            # No languages in database
            return None
    except Exception as e:
        logger.error(f"Error getting language by code: {str(e)}")
        return None


def is_valid_pdf(file_obj) -> bool:
    """
    Check if a file is a valid PDF.
    
    Args:
        file_obj: File object to check
        
    Returns:
        Boolean indicating if file is a valid PDF
    """
    # Check file extension
    if not file_obj.name.lower().endswith('.pdf'):
        return False
        
    # Check file size (max 20MB)
    if file_obj.size > 20 * 1024 * 1024:
        return False
        
    # Check if file is not empty
    if file_obj.size == 0:
        return False
        
    return True
    
    
def check_column_exists(table_name: str, column_name: str) -> bool:
    """
    Check if a column exists in a database table.
    
    Args:
        table_name: Name of the database table
        column_name: Name of the column to check
        
    Returns:
        Boolean indicating if the column exists
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name=%s AND column_name=%s",
                [table_name, column_name]
            )
            return bool(cursor.fetchone())
    except Exception as e:
        logger.error(f"Error checking if column {column_name} exists in table {table_name}: {str(e)}")
        return False
        
        
def get_queryset_with_safe_fields(queryset: QuerySet, table_name: str, 
                                 required_fields: List[str] = None,
                                 optional_fields: List[str] = None) -> QuerySet:
    """
    Get a queryset with only fields that are guaranteed to exist in the database.
    This is useful when the database schema might have changed during deployment.
    
    Args:
        queryset: Initial queryset
        table_name: Name of the database table
        required_fields: List of field names that are required (will use defer if they don't exist)
        optional_fields: List of field names that are optional (will use only if they exist)
        
    Returns:
        QuerySet with only fields that exist in the database
    """
    if not required_fields:
        required_fields = []
    if not optional_fields:
        optional_fields = []
        
    try:
        # Get all existing columns for the table
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name=%s",
                [table_name]
            )
            existing_columns = {row[0] for row in cursor.fetchall()}
            
        # Check if all required fields exist
        all_required_exist = all(field in existing_columns for field in required_fields)
        
        # Filter optional fields to only include those that exist
        existing_optional_fields = [field for field in optional_fields if field in existing_columns]
        
        if all_required_exist and existing_optional_fields:
            # If all required fields exist and some optional fields exist, use only()
            return queryset.only(*(required_fields + existing_optional_fields))
        elif all_required_exist:
            # If all required fields exist but no optional fields, use only() with required fields
            return queryset.only(*required_fields)
        else:
            # If some required fields don't exist, use defer() for fields that don't exist
            non_existing_required = [field for field in required_fields if field not in existing_columns]
            return queryset.defer(*non_existing_required)
            
    except Exception as e:
        logger.error(f"Error getting safe queryset for {table_name}: {str(e)}")
        # Fallback to the original queryset
        return queryset


def can_view_document(user, document, doctor_only=False) -> bool:
    """
    Check if a user has permission to view a document.

    If doctor_only is True, only the assigned doctor can view the document.

    Otherwise, a user can view a document if any of the following conditions are met:
    1. The user is an administrator
    2. The user is the patient the document belongs to
    3. The user is the doctor assigned to the patient the document belongs to
    4. The user is the one who uploaded the document

    Args:
        user: User model instance
        document: MedicalDocument model instance
        doctor_only: Boolean indicating if only the assigned doctor should have access

    Returns:
        Boolean indicating if the user can view the document
    """
    # If doctor_only mode, only allow the assigned doctor
    if doctor_only:
        # Only the assigned doctor can see the document
        if document.patient and document.patient.assigned_doctor == user:
            return True
        return False

    # Administrator always has access
    if hasattr(user, 'is_administrator') and user.is_administrator():
        return True

    # Patient can see their own documents
    if user == document.patient:
        return True

    # Doctor can see their patients' documents
    if document.patient and document.patient.assigned_doctor == user:
        return True

    # Uploader can see the documents they uploaded
    if user == document.uploaded_by:
        return True

    # If none of the conditions are met, deny access
    return False