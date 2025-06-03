"""
Simplified chat views
"""
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

from .models import ChatSession, ChatMessage
from .forms import ChatInputForm
from .services import chat_service

logger = logging.getLogger(__name__)


@login_required
def chat_interface(request):
    """
    Main chat interface - simplified version
    """
    # Get or create session
    session = chat_service.create_or_continue_session(request.user)
    
    # Get messages
    messages = ChatMessage.objects.filter(
        session=session
    ).order_by('created_at')[:50]  # Last 50 messages
    
    context = {
        'messages': messages,
        'session': session,
    }
    
    return render(request, 'chat/interface_new.html', context)


@login_required
@require_POST
def chat_message(request):
    """
    Handle chat messages - simplified version
    """
    form = ChatInputForm(request.POST)
    
    if form.is_valid():
        message_text = form.cleaned_data['message']
        
        try:
            # Generate response
            response_text, assistant_message = chat_service.generate_response(
                request.user, 
                message_text
            )
            
            # Return just the AI message HTML
            context = {
                'role': 'assistant',
                'content': response_text
            }
            
            return render(request, 'chat/partials/message.html', context)
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            
            # Return error message
            context = {
                'role': 'assistant',
                'content': 'Sorry, I encountered an error. Please try again.'
            }
            
            return render(request, 'chat/partials/message.html', context)
    
    # Return error for invalid form
    return HttpResponse("Invalid message", status=400)