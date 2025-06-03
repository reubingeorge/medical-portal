"""
Views for the audit app.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils.html import escape

from apps.accounts.decorators import role_required
from .models import AuditLog


@login_required
@role_required(['administrator'])
def audit_logs(request):
    """
    Administrator view for audit logs.
    """
    # Check if middleware is active
    from .middleware import get_current_user, get_client_ip, get_user_agent
    middleware_user = get_current_user()

    # Get sort parameters
    sort_by = request.GET.get('sort', 'timestamp')
    sort_order = request.GET.get('order', 'desc')
    
    # Validate sort column
    valid_sort_columns = ['timestamp', 'model_name', 'action', 'user', 'object_id']
    if sort_by not in valid_sort_columns:
        sort_by = 'timestamp'  # Default sort

    # Build sort field with direction
    if sort_by == 'user':
        # Handle special case for user sorting
        sort_field = 'user__email' if sort_order == 'asc' else '-user__email'
    else:
        sort_field = sort_by if sort_order == 'asc' else f'-{sort_by}'
    
    logs = AuditLog.objects.all().select_related('user').order_by(sort_field)
    
    # Debug code to test if middleware is capturing user correctly
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Current user from middleware: {middleware_user}")
    logger.info(f"Current user from request: {request.user}")
    
    # Add debug log entries for testing
    if request.GET.get('debug') == '1':
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.CREATE,
            model_name='Debug',
            object_id='test',
            changes={'test': 'value'},
            ip_address=get_client_ip() or request.META.get('REMOTE_ADDR'),
            user_agent=get_user_agent() or request.META.get('HTTP_USER_AGENT')
        )
        
    # Initialize filter variables with default values
    search_query = request.GET.get('q', '')
    model_filter = request.GET.get('model', '')
    action_filter = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Filter params handling - Ensure values aren't 'None' strings
    if model_filter == 'None' or not model_filter:
        model_filter = ''
        
    if action_filter == 'None' or not action_filter:
        action_filter = ''
        
    if user_filter == 'None' or not user_filter:
        user_filter = ''
        
    if start_date == 'None' or not start_date:
        start_date = ''
        
    if end_date == 'None' or not end_date:
        end_date = ''
    
    # Check if we should fix user associations
    from apps.accounts.models import User
    if request.GET.get('fix_users') == '1':
        # Get admin user for special fixes
        admin_user = User.objects.filter(email='admin@example.com').first()
        
        # 1. Fix logs without users where model_name is accounts.User
        for log in AuditLog.objects.filter(user__isnull=True, model_name='accounts.User'):
            try:
                user_id = log.object_id
                if user_id and user_id.isdigit():
                    user = User.objects.filter(id=user_id).first()
                    if user:
                        log.user = user
                        log.save(update_fields=['user'])
                        logger.info(f"Fixed user association for log ID {log.id}")
            except Exception as e:
                logger.error(f"Error fixing user association: {e}")
        
        # 2. Special handling for admin user in changes
        if admin_user:
            # Find logs that mention admin in changes but have no user
            for log in AuditLog.objects.filter(user__isnull=True):
                try:
                    if log.changes and isinstance(log.changes, dict):
                        # Check if changes contain admin email
                        changes_str = str(log.changes)
                        if 'admin@example.com' in changes_str:
                            log.user = admin_user
                            log.save(update_fields=['user'])
                            logger.info(f"Fixed admin user association for log ID {log.id} based on changes content")
                except Exception as e:
                    logger.error(f"Error fixing admin association: {e}")
        
        # 3. Fix all User model actions without user (likely admin actions)
        if admin_user:
            # Find logs for User model with no user assigned (likely admin user actions)
            admin_assigned_count = 0
            for log in AuditLog.objects.filter(user__isnull=True, model_name='accounts.User'):
                try:
                    log.user = admin_user
                    log.save(update_fields=['user'])
                    admin_assigned_count += 1
                except Exception as e:
                    logger.error(f"Error fixing admin user actions: {e}")
            
            if admin_assigned_count > 0:
                logger.info(f"Assigned {admin_assigned_count} User model actions to admin user")
    
    # Search functionality
    if search_query:
        logs = logs.filter(
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(model_name__icontains=search_query) |
            Q(action__icontains=search_query) |
            Q(object_id__icontains=search_query)
        )
    
    # Filter by model
    if model_filter and model_filter != 'None':
        logs = logs.filter(model_name=model_filter)
    
    # Filter by action
    if action_filter and action_filter != 'None':
        logs = logs.filter(action=action_filter)
    
    # Filter by user
    if user_filter and user_filter != 'None':
        try:
            # Make sure it's a valid ID before filtering
            int(user_filter)  # This will raise ValueError if not an integer
            logs = logs.filter(user_id=user_filter)
        except ValueError:
            # If it's not a valid ID, don't apply the filter
            pass
    
    # Filter by date range
    if start_date and start_date != 'None':
        logs = logs.filter(timestamp__date__gte=start_date)
    
    if end_date and end_date != 'None':
        logs = logs.filter(timestamp__date__lte=end_date)
    
    # Get unique model names and actions for filter dropdowns
    model_names = AuditLog.objects.values_list('model_name', flat=True).distinct().order_by('model_name')
    
    # Get unique users who have logs
    from apps.accounts.models import User
    users_with_logs = User.objects.filter(
        id__in=AuditLog.objects.values_list('user_id', flat=True).distinct()
    ).order_by('email')
    
    # Pagination
    items_per_page = int(request.GET.get('size', 20))
    paginator = Paginator(logs, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'model_names': model_names,
        'action_choices': AuditLog.ACTION_CHOICES,
        'users_with_logs': users_with_logs,
        'search_query': search_query,
        'model_filter': model_filter,
        'action_filter': action_filter,
        'user_filter': user_filter,
        'start_date': start_date,
        'end_date': end_date,
        'items_per_page': items_per_page,
        'sort_by': sort_by,
        'sort_order': sort_order,
    }
    
    if request.htmx:
        if 'page' in request.GET or 'q' in request.GET or 'size' in request.GET or 'sort' in request.GET:
            return render(request, 'audit/partials/logs_list.html', context)
    
    return render(request, 'audit/logs.html', context)