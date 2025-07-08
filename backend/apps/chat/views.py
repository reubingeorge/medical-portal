"""
Views for the chat app.
"""
import json
import logging
import os
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.db.transaction import atomic

from apps.accounts.decorators import role_required
from apps.medical.models import CancerType

from .models import ChatDocument, ChatSession, ChatMessage, ChatFeedback
from .forms import ChatDocumentForm, ChatFeedbackForm, ChatInputForm, ChatDocumentEditForm
from .services import chat_service

logger = logging.getLogger(__name__)


@login_required
@require_GET
def chat_interface(request):
    """
    Main chat interface view.
    """
    from datetime import datetime, timedelta

    # Get active sessions for navbar
    all_sessions = ChatSession.objects.filter(
        user=request.user,
        active=True
    ).order_by('-updated_at')

    # Get today's date
    today = timezone.now().date()

    # Split sessions into today and previous
    today_sessions = []
    previous_sessions = []

    for session in all_sessions[:20]:  # Limit to 20 most recent sessions
        if session.created_at.date() == today:
            today_sessions.append(session)
        else:
            previous_sessions.append(session)

    # Get or create current session
    current_session_id = request.GET.get('session')
    current_session = None

    if current_session_id:
        current_session = get_object_or_404(
            ChatSession,
            id=current_session_id,
            user=request.user
        )
    else:
        # Get most recent session or create new one
        current_session = chat_service.create_or_continue_session(request.user)

    # Get messages for current session
    messages = ChatMessage.objects.filter(
        session=current_session
    ).order_by('created_at')

    context = {
        'today_sessions': today_sessions,
        'previous_sessions': previous_sessions,
        'current_session': current_session,
        'messages': messages,
        'form': ChatInputForm(),
    }

    return render(request, 'chat/interface.html', context)


@login_required
@require_POST
def chat_message(request):
    """
    Handle new chat messages.
    """
    logger.info(f"Received chat request: {request.POST}")
    form = ChatInputForm(request.POST)

    if form.is_valid():
        message_text = form.cleaned_data['message']
        logger.info(f"Valid message received: {message_text}")

        # Generate response
        try:
            logger.info("Calling generate_response...")
            response_text, assistant_message = chat_service.generate_response(
                request.user, message_text
            )
            logger.info(f"Response generated: {response_text[:100]}...")

            if request.htmx:
                # Render only the AI response since the user message is displayed immediately by JavaScript
                context = {
                    'assistant_message': response_text,
                    'message_id': str(assistant_message.id),
                }
                return render(request, 'chat/partials/ai_message.html', context)

            # JSON response for AJAX
            return JsonResponse({
                'status': 'success',
                'response': response_text,
                'message_id': str(assistant_message.id),
            })

        except Exception as e:
            logger.error(f"Error generating chat response: {e}")

            if request.htmx:
                return HttpResponse(
                    _("I'm sorry, an error occurred while processing your request."),
                    status=500
                )

            return JsonResponse({
                'status': 'error',
                'error': _("An error occurred while processing your request."),
            }, status=500)
    else:
        logger.error(f"Form validation failed: {form.errors}")
        
        if request.htmx:
            return HttpResponse(
                _("Please enter a valid message."),
                status=400
            )

        return JsonResponse({
            'status': 'error',
            'error': _("Please enter a valid message."),
            'errors': form.errors
        }, status=400)


@login_required
@require_POST
def chat_feedback(request):
    """
    Handle feedback on chat responses.
    """
    form = ChatFeedbackForm(request.POST)

    if form.is_valid():
        helpful = form.cleaned_data['helpful']
        comment = form.cleaned_data.get('comment', '')
        message_id = request.POST.get('message_id')

    try:
        message = get_object_or_404(ChatMessage, id=message_id)

        # Check if feedback already exists
        existing_feedback = ChatFeedback.objects.filter(message=message).first()

        if existing_feedback:
            # Update existing feedback
            existing_feedback.helpful = helpful
            existing_feedback.comment = comment
            existing_feedback.save()
        else:
            # Create new feedback
            ChatFeedback.objects.create(
                message=message,
                helpful=helpful,
                comment=comment
            )

        if request.htmx:
            return HttpResponse(
                _("Thank you for your feedback!"),
                headers={"HX-Trigger": "feedbackSubmitted"}
            )

        return JsonResponse({
            'status': 'success',
            'message': _("Thank you for your feedback!"),
        })

    except Exception as e:
        logger.error(f"Error saving feedback: {e}")

        if request.htmx:
            return HttpResponse(
                _("An error occurred while saving your feedback."),
                status=500
            )

        return JsonResponse({
            'status': 'error',
            'error': _("An error occurred while saving your feedback."),
        }, status=500)


@login_required
@require_GET
def chat_history(request):
    """
    View for chat history.
    """
    search_query = request.GET.get('q', '')
    filter_type = request.GET.get('filter', 'all')

    # Base query
    sessions = ChatSession.objects.filter(
        user=request.user,
        active=True
    ).order_by('-updated_at')

    # Apply filters
    if filter_type == 'today':
        today = timezone.now().date()
        sessions = sessions.filter(updated_at__date=today)
    elif filter_type == 'week':
        week_ago = timezone.now() - timezone.timedelta(days=7)
        sessions = sessions.filter(updated_at__gte=week_ago)
    elif filter_type == 'month':
        month_ago = timezone.now() - timezone.timedelta(days=30)
        sessions = sessions.filter(updated_at__gte=month_ago)

    # Apply search if provided
    if search_query:
        sessions = sessions.filter(
            Q(title__icontains=search_query) |
            Q(messages__content__icontains=search_query)
        ).distinct()

    # Paginate results
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'filter_type': filter_type,
    }

    return render(request, 'chat/history.html', context)


@login_required
@require_GET
def view_session(request, session_id):
    """
    View a specific chat session.
    """
    session = get_object_or_404(
        ChatSession,
        id=session_id,
        user=request.user
    )

    messages = ChatMessage.objects.filter(
        session=session
    ).order_by('created_at')

    context = {
        'session': session,
        'messages': messages,
        'form': ChatInputForm(),
    }

    if request.htmx:
        return render(request, 'chat/partials/session_messages.html', context)

    return render(request, 'chat/view_session.html', context)


@login_required
def test_chat(request):
    """
    Simple test view to debug chat issues.
    """
    if request.method == 'POST':
        message = request.POST.get('message', 'Test message')
        logger.info(f"Test chat received: {message}")

        try:
            # Direct response for testing
            return HttpResponse(f"""
                <div class="message-row ai">
                    <div class="avatar ai">AI</div>
                    <div class="message-bubble">Test response to: {message}</div>
                </div>
                <div id="typing-indicator" class="message-row ai typing-indicator" style="display: none;">
                    <div class="avatar ai">AI</div>
                    <div class="message-bubble">
                        <div class="typing-indicator show">
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                        </div>
                    </div>
                </div>
            """)
        except Exception as e:
            logger.error(f"Test chat error: {e}")
            return HttpResponse(f"Error: {e}", status=500)

    return HttpResponse("GET request not supported", status=405)


@login_required
def test_chat_page(request):
    """
    Test chat page for debugging.
    """
    return render(request, 'chat/test_chat.html')


@login_required
@require_POST
def create_session(request):
    """
    Create a new chat session.
    """
    title = request.POST.get('title', '')

    if not title:
        title = f"Chat {timezone.now().strftime('%Y-%m-%d %H:%M')}"

    session = ChatSession.objects.create(
        user=request.user,
        title=title,
        active=True
    )

    if request.htmx:
        return redirect(reverse('chat:chat_interface') + f'?session={session.id}')

    return JsonResponse({
        'status': 'success',
        'session_id': str(session.id),
        'redirect': reverse('chat:chat_interface') + f'?session={session.id}',
    })


@login_required
@require_POST
def update_session(request, session_id):
    """
    Update a chat session (rename or archive).
    """
    session = get_object_or_404(
        ChatSession,
        id=session_id,
        user=request.user
    )

    title = request.POST.get('title')
    active = request.POST.get('active')

    if title is not None:
        session.title = title

    if active is not None:
        session.active = active == 'true'

    session.save()

    if request.htmx:
        return HttpResponse(
            _("Session updated successfully."),
            headers={"HX-Trigger": "sessionUpdated"}
        )

    return JsonResponse({
        'status': 'success',
        'message': _("Session updated successfully."),
    })


@login_required
@require_POST
def delete_session(request, session_id):
    """
    Delete a chat session and all its messages.
    """
    session = get_object_or_404(
        ChatSession,
        id=session_id,
        user=request.user
    )

    # Delete the session (this will cascade delete all messages)
    session.delete()

    if request.htmx:
        return HttpResponse(
            _("Session deleted successfully."),
            headers={"HX-Trigger": "sessionDeleted"}
        )

    return JsonResponse({
        'status': 'success',
        'message': _("Session deleted successfully."),
    })


# status updates
@login_required
@role_required(['administrator'])
def document_statuses(request):
    docs = ChatDocument.objects.select_related('cancer_type', 'uploaded_by').all()
    return JsonResponse({
        'documents': [
            {
                'id': doc.id,
                'title': doc.title,
                'indexed': doc.indexed,
                'chunk_count': doc.chunks.count(),
                'created_at': doc.created_at.isoformat(),
                'uploaded_by': str(doc.uploaded_by),
                'cancer_type': doc.cancer_type.name if doc.cancer_type else None,
            }
            for doc in docs
        ]
    })


# Admin views
def admin_chat_documents(request):
    """
    Admin interface for managing chat documents.
    """
    if request.method == 'POST':
        form = ChatDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with atomic():
                    document = form.save(commit=False)
                    document.uploaded_by = request.user
                    document.save()
                    document.refresh_from_db()
                import threading
                # Start background indexing
                def process_document_async(doc_id):
                    try:
                        # Re-fetch document in the thread to avoid database connection issues
                        from apps.chat.models import ChatDocument
                        doc = ChatDocument.objects.get(id=doc_id)
                        chat_service.process_document(doc)
                        logger.info(f"Document {doc_id} indexed successfully")
                    except Exception as e:
                        logger.error(f"Error indexing document {doc_id}: {e}")

                # Start processing in a background thread
                thread = threading.Thread(target=process_document_async, args=(str(document.id),))
                thread.daemon = True
                thread.start()

                messages.success(request, _(f"Document '{document.title}' uploaded. Indexing started in background."))

                return redirect(f"{reverse('chat:admin_chat_documents')}?uploaded={document.id}&_t={int(time.time())}")
            except Exception as e:
                logger.error(f"Error processing document: {e}")
                messages.error(request, _("Error processing document. Please try again."))
        else:
            messages.error(request, _("Please correct the errors below."))
    else:
        form = ChatDocumentForm()

    documents = ChatDocument.objects.select_related('uploaded_by', 'cancer_type').prefetch_related('chunks').order_by('-created_at')

    if cancer_type_filter := request.GET.get('cancer_type'):
        documents = documents.filter(cancer_type_id=cancer_type_filter)

    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "chat/admin/documents.html", {
        'form': form,
        'page_obj': page_obj,
        'cancer_types': CancerType.objects.filter(is_organ=True).order_by('name'),
    })


@login_required
@role_required(['administrator'])
@require_POST
def delete_chat_document(request, document_id):
    """
    Delete a chat document.
    """
    document = get_object_or_404(ChatDocument, id=document_id)
    document.delete()

    messages.success(request, _("Document deleted successfully."))

    return redirect('chat:admin_chat_documents')


@login_required
@role_required(['administrator'])
def edit_chat_document(request, document_id):
    """
    Edit a chat document.
    """
    document = get_object_or_404(ChatDocument, id=document_id)

    if request.method == 'POST':
        form = ChatDocumentEditForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, _("Document updated successfully."))
            return redirect('chat:admin_chat_documents')
    else:
        form = ChatDocumentEditForm(instance=document)

    context = {
        'form': form,
        'document': document,
    }

    return render(request, 'chat/admin/edit_document.html', context)


@login_required
@role_required(['administrator'])
def admin_chat_analytics(request):
    """
    Chat analytics dashboard.
    """
    # Get date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date:
        start_date = timezone.now() - timezone.timedelta(days=30)
    else:
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = timezone.now()
    else:
        end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()

    # Get analytics data
    total_sessions = ChatSession.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).count()

    total_messages = ChatMessage.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).count()

    unique_users = ChatSession.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).values('user').distinct().count()

    # Average messages per session
    avg_messages_per_session = 0
    if total_sessions > 0:
        avg_messages_per_session = total_messages / total_sessions

    # Most discussed topics (simple implementation)
    # This would require more sophisticated NLP analysis in production

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_sessions': total_sessions,
        'total_messages': total_messages,
        'unique_users': unique_users,
        'avg_messages_per_session': round(avg_messages_per_session, 1),
    }

    return render(request, 'chat/admin/analytics.html', context)


@login_required
@role_required(['administrator'])
def admin_chat_feedback(request):
    """
    View all chat feedback.
    """
    feedback_list = ChatFeedback.objects.all().order_by('-created_at')

    # Apply filters
    helpful_filter = request.GET.get('helpful')
    if helpful_filter == 'true':
        feedback_list = feedback_list.filter(helpful=True)
    elif helpful_filter == 'false':
        feedback_list = feedback_list.filter(helpful=False)

    # Paginate
    paginator = Paginator(feedback_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'helpful_filter': helpful_filter,
    }

    return render(request, 'chat/admin/feedback.html', context)
