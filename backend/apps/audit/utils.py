"""
Utility functions for the audit app.
"""
import json
from datetime import datetime


def json_serial(obj):
    """
    JSON serializer for objects not serializable by default.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def get_changed_fields(old_state, new_state):
    """
    Compare old and new states to find changed fields.

    Args:
        old_state (dict): Dictionary of field values before changes
        new_state (dict): Dictionary of field values after changes

    Returns:
        list: List of field names that have changed
    """
    changed = []

    # Skip password field changes since they're always hashed
    ignored_fields = ['password', 'last_login']

    for field, new_value in new_state.items():
        if field in ignored_fields:
            continue

        old_value = old_state.get(field)

        # Handle datetime objects
        if isinstance(new_value, datetime) and isinstance(old_value, datetime):
            if new_value.replace(microsecond=0) != old_value.replace(microsecond=0):
                changed.append(field)
            continue

        # Handle other types
        if new_value != old_value:
            changed.append(field)

    return changed


def get_related_object_changes(related_model_entries):
    """
    Format related model changes for audit logs.

    Args:
        related_model_entries: QuerySet of related model entries

    Returns:
        dict: Dictionary of changes suitable for audit logs
    """
    changes = {'added': [], 'updated': [], 'deleted': []}

    for entry in related_model_entries:
        action = entry.action.lower()
        if action in changes:
            changes[action].append({
                'id': str(entry.object_id),
                'changes': entry.changes
            })

    return changes


def anonymize_sensitive_data(changes):
    """
    Anonymize sensitive data in audit logs.

    Args:
        changes (dict): Dictionary of changes

    Returns:
        dict: Dictionary with sensitive data anonymized
    """
    if not changes:
        return changes

    sensitive_fields = [
        'password', 'password1', 'password2',
        'credit_card', 'ssn', 'social_security',
        'security_answer'
    ]

    result = {}

    # Process the original/old data
    if 'original' in changes:
        result['original'] = {}
        for field, value in changes['original'].items():
            if field.lower() in sensitive_fields:
                result['original'][field] = '********'
            else:
                result['original'][field] = value

    # Process the new data
    if 'new' in changes:
        result['new'] = {}
        for field, value in changes['new'].items():
            if field.lower() in sensitive_fields:
                result['new'][field] = '********'
            else:
                result['new'][field] = value

    # Process deleted data
    if 'deleted' in changes:
        result['deleted'] = {}
        for field, value in changes['deleted'].items():
            if field.lower() in sensitive_fields:
                result['deleted'][field] = '********'
            else:
                result['deleted'][field] = value

    return result


def format_changes_for_display(changes):
    """
    Format changes for human-readable display.

    Args:
        changes (dict): Dictionary of changes from audit log

    Returns:
        str: Human-readable description of changes
    """
    if not changes:
        return "No changes recorded"

    lines = []

    # Handle creation
    if 'new' in changes and 'original' not in changes:
        lines.append("Created new record with:")
        for field, value in changes['new'].items():
            lines.append(f"  • {field}: {value}")

    # Handle update
    elif 'original' in changes and 'new' in changes:
        lines.append("Updated the following fields:")
        for field in changes['new']:
            if field in changes['original']:
                old_val = changes['original'][field]
                new_val = changes['new'][field]
                if old_val != new_val:
                    lines.append(f"  • {field}: {old_val} → {new_val}")

    # Handle deletion
    elif 'deleted' in changes:
        lines.append("Deleted record with:")
        for field, value in changes['deleted'].items():
            lines.append(f"  • {field}: {value}")

    return "\n".join(lines)