"""
Enhanced chat service with improved efficiency and modularity.
"""
import os
import logging
import time
from typing import Optional, Tuple, List, Dict
from datetime import datetime
import json
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.db import transaction

# LangChain imports
from langchain_core.language_models import LLM
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_community.document_loaders import PDFMinerLoader, TextLoader, Docx2txtLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .models import ChatDocument, ChatDocumentChunk, ChatSession, ChatMessage
from .prompts import PromptBuilder

logger = logging.getLogger(__name__)


class EnhancedChatService:
    """Enhanced chat service with better error handling and performance."""
    
    # Class-level constants
    EMERGENCY_KEYWORDS = {
        'emergency', 'urgent', 'chest pain', 'severe pain', 'trouble breathing',
        'heart attack', 'suicide', 'bleeding', 'hemorrhage', 'unconscious',
        '911', 'help me', 'need help now', 'stroke', 'seizure', 'dying',
        'can\'t breathe', 'passing out', 'severe headache', 'overdose'
    }
    
    SUPPORTED_FILE_TYPES = {
        '.pdf': PDFMinerLoader,
        '.txt': TextLoader,
        '.docx': Docx2txtLoader,
        '.doc': Docx2txtLoader
    }
    
    def __init__(self):
        """Initialize service with lazy loading of models."""
        self.openai_api_key = os.environ.get("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        self._embedding_model = None
        self._llm_model = None
        self._vector_store = None
        
        # Service configuration
        self.chunk_size = 800
        self.chunk_overlap = 200
        self.retrieval_k = 10  # Number of top documents to retrieve
        
        # Initialize vector store
        self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """Initialize the vector store connection."""
        try:
            # Force get the vector store to ensure it's connected
            _ = self.vector_store
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
    
    @property
    def embedding_model(self) -> Embeddings:
        """Get or create embedding model with lazy loading."""
        if self._embedding_model is None:
            self._embedding_model = OpenAIEmbeddings(
                openai_api_key=self.openai_api_key,
                model="text-embedding-3-small"
            )
        return self._embedding_model
    
    @property
    def llm_model(self) -> LLM:
        """Get or create LLM model with lazy loading."""
        if self._llm_model is None:
            self._llm_model = ChatOpenAI(
                openai_api_key=self.openai_api_key,
                model_name="gpt-3.5-turbo",
                temperature=0.3,
                max_tokens=1000
            )
        return self._llm_model
    
    @property
    def vector_store(self) -> PGVector:
        """Get or create vector store with lazy loading."""
        if self._vector_store is None:
            connection_string = self._build_connection_string()
            self._vector_store = PGVector(
                connection=connection_string,
                embeddings=self.embedding_model,
                collection_name="medical_embeddings"
            )
        return self._vector_store
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string for vector store."""
        db_config = settings.DATABASES['default']
        return (
            f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}@"
            f"{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"
        )
    
    def is_emergency_message(self, message: str) -> bool:
        """Check if message contains emergency keywords."""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.EMERGENCY_KEYWORDS)
    
    def create_or_continue_session(self, user) -> ChatSession:
        """Create a new chat session or continue the most recent one."""
        # Try to get the most recent active session
        session = ChatSession.objects.filter(
            user=user,
            active=True
        ).order_by('-updated_at').first()
        
        if not session:
            # Create new session if none exists
            session = ChatSession.objects.create(
                user=user,
                title=f"Chat - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            )
        
        return session
    
    def get_chat_history(self, session: ChatSession) -> List[Dict]:
        """Get formatted chat history for a session."""
        messages = ChatMessage.objects.filter(
            session=session
        ).order_by('created_at')[:20]  # Limit to last 20 messages for context
        
        return [
            {
                "role": message.role,
                "content": message.content
            }
            for message in messages
        ]
    
    def process_document(self, document: ChatDocument) -> int:
        """
        Process a document and create embeddings for RAG.
        
        Args:
            document: The ChatDocument to process
            
        Returns:
            Number of chunks created
        """
        chunks_created = 0
        
        try:
            # Clear existing chunks if any
            document.chunks.all().delete()
            
            # Get file path
            file_path = Path(document.file.path)
            
            # Select appropriate loader
            loader_class = self.SUPPORTED_FILE_TYPES.get(file_path.suffix.lower())
            if not loader_class:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")
            
            # Load document
            loader = loader_class(str(file_path))
            docs = loader.load()
            
            # Split into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            split_docs = text_splitter.split_documents(docs)
            
            # Process each chunk
            for i, doc in enumerate(split_docs):
                # Prepare metadata
                metadata = {
                    'source': str(document.id),
                    'title': document.title,
                    'document_type': document.document_type,
                    'cancer_type': document.cancer_type.name if document.cancer_type else None,
                    'page': doc.metadata.get('page', 0),
                    'chunk_index': i,
                    'cancer_type_id': str(document.cancer_type.id) if document.cancer_type else None
                }
                
                # Create Document with metadata
                doc_with_metadata = Document(
                    page_content=doc.page_content,
                    metadata=metadata
                )
                
                # Create chunk record
                chunk = ChatDocumentChunk.objects.create(
                    document=document,
                    chunk_index=i,
                    content=doc.page_content,
                    metadata=metadata
                )
                
                # Add to vector store
                try:
                    vector_id = self.vector_store.add_documents(
                        [doc_with_metadata],
                        ids=[str(chunk.id)]
                    )[0]
                    
                    # Update chunk with vector ID
                    chunk.vector_id = vector_id
                    chunk.save()
                    
                    chunks_created += 1
                except Exception as e:
                    logger.error(f"Error adding chunk to vector store: {e}")
                    # Continue processing other chunks
            
            # Update document status
            document.indexed = True
            document.indexed_at = timezone.now()
            document.save()
            
            logger.info(f"Document {document.id} processed: {chunks_created} chunks created")
            
        except Exception as e:
            logger.error(f"Error processing document {document.id}: {e}")
            document.indexed = False
            document.save()
            raise
        
        return chunks_created
    
    def generate_response(self, user, message_text: str) -> Tuple[str, ChatMessage]:
        """Generate chat response with improved error handling."""
        start_time = time.time()
        
        # Get or create session
        session = self.create_or_continue_session(user)
        
        # Create prompt builder
        prompt_builder = PromptBuilder(patient=user, language=user.language)
        
        # Check for emergency first
        if self.is_emergency_message(message_text):
            emergency_response = prompt_builder.build_emergency_response()
            
            # Save messages
            user_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.ROLE_USER,
                content=message_text
            )
            
            assistant_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.ROLE_ASSISTANT,
                content=emergency_response
            )
            
            logger.info(f"Emergency response generated in {time.time() - start_time:.2f}s")
            return emergency_response, assistant_message
        
        # Get chat history
        chat_history = self.get_chat_history(session)
        
        # Build prompts
        system_prompt = prompt_builder.build_system_prompt()
        
        # Get cancer type for filtering
        cancer_type = None
        organ_type = None
        try:
            if hasattr(user, 'medical_record') and user.medical_record:
                cancer_type = user.medical_record.cancer_type
                # Use organ type for filtering
                if cancer_type and not cancer_type.is_organ and cancer_type.parent:
                    organ_type = cancer_type.parent
                else:
                    organ_type = cancer_type
        except Exception:
            pass
        
        # Build query for retrieval
        query_prompt = prompt_builder.build_query_prompt(
            message_text, 
            cancer_type=organ_type or cancer_type
        )
        
        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.ROLE_USER,
            content=message_text
        )
        
        try:
            # Retrieve relevant documents
            retriever = self._get_retriever(organ_type)
            retrieved_docs = retriever.invoke(query_prompt)
            
            # If no relevant documents found
            if not retrieved_docs:
                not_found_response = prompt_builder.build_not_found_response(message_text)
                
                assistant_message = ChatMessage.objects.create(
                    session=session,
                    role=ChatMessage.ROLE_ASSISTANT,
                    content=not_found_response
                )
                
                logger.info(f"No documents found response in {time.time() - start_time:.2f}s")
                return not_found_response, assistant_message
            
            # Combine retrieved documents
            retrieved_context = "\n\n".join([
                f"[Document {i+1}]\n{doc.page_content}"
                for i, doc in enumerate(retrieved_docs)
            ])
            
            # Create messages for prompt
            messages = [("system", system_prompt)]
            
            # Add chat history
            for msg in chat_history:
                messages.append((msg["role"], msg["content"]))
            
            # Add current query with context
            messages.append((
                "user", 
                f"Context from knowledge base:\n{retrieved_context}\n\n"
                f"User Question: {message_text}"
            ))
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages(messages)
            
            # Create chain and generate response
            chain = prompt | self.llm_model | StrOutputParser()
            response = chain.invoke({})
            
            # Save assistant message
            assistant_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.ROLE_ASSISTANT,
                content=response
            )
            
            logger.info(f"Response generated in {time.time() - start_time:.2f}s")
            return response, assistant_message
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            
            # Create error response
            error_response = (
                "I apologize, but I encountered an error while processing your request. "
                "Please try again later or contact your healthcare provider if this is urgent."
            )
            
            # Save error message
            error_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.ROLE_ASSISTANT,
                content=error_response
            )
            
            return error_response, error_message
    
    def _get_retriever(self, cancer_type=None):
        """Get retriever with appropriate filters."""
        search_filter = None
        
        if cancer_type:
            # Filter by cancer type name (matching the metadata structure)
            search_filter = {
                "$or": [
                    {"cancer_type": cancer_type.name},
                    {"cancer_type": "general"}
                ]
            }
        
        return self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": self.retrieval_k,
                "filter": search_filter,  # Can be None for no filtering
                "fetch_k": self.retrieval_k * 5  # Fetch more for better selection
            }
        )
    
    def clear_document_embeddings(self, document: ChatDocument):
        """Clear embeddings for a specific document."""
        try:
            # Get chunk vector IDs
            chunks = document.chunks.all()
            vector_ids = [chunk.vector_id for chunk in chunks if chunk.vector_id]
            
            if vector_ids:
                # Delete from vector store
                self.vector_store.delete(vector_ids)
                
                # Delete chunk records
                chunks.delete()
                
                logger.info(f"Cleared {len(vector_ids)} embeddings for document {document.id}")
        except Exception as e:
            logger.error(f"Error clearing embeddings: {e}")
            raise
    
    def health_check(self) -> Dict[str, bool]:
        """
        Perform health check on the chat service components.
        
        Returns:
            Dictionary with component health status
        """
        health_status = {
            "service": True,
            "database": True,
            "vector_store": False,
            "llm": False,
            "embeddings": False
        }
        
        # Check database
        try:
            ChatDocument.objects.exists()
            health_status["database"] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["database"] = False
        
        # Check vector store
        try:
            # Try to perform a simple search
            self.vector_store.similarity_search("test", k=1)
            health_status["vector_store"] = True
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            health_status["vector_store"] = False
        
        # Check LLM
        try:
            self.llm_model.invoke("test")
            health_status["llm"] = True
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            health_status["llm"] = False
        
        # Check embeddings
        try:
            self.embedding_model.embed_query("test")
            health_status["embeddings"] = True
        except Exception as e:
            logger.error(f"Embeddings health check failed: {e}")
            health_status["embeddings"] = False
        
        # Overall service health
        health_status["service"] = all([
            health_status["database"],
            health_status["vector_store"]
        ])
        
        return health_status


# Create singleton instance
chat_service = EnhancedChatService()