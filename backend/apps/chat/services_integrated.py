"""
Integrated Advanced Chat Service with Complete RAG Pipeline
"""
import uuid
import time
import logging
from typing import Optional, Tuple, List, Dict
from datetime import datetime

from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import ChatDocument, ChatDocumentChunk, ChatSession, ChatMessage
from .prompts import PromptBuilder
from .services_advanced import AdvancedRAGService, RetrievalResult
from .document_processor_advanced import AdvancedDocumentProcessor
from .rag_cache import rag_cache, COMMON_MEDICAL_QUERIES
from .rag_monitor import rag_monitor, QueryMetrics

logger = logging.getLogger(__name__)


class IntegratedChatService:
    """
    Complete integrated chat service combining:
    - Advanced RAG with hybrid search and reranking
    - Intelligent caching with semantic similarity
    - Enhanced document processing with metadata
    - Comprehensive monitoring and analytics
    - Query expansion and confidence scoring
    """
    
    def __init__(self):
        # Initialize components
        self.rag_service = AdvancedRAGService()
        self.doc_processor = AdvancedDocumentProcessor()
        
        # Warm up cache on init
        self._warm_cache()
        
        logger.info("Integrated Chat Service initialized")
    
    def _warm_cache(self):
        """Warm up cache with common queries"""
        try:
            rag_cache.warm_cache(COMMON_MEDICAL_QUERIES)
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
    
    def process_document(self, document: ChatDocument) -> int:
        """
        Process document with advanced chunking and indexing
        """
        start_time = time.time()
        chunks_created = 0
        
        try:
            # Clear existing chunks
            document.chunks.all().delete()
            
            # Prepare metadata
            metadata = {
                "source": str(document.id),
                "title": document.title,
                "document_type": document.document_type,
                "cancer_type": document.cancer_type.name if document.cancer_type else None,
                "uploaded_by": document.uploaded_by.get_full_name() if document.uploaded_by else None,
                "created_at": document.created_at.isoformat()
            }
            
            # Process document with advanced processor
            processed_chunks = self.doc_processor.process_document(
                str(document.file.path),
                metadata
            )
            
            # Create chunk records and embeddings
            for i, chunk_doc in enumerate(processed_chunks):
                # Create chunk record
                chunk = ChatDocumentChunk.objects.create(
                    document=document,
                    chunk_index=i,
                    content=chunk_doc.page_content,
                    metadata=chunk_doc.metadata
                )
                
                # Add to vector store
                vector_id = self.rag_service.vector_store.add_documents(
                    [chunk_doc],
                    ids=[str(chunk.id)]
                )[0]
                
                # Update chunk with vector ID
                chunk.vector_id = vector_id
                chunk.save()
                
                chunks_created += 1
            
            # Update document status
            document.indexed = True
            document.indexed_at = timezone.now()
            document.save()
            
            # Log processing metrics
            processing_time = time.time() - start_time
            logger.info(
                f"Document {document.id} processed: "
                f"{chunks_created} chunks in {processing_time:.2f}s"
            )
            
            # Invalidate relevant cache entries
            if document.cancer_type:
                rag_cache.invalidate_cache(pattern=document.cancer_type.name)
            
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            # Mark document as failed
            document.indexed = False
            document.save()
            raise
        
        return chunks_created
    
    def generate_response(self, user, message_text: str) -> Tuple[str, ChatMessage]:
        """
        Generate response using the complete RAG pipeline
        """
        # Start monitoring
        query_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Track metrics
        metrics = QueryMetrics(
            query_id=query_id,
            query_text=message_text,
            user_id=str(user.id) if user else None,
            timestamp=datetime.now(),
            total_duration=0,
            retrieval_duration=0,
            reranking_duration=0,
            generation_duration=0,
            retrieval_count=0,
            rerank_count=0,
            confidence_score=0,
            fallback_used=False,
            cache_hit=False,
            cache_type=None,
            response_length=0,
            tokens_used=0
        )
        
        try:
            # Get or create session
            session = self._get_or_create_session(user)
            
            # Create prompt builder
            prompt_builder = PromptBuilder(
                patient=user,
                language=getattr(user, 'language', None)
            )
            
            # Check for emergency
            if self._is_emergency(message_text):
                response = prompt_builder.build_emergency_response()
                return self._save_and_return(session, message_text, response, metrics)
            
            # Check cache first
            cache_start = time.time()
            cached_response = rag_cache.get_cached_response(
                message_text,
                context=self._get_user_context(user)
            )
            
            if cached_response:
                metrics.cache_hit = True
                metrics.cache_type = cached_response.get('cache_type', 'exact')
                response = cached_response.get('content', '')
                metrics.confidence_score = cached_response.get('confidence', 0.8)
                
                return self._save_and_return(session, message_text, response, metrics)
            
            # Perform RAG retrieval
            retrieval_start = time.time()
            response_text, confidence, retrieval_metrics = self._perform_rag_retrieval(
                message_text,
                user,
                prompt_builder
            )
            
            # Update metrics
            metrics.retrieval_duration = retrieval_metrics.get('retrieval_time', 0)
            metrics.reranking_duration = retrieval_metrics.get('reranking_time', 0)
            metrics.generation_duration = retrieval_metrics.get('generation_time', 0)
            metrics.retrieval_count = retrieval_metrics.get('retrieval_count', 0)
            metrics.rerank_count = retrieval_metrics.get('rerank_count', 0)
            metrics.confidence_score = confidence
            metrics.fallback_used = retrieval_metrics.get('fallback_used', False)
            
            # Cache the response
            if not metrics.fallback_used and confidence > 0.6:
                rag_cache.cache_response(
                    message_text,
                    {
                        'content': response_text,
                        'confidence': confidence,
                        'cache_type': 'generated'
                    },
                    context=self._get_user_context(user)
                )
            
            return self._save_and_return(session, message_text, response_text, metrics)
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            
            # Create error response
            error_response = (
                "I apologize, but I encountered an error while processing your request. "
                "Please try again later or contact your healthcare provider if this is urgent."
            )
            
            # Update metrics
            metrics.fallback_used = True
            
            return self._save_and_return(session, message_text, error_response, metrics)
    
    def _perform_rag_retrieval(
        self, 
        message_text: str, 
        user,
        prompt_builder: PromptBuilder
    ) -> Tuple[str, float, Dict]:
        """
        Perform the complete RAG retrieval pipeline
        """
        start_time = time.time()
        
        # Get user context for filtering
        cancer_type = self._get_user_cancer_type(user)
        filters = self._build_search_filters(cancer_type)
        
        # Perform hybrid search
        retrieval_start = time.time()
        results = self.rag_service.hybrid_search(message_text, filters)
        retrieval_time = time.time() - retrieval_start
        
        # Rerank results
        rerank_start = time.time()
        results = self.rag_service.rerank_results(message_text, results)
        reranking_time = time.time() - rerank_start
        
        # Calculate confidence
        confidence = self.rag_service.calculate_confidence(results)
        
        # Generate response
        generation_start = time.time()
        
        if not results or confidence < self.rag_service.confidence_threshold:
            # Use fallback
            response = prompt_builder.build_not_found_response(message_text)
            fallback_used = True
        else:
            # Generate from context
            context = self.rag_service._build_context_from_results(results)
            response = self.rag_service._generate_from_context(
                message_text,
                context,
                prompt_builder
            )
            fallback_used = False
        
        generation_time = time.time() - generation_start
        
        # Return response with metrics
        metrics = {
            'retrieval_time': retrieval_time,
            'reranking_time': reranking_time,
            'generation_time': generation_time,
            'retrieval_count': len(results),
            'rerank_count': len(results),
            'fallback_used': fallback_used
        }
        
        return response, confidence, metrics
    
    def _get_or_create_session(self, user) -> ChatSession:
        """Get or create chat session"""
        session = ChatSession.objects.filter(
            user=user,
            active=True
        ).order_by('-updated_at').first()
        
        if not session:
            session = ChatSession.objects.create(
                user=user,
                title=f"Chat - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            )
        
        return session
    
    def _save_and_return(
        self, 
        session: ChatSession,
        user_content: str,
        assistant_content: str,
        metrics: QueryMetrics
    ) -> Tuple[str, ChatMessage]:
        """Save messages and return response with monitoring"""
        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_USER,
            content=user_content
        )
        
        # Save assistant message
        assistant_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_ASSISTANT,
            content=assistant_content
        )
        
        # Update metrics
        metrics.response_length = len(assistant_content)
        metrics.total_duration = time.time() - metrics.timestamp.timestamp()
        
        # Record metrics
        rag_monitor.record_query(metrics)
        
        return assistant_content, assistant_message
    
    def _get_user_context(self, user) -> Dict:
        """Get user context for caching and filtering"""
        context = {}
        
        if hasattr(user, 'medical_record') and user.medical_record:
            record = user.medical_record
            context['cancer_type'] = record.cancer_type.name if record.cancer_type else None
            context['cancer_stage'] = record.cancer_stage_text if hasattr(record, 'cancer_stage_text') else None
        
        if hasattr(user, 'language') and user.language:
            context['language'] = user.language.code
        
        return context
    
    def _get_user_cancer_type(self, user):
        """Get user's cancer type"""
        try:
            if hasattr(user, 'medical_record') and user.medical_record:
                return user.medical_record.cancer_type
        except Exception:
            pass
        return None
    
    def _build_search_filters(self, cancer_type) -> Dict:
        """Build search filters"""
        if not cancer_type:
            return {}
        
        return {
            "$or": [
                {"cancer_type": cancer_type.name},
                {"cancer_type": "general"},
                {"cancer_type": None}
            ]
        }
    
    def _is_emergency(self, message: str) -> bool:
        """Check if message indicates emergency"""
        return self.rag_service.is_emergency_message(message)
    
    def record_feedback(self, message_id: str, rating: int, feedback: Optional[str] = None):
        """Record user feedback for a message"""
        try:
            message = ChatMessage.objects.get(id=message_id)
            
            # Find associated metrics
            session_messages = ChatMessage.objects.filter(
                session=message.session,
                created_at__lte=message.created_at
            ).order_by('-created_at')
            
            # Get the query that generated this response
            user_message = None
            for msg in session_messages:
                if msg.role == ChatMessage.ROLE_USER:
                    user_message = msg
                    break
            
            if user_message:
                # Record feedback in monitor
                rag_monitor.record_user_feedback(
                    query_id=str(user_message.id),
                    rating=rating,
                    feedback=feedback
                )
        
        except Exception as e:
            logger.error(f"Error recording feedback: {e}")
    
    def get_analytics_dashboard(self, time_range: str = '24h') -> Dict:
        """Get analytics data for dashboard"""
        return rag_monitor.get_analytics_data(time_range)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return rag_cache.get_cache_stats()


# Create singleton instance
integrated_chat_service = IntegratedChatService()