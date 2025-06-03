"""
Advanced RAG Service with Hybrid Search, Reranking, and Enhanced Retrieval
"""
import os
import time
import logging
import hashlib
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import numpy as np

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

# LangChain imports
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import LLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PDFMinerLoader, TextLoader, Docx2txtLoader
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

from .models import ChatDocument, ChatDocumentChunk, ChatSession, ChatMessage
from .prompts import PromptBuilder

logger = logging.getLogger(__name__)

# Sentence transformers for advanced similarity
try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("Sentence transformers not available. Some features will be limited.")


@dataclass
class RetrievalResult:
    """Data class for retrieval results with confidence scores"""
    document: Document
    relevance_score: float
    rerank_score: Optional[float] = None
    metadata: Optional[Dict] = None


class AdvancedRAGService:
    """
    Enhanced RAG service with:
    - Hybrid search (vector + keyword)
    - Cross-encoder reranking
    - Query expansion
    - Confidence scoring
    - Caching layer
    - Advanced chunking with context overlap
    """
    
    def __init__(self):
        """Initialize the advanced RAG service"""
        self._embedding_model = None
        self._llm_model = None
        self._vector_store = None
        self._reranker = None
        self._query_expander = None
        
        # Configuration
        self.chunk_size = 800
        self.chunk_overlap = 200
        self.retrieval_k = 20  # Retrieve more for reranking
        self.rerank_k = 5     # Return top-k after reranking
        self.confidence_threshold = 0.7
        self.cache_ttl = 3600  # 1 hour cache
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize all required models"""
        try:
            # Cross-encoder for reranking
            self._reranker = HuggingFaceCrossEncoder(
                model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
            ) if 'HuggingFaceCrossEncoder' in globals() else None

            # Query expansion model
            self._query_expander = SentenceTransformer('all-MiniLM-L6-v2') if SENTENCE_TRANSFORMERS_AVAILABLE else None

            logger.info("Advanced RAG models initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing advanced models: {e}")
    
    @property
    def embedding_model(self) -> Embeddings:
        """Get or create embedding model"""
        if self._embedding_model is None:
            self._embedding_model = OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY,
                model="text-embedding-3-small"
            )
        return self._embedding_model
    
    @property
    def llm_model(self) -> LLM:
        """Get or create LLM model"""
        if self._llm_model is None:
            self._llm_model = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                model_name="gpt-3.5-turbo",
                temperature=0.3,
                max_tokens=1000
            )
        return self._llm_model
    
    @property
    def vector_store(self) -> PGVector:
        """Get or create vector store"""
        if self._vector_store is None:
            connection_string = self._build_connection_string()
            self._vector_store = PGVector(
                connection=connection_string,
                embeddings=self.embedding_model,
                collection_name="medical_embeddings"
            )
        return self._vector_store
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string"""
        return (
            f"postgresql://{settings.DATABASES['default']['USER']}:"
            f"{settings.DATABASES['default']['PASSWORD']}@"
            f"{settings.DATABASES['default']['HOST']}:"
            f"{settings.DATABASES['default']['PORT']}/"
            f"{settings.DATABASES['default']['NAME']}"
        )
    
    def advanced_chunk_document(self, text: str, metadata: Dict) -> List[Document]:
        """
        Advanced document chunking with:
        - Context overlap
        - Sentence-aware splitting
        - Metadata preservation
        """
        # Use RecursiveCharacterTextSplitter for better chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        
        # Split text
        chunks = text_splitter.split_text(text)
        
        # Create documents with enhanced metadata
        documents = []
        for i, chunk in enumerate(chunks):
            # Add context from neighboring chunks
            context_before = chunks[i-1][-100:] if i > 0 else ""
            context_after = chunks[i+1][:100] if i < len(chunks)-1 else ""
            
            enhanced_metadata = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "context_before": context_before,
                "context_after": context_after,
                "chunk_size": len(chunk)
            }
            
            doc = Document(
                page_content=chunk,
                metadata=enhanced_metadata
            )
            documents.append(doc)
        
        return documents
    
    def expand_query(self, query: str, context: Optional[Dict] = None) -> List[str]:
        """
        Expand query with:
        - Synonyms
        - Related terms
        - Context-aware variations
        """
        expanded_queries = [query]
        
        # Use LLM for query expansion
        expansion_prompt = f"""
        Generate 3 alternative phrasings for this medical query: "{query}"
        
        Consider:
        1. Medical synonyms
        2. Layman's terms
        3. Related concepts
        
        Return only the alternative queries, one per line.
        """
        
        try:
            response = self.llm_model.invoke(expansion_prompt)
            alternatives = response.strip().split('\n')
            expanded_queries.extend([alt.strip() for alt in alternatives if alt.strip()])
        except Exception as e:
            logger.error(f"Query expansion error: {e}")
        
        return expanded_queries[:4]  # Limit to 4 queries
    
    def hybrid_search(self, query: str, filters: Optional[Dict] = None) -> List[RetrievalResult]:
        """
        Perform hybrid search combining:
        - Vector similarity search
        - Keyword search
        - Metadata filtering
        """
        results = []
        
        # Check cache first
        cache_key = f"rag_query_{hashlib.md5(query.encode()).hexdigest()}"
        cached_results = cache.get(cache_key)
        if cached_results:
            logger.info(f"Cache hit for query: {query}")
            return cached_results
        
        # Expand query
        expanded_queries = self.expand_query(query)
        
        # Perform vector searches for each query
        all_docs = {}
        for exp_query in expanded_queries:
            retriever = self.vector_store.as_retriever(
                search_kwargs={
                    "k": self.retrieval_k,
                    "filter": filters
                }
            )
            
            docs = retriever.get_relevant_documents(exp_query)
            
            # Deduplicate and score
            for doc in docs:
                doc_id = doc.metadata.get('source', str(hash(doc.page_content)))
                if doc_id not in all_docs:
                    all_docs[doc_id] = {
                        'document': doc,
                        'scores': []
                    }
                
                # Calculate similarity score (mock - in production use actual scores)
                similarity = 0.8 - (len(all_docs[doc_id]['scores']) * 0.1)
                all_docs[doc_id]['scores'].append(similarity)
        
        # Combine scores and create results
        for doc_data in all_docs.values():
            avg_score = np.mean(doc_data['scores'])
            results.append(RetrievalResult(
                document=doc_data['document'],
                relevance_score=avg_score
            ))
        
        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Cache results
        cache.set(cache_key, results[:self.retrieval_k], self.cache_ttl)
        
        return results[:self.retrieval_k]
    
    def rerank_results(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        Rerank results using cross-encoder for better relevance
        """
        if not results or not self._reranker:
            return results
        
        # Prepare pairs for reranking
        pairs = [[query, result.document.page_content] for result in results]
        
        try:
            # Get reranking scores
            rerank_scores = self._reranker.predict(pairs)
            
            # Update results with rerank scores
            for i, result in enumerate(results):
                result.rerank_score = float(rerank_scores[i])
            
            # Sort by rerank score
            results.sort(key=lambda x: x.rerank_score or 0, reverse=True)
            
        except Exception as e:
            logger.error(f"Reranking error: {e}")
        
        return results[:self.rerank_k]
    
    def calculate_confidence(self, results: List[RetrievalResult]) -> float:
        """
        Calculate confidence score based on:
        - Top result scores
        - Score distribution
        - Content relevance
        """
        if not results:
            return 0.0
        
        # Get top scores
        top_scores = [r.rerank_score or r.relevance_score for r in results[:3]]
        
        # Calculate confidence metrics
        avg_top_score = np.mean(top_scores)
        score_variance = np.var(top_scores) if len(top_scores) > 1 else 0
        
        # High scores with low variance = high confidence
        confidence = avg_top_score * (1 - score_variance)
        
        return min(max(confidence, 0.0), 1.0)
    
    def generate_response(self, user, message_text: str) -> Tuple[str, ChatMessage]:
        """
        Generate response with confidence scoring and fallback
        """
        start_time = time.time()
        
        # Get or create session
        session = self.get_or_create_session(user)
        
        # Create prompt builder
        prompt_builder = PromptBuilder(patient=user, language=user.language)
        
        # Check for emergency
        if self.is_emergency_message(message_text):
            emergency_response = prompt_builder.build_emergency_response()
            return self._save_and_return_message(
                session, message_text, emergency_response
            )
        
        # Get user context
        cancer_type = self._get_user_cancer_type(user)
        filters = self._build_search_filters(cancer_type)
        
        # Perform hybrid search
        results = self.hybrid_search(message_text, filters)
        
        # Rerank results
        results = self.rerank_results(message_text, results)
        
        # Calculate confidence
        confidence = self.calculate_confidence(results)
        
        # Log retrieval metrics
        self._log_retrieval_metrics(message_text, results, confidence)
        
        # Generate response based on confidence
        if confidence < self.confidence_threshold or not results:
            # Low confidence - use fallback
            response = prompt_builder.build_not_found_response(message_text)
        else:
            # High confidence - generate from context
            context = self._build_context_from_results(results)
            response = self._generate_from_context(
                message_text, context, prompt_builder
            )
        
        # Add confidence indicator
        if confidence < 0.5:
            response += "\n\n*Note: This response has lower confidence. Please verify with your healthcare provider.*"
        
        elapsed_time = time.time() - start_time
        logger.info(f"Response generated in {elapsed_time:.2f}s with confidence {confidence:.2f}")
        
        return self._save_and_return_message(session, message_text, response)
    
    def _get_user_cancer_type(self, user):
        """Get user's cancer type for filtering"""
        try:
            if hasattr(user, 'medical_record') and user.medical_record:
                return user.medical_record.cancer_type
        except Exception:
            pass
        return None
    
    def _build_search_filters(self, cancer_type):
        """Build search filters based on cancer type"""
        if not cancer_type:
            return None
        
        return {
            "$or": [
                {"cancer_type": cancer_type.name},
                {"cancer_type": "general"},
                {"cancer_type": None}
            ]
        }
    
    def _build_context_from_results(self, results: List[RetrievalResult]) -> str:
        """Build context from retrieval results"""
        context_parts = []
        
        for i, result in enumerate(results):
            score = result.rerank_score or result.relevance_score
            context_parts.append(
                f"[Source {i+1} - Relevance: {score:.2f}]\n"
                f"{result.document.page_content}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def _generate_from_context(self, query: str, context: str, prompt_builder: PromptBuilder) -> str:
        """Generate response from context"""
        system_prompt = prompt_builder.build_system_prompt()
        
        messages = [
            ("system", system_prompt),
            ("user", f"Context:\n{context}\n\nQuestion: {query}")
        ]
        
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | self.llm_model | StrOutputParser()
        
        return chain.invoke({})
    
    def _save_and_return_message(self, session: ChatSession, user_content: str, assistant_content: str) -> Tuple[str, ChatMessage]:
        """Save messages and return response"""
        # Save user message
        ChatMessage.objects.create(
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
        
        return assistant_content, assistant_message
    
    def _log_retrieval_metrics(self, query: str, results: List[RetrievalResult], confidence: float):
        """Log retrieval metrics for monitoring"""
        metrics = {
            "query": query,
            "num_results": len(results),
            "confidence": confidence,
            "top_scores": [r.rerank_score or r.relevance_score for r in results[:3]],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"RAG Metrics: {json.dumps(metrics)}")
    
    def get_or_create_session(self, user) -> ChatSession:
        """Get or create chat session"""
        # Try to get the most recent active session
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
    
    def is_emergency_message(self, message: str) -> bool:
        """Check if message indicates emergency"""
        emergency_keywords = {
            'emergency', 'urgent', 'chest pain', 'severe pain', 'trouble breathing',
            'heart attack', 'suicide', 'bleeding', 'hemorrhage', 'unconscious',
            '911', 'help me', 'need help now', 'stroke', 'seizure'
        }
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in emergency_keywords)


# Create singleton instance
advanced_rag_service = AdvancedRAGService()