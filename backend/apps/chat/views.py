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


# Admin views
@login_required
@role_required(['administrator'])
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
                    document.save()  # Save the document first to create the file
                    
                    # Force refresh from database to ensure it's saved
                    document.refresh_from_db()
                
                # Start document processing asynchronously
                try:
                    # Import threading to process in background
                    import threading
                    
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
                except Exception as process_error:
                    logger.error(f"Error starting document indexing {document.id}: {process_error}")
                    messages.warning(request, _(f"Document '{document.title}' uploaded but indexing could not be started."))
                
                # Return a response that forces a JavaScript reload
                response_html = f"""
                <html>
                <head>
                    <script>
                        // Force reload the page to show the new document
                        window.location.href = "{reverse('chat:admin_chat_documents')}?uploaded={document.id}&_t={int(time.time())}";
                    </script>
                </head>
                <body>
                    <p>Document uploaded successfully. Redirecting...</p>
                </body>
                </html>
                """
                return HttpResponse(response_html)
            except Exception as e:
                logger.error(f"Error processing document: {e}")
                messages.error(request, _("Error processing document. Please try again."))
        else:
            messages.error(request, _("Please correct the errors below."))
    else:
        form = ChatDocumentForm()

    # Get all documents - use select_related and prefetch_related for efficiency
    documents = ChatDocument.objects.select_related('uploaded_by', 'cancer_type').prefetch_related('chunks').all().order_by('-created_at')

    # Apply filters
    cancer_type_filter = request.GET.get('cancer_type')

    if cancer_type_filter:
        documents = documents.filter(cancer_type_id=cancer_type_filter)

    # Paginate
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Create HTML response matching website's Tailwind CSS styling
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <title>Chat Documents Admin - Medical Portal</title>
        {% if request.GET.uploaded %}
        <meta http-equiv="refresh" content="3;url={% url 'chat:admin_chat_documents' %}">
        {% endif %}
        <script src="https://cdn.tailwindcss.com/3.4.0"></script>
        <link rel="stylesheet" href="/static/css/main.css?v={% now 'U' %}">
        <link rel="stylesheet" href="/static/css/tailwind.css?v={% now 'U' %}">
        <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
        <script>
            function updateFileName(input) {
                const fileName = input.files[0] ? input.files[0].name : 'No file selected';
                document.getElementById('file-name-display').textContent = fileName;
                
                // Auto-fill title if empty
                const titleInput = document.querySelector('input[name="title"]');
                if (titleInput && !titleInput.value && input.files[0]) {
                    titleInput.value = fileName.replace(/\.[^/.]+$/, "");
                }
                
                // Auto-fill document type based on file extension
                const documentTypeInput = document.querySelector('input[name="document_type"]');
                if (documentTypeInput && input.files[0]) {
                    const extension = fileName.split('.').pop().toUpperCase();
                    documentTypeInput.value = extension;
                }
            }
        </script>
        <script>
            // Force reload if page was loaded from cache
            window.addEventListener('pageshow', function(event) {
                if (event.persisted || (window.performance && window.performance.navigation.type === 2)) {
                    window.location.reload(true);
                }
            });
            
            // Auto-refresh page when documents are being indexed
            document.addEventListener('DOMContentLoaded', function() {
                let refreshCount = 0;
                const maxRefreshes = 20; // Stop after 20 refreshes (about 1 minute)
                
                function shouldRefresh() {
                    // Check for documents that are being indexed
                    const pendingDocs = document.querySelectorAll('[data-indexing="true"]');
                    const yellowBorders = document.querySelectorAll('.border-l-yellow-400');
                    const blueBorders = document.querySelectorAll('.border-l-blue-400');
                    
                    // Check if we recently uploaded (within last minute)
                    const uploadedParam = new URLSearchParams(window.location.search).get('uploaded');
                    
                    console.log('Checking refresh conditions:', {
                        pendingDocs: pendingDocs.length,
                        yellowBorders: yellowBorders.length,
                        blueBorders: blueBorders.length,
                        uploaded: uploadedParam,
                        refreshCount: refreshCount
                    });
                    
                    // Refresh if:
                    // 1. There are documents being indexed (blue border) - ALWAYS refresh
                    // 2. There are pending documents (yellow) AND we just uploaded AND haven't refreshed too much
                    // Don't refresh if all documents are green (indexed)
                    if (blueBorders.length > 0) {
                        return true; // Documents actively being indexed
                    }
                    
                    if (uploadedParam && yellowBorders.length > 0 && refreshCount < 3) {
                        return true; // Just uploaded, waiting for indexing to start
                    }
                    
                    return false; // All done, no refresh needed
                }
                
                if (shouldRefresh()) {
                    // Update refresh count from URL or localStorage
                    const urlParams = new URLSearchParams(window.location.search);
                    refreshCount = parseInt(urlParams.get('_rc') || '0');
                    
                    console.log('Will refresh in 3 seconds... (refresh #' + (refreshCount + 1) + ')');
                    
                    // Show indicator
                    const indicator = document.createElement('div');
                    indicator.innerHTML = 'Checking indexing status in <span id="countdown">3</span>s...';
                    indicator.className = 'fixed bottom-4 right-4 bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg text-sm';
                    document.body.appendChild(indicator);
                    
                    // Countdown and refresh
                    let count = 3;
                    const countdownInterval = setInterval(function() {
                        count--;
                        const countdownEl = document.getElementById('countdown');
                        if (countdownEl) countdownEl.textContent = count;
                        if (count <= 0) {
                            clearInterval(countdownInterval);
                            // Add refresh count to URL
                            const url = new URL(window.location);
                            url.searchParams.set('_rc', refreshCount + 1);
                            window.location.href = url.toString();
                        }
                    }, 1000);
                } else {
                    // Clear the uploaded parameter if we're done refreshing
                    const url = new URL(window.location);
                    if (url.searchParams.has('uploaded') || url.searchParams.has('_rc')) {
                        url.searchParams.delete('uploaded');
                        url.searchParams.delete('_rc');
                        window.history.replaceState({}, '', url);
                        
                        // Show completion message if we were refreshing
                        if (refreshCount > 0 || uploadedParam) {
                            const completionMsg = document.createElement('div');
                            completionMsg.innerHTML = '✓ Indexing complete';
                            completionMsg.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg text-sm';
                            document.body.appendChild(completionMsg);
                            
                            // Remove after 3 seconds
                            setTimeout(function() {
                                completionMsg.remove();
                            }, 3000);
                        }
                    }
                    
                    console.log('No refresh needed - all documents are indexed or no recent upload');
                }
                
                // Handle form submission
                const uploadForm = document.getElementById('upload-form');
                if (uploadForm) {
                    uploadForm.addEventListener('submit', function(e) {
                        // Show loading state on submit button
                        const submitBtn = uploadForm.querySelector('button[type="submit"]');
                        if (submitBtn) {
                            submitBtn.disabled = true;
                            submitBtn.innerHTML = '<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Uploading...';
                        }
                    });
                }
            });
        </script>
    </head>
    <body class="bg-gray-50 min-h-screen flex flex-col">
        <!-- Header -->
        <header class="bg-white shadow-sm">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center h-16">
                    <div class="flex items-center">
                        <img src="/static/img/logo.svg" alt="Medical Portal" class="h-8 w-8 mr-3">
                        <span class="text-xl font-semibold text-gray-900">Medical Portal</span>
                    </div>
                    <nav class="hidden md:flex space-x-8">
                        <a href="{% url 'medical:admin_dashboard' %}" class="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                            Dashboard
                        </a>
                        <a href="{% url 'accounts:user_list' %}" class="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                            Users
                        </a>
                        <a href="{% url 'audit:logs' %}" class="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                            Audit Logs
                        </a>
                        <div class="relative" x-data="{ open: false }">
                            <button @click="open = !open" class="flex items-center text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                                {{ request.user.get_full_name|default:request.user.username }}
                                <svg class="ml-2 h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                                </svg>
                            </button>
                            <div x-show="open" @click.away="open = false" x-transition class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50">
                                <a href="{% url 'accounts:profile' %}" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                    My Profile
                                </a>
                                <hr class="my-1">
                                <a href="{% url 'accounts:logout' %}" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                    Sign out
                                </a>
                            </div>
                        </div>
                    </nav>
                    <div class="md:hidden">
                        <button type="button" class="text-gray-700 hover:text-gray-900">
                            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <main class="flex-grow pb-8">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">
                <h2 class="text-2xl font-semibold text-gray-900 mb-6">Chat Documents Management</h2>
                
                <!-- Upload Form Card -->
                <div class="bg-white shadow rounded-lg mb-8">
                    <div class="px-6 py-4 border-b border-gray-200 bg-gray-50">
                        <h3 class="text-lg font-medium text-gray-900">Upload New Document</h3>
                    </div>
                    <div class="p-6">
                        <form method="post" enctype="multipart/form-data" class="space-y-6" id="upload-form">
                            {% csrf_token %}
                            
                            <div class="grid grid-cols-1 gap-6 sm:grid-cols-2">
                                <!-- File Input -->
                                <div class="sm:col-span-2">
                                    <label class="block text-sm font-medium text-gray-700 mb-2">
                                        Document File <span class="text-red-500">*</span>
                                    </label>
                                    <div class="mt-1 flex items-center">
                                        <label for="id_file" class="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 cursor-pointer">
                                            <svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                                            </svg>
                                            Choose File
                                        </label>
                                        <input type="file" name="file" id="id_file" class="sr-only" required onchange="updateFileName(this)">
                                        <span id="file-name-display" class="ml-3 text-sm text-gray-600">No file selected</span>
                                    </div>
                                </div>
                                
                                <!-- Title Input -->
                                <div class="sm:col-span-2">
                                    <label for="id_title" class="block text-sm font-medium text-gray-700">
                                        Title <span class="text-red-500">*</span>
                                    </label>
                                    <input type="text" name="title" id="id_title" required
                                           class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                                           placeholder="Enter document title">
                                </div>
                                
                                <!-- Description -->
                                <div class="sm:col-span-2">
                                    <label for="id_description" class="block text-sm font-medium text-gray-700">
                                        Description
                                    </label>
                                    <textarea name="description" id="id_description" rows="3"
                                              class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                                              placeholder="Brief description of the document content"></textarea>
                                </div>
                                
                                <!-- Document Type -->
                                <div>
                                    <label for="id_document_type" class="block text-sm font-medium text-gray-700">
                                        Document Type <span class="text-red-500">*</span>
                                    </label>
                                    <input type="text" name="document_type" id="id_document_type" required readonly
                                           class="mt-1 block w-full border-gray-300 rounded-md shadow-sm bg-gray-100 text-gray-600 sm:text-sm"
                                           placeholder="Auto-detected from file">
                                </div>
                                
                                <!-- Cancer Type -->
                                <div>
                                    <label for="id_cancer_type" class="block text-sm font-medium text-gray-700">
                                        Cancer Type
                                    </label>
                                    <select name="cancer_type" id="id_cancer_type" 
                                            class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm">
                                        <option value="">Select Cancer Type</option>
                                        {% for ct in cancer_types %}
                                        <option value="{{ ct.id }}">{{ ct.name }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                            </div>
                            
                            <!-- Submit Buttons -->
                            <div class="flex justify-end space-x-3 pt-6 border-t border-gray-200">
                                <a href="{% url 'medical:admin_dashboard' %}" 
                                   class="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                                    Cancel
                                </a>
                                <button type="submit" 
                                        class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                                    Upload Document
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
                
                <!-- Documents List -->
                <div class="bg-white shadow-sm rounded-lg">
                    <div class="px-6 py-4 border-b border-gray-200">
                        <h3 class="text-lg font-medium text-gray-900">
                            Uploaded Documents 
                            <span class="text-sm text-gray-500">({{ page_obj.paginator.count }} total)</span>
                        </h3>
                    </div>
                    <div class="p-6">
                        {% if page_obj %}
                            <div class="space-y-4">
                                {% for doc in page_obj %}
                                <div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow {% if doc.indexed %}border-l-4 border-l-green-400{% elif doc.chunks.exists %}border-l-4 border-l-blue-400{% else %}border-l-4 border-l-yellow-400{% endif %} {% if request.GET.uploaded == doc.id|stringformat:'s' %}ring-2 ring-blue-500 bg-blue-50{% endif %}" {% if doc.chunks.exists and not doc.indexed %}data-indexing="true"{% endif %}>
                                    <div class="flex justify-between items-start">
                                        <div class="flex-1">
                                            <h4 class="text-lg font-medium text-gray-900">{{ doc.title }}</h4>
                                            <p class="text-gray-600 mt-1">{{ doc.description|truncatewords:20 }}</p>
                                            <div class="mt-2 text-sm text-gray-500 space-x-4">
                                                <span>Type: {{ doc.document_type }}</span>
                                                <span>•</span>
                                                <span>Cancer Type: {{ doc.cancer_type|default:"Not specified" }}</span>
                                                <span>•</span>
                                                <span>Uploaded: {{ doc.created_at|date:"M d, Y" }}</span>
                                                <span>•</span>
                                                <span>By: {{ doc.uploaded_by }}</span>
                                            </div>
                                        </div>
                                        <div class="ml-4 flex flex-col items-end space-y-2">
                                            {% if doc.indexed %}
                                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                    <svg class="mr-1.5 h-2 w-2 text-green-400" fill="currentColor" viewBox="0 0 8 8">
                                                        <circle cx="4" cy="4" r="3" />
                                                    </svg>
                                                    Indexed
                                                </span>
                                                {% if doc.indexed_at %}
                                                    <span class="text-xs text-gray-500">{{ doc.indexed_at|date:"M d, Y H:i" }}</span>
                                                {% endif %}
                                                <span class="text-xs text-gray-600">{{ doc.chunks.count }} chunks</span>
                                            {% elif doc.chunks.exists %}
                                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                                    <svg class="animate-spin mr-1.5 h-3 w-3 text-blue-600" fill="none" viewBox="0 0 24 24">
                                                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                    </svg>
                                                    Indexing...
                                                </span>
                                                <span class="text-xs text-gray-600">
                                                    <span class="font-semibold">{{ doc.chunks.count }}</span> chunks processed
                                                </span>
                                            {% else %}
                                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                                    <svg class="mr-1.5 h-2 w-2 text-yellow-400" fill="currentColor" viewBox="0 0 8 8">
                                                        <circle cx="4" cy="4" r="3" />
                                                    </svg>
                                                    Pending Index
                                                </span>
                                                <span class="text-xs text-gray-500">Ready to process</span>
                                            {% endif %}
                                        </div>
                                    </div>
                                    <div class="mt-4 flex gap-2">
                                        <a href="{% url 'chat:edit_chat_document' doc.id %}" 
                                           class="btn-secondary btn-sm">
                                            Edit
                                        </a>
                                        <form method="post" action="{% url 'chat:delete_chat_document' doc.id %}" 
                                              style="display: inline;" 
                                              onsubmit="return confirm('Are you sure you want to delete this document?')">
                                            {% csrf_token %}
                                            <button type="submit" class="btn-danger btn-sm">
                                                Delete
                                            </button>
                                        </form>
                                    </div>
                                </div>
                                {% endfor %}
                            </div>
                            
                            {% if page_obj.has_other_pages %}
                            <div class="mt-6 flex justify-center">
                                <nav class="flex items-center space-x-2">
                                    {% if page_obj.has_previous %}
                                    <a href="?page={{ page_obj.previous_page_number }}" 
                                       class="px-3 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50">
                                        Previous
                                    </a>
                                    {% endif %}
                                    
                                    <span class="px-3 py-2 text-sm text-gray-700">
                                        Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}
                                    </span>
                                    
                                    {% if page_obj.has_next %}
                                    <a href="?page={{ page_obj.next_page_number }}" 
                                       class="px-3 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50">
                                        Next
                                    </a>
                                    {% endif %}
                                </nav>
                            </div>
                            {% endif %}
                        {% else %}
                            <p class="text-gray-500 text-center py-8">No documents uploaded yet.</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </main>
        
        <!-- Footer -->
        <footer class="bg-white border-t border-gray-200 mt-auto">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                <div class="flex flex-col sm:flex-row justify-between items-center">
                    <div class="text-sm text-gray-500">
                        © {% now "Y" %} Medical Portal. All rights reserved.
                    </div>
                    <div class="flex space-x-6 mt-2 sm:mt-0">
                        <a href="#" class="text-sm text-gray-500 hover:text-gray-700">Privacy Policy</a>
                        <a href="#" class="text-sm text-gray-500 hover:text-gray-700">Terms of Service</a>
                        <a href="#" class="text-sm text-gray-500 hover:text-gray-700">Contact</a>
                    </div>
                </div>
            </div>
        </footer>
    </body>
    </html>
    """
    
    from django.template import Template, Context
    from django.template.context_processors import csrf
    
    template = Template(html)
    context_dict = {
        'form': form,
        'page_obj': page_obj,
        'cancer_types': CancerType.objects.filter(is_organ=True).order_by('name'),
        'request': request,
    }
    context_dict.update(csrf(request))
    context = Context(context_dict)
    
    response = HttpResponse(template.render(context))
    # Prevent caching to ensure fresh data
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


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