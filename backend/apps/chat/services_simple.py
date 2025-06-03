"""
Simplified chat service that works without advanced dependencies
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
from langchain_community.document_loaders import PDFMinerLoader, TextLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .models import ChatDocument, ChatDocumentChunk, ChatSession, ChatMessage
from .prompts import PromptBuilder

logger = logging.getLogger(__name__)


class SimpleChatService:
    """
    Simple chat service that provides basic RAG functionality
    without requiring advanced dependencies
    """
    
    EMERGENCY_KEYWORDS = {
        'emergency', 'urgent', 'chest pain', 'severe pain', 'trouble breathing',
        'heart attack', 'suicide', 'bleeding', 'hemorrhage', 'unconscious',
        '911', 'help me', 'need help now', 'stroke', 'seizure'
    }
    
    def __init__(self):
        """Initialize the service with lazy loading of models."""
        self.openai_api_key = os.environ.get("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        self._embedding_model = None
        self._llm_model = None
        self._vector_store = None
        
        # Configuration
        self.chunk_size = 800
        self.chunk_overlap = 200
        self.retrieval_k = 10
    
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
    
    def create_or_continue_session(self, user) -> ChatSession:
        """Create or continue a chat session."""
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
        """Check if message indicates emergency."""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.EMERGENCY_KEYWORDS)
    
    def get_chat_history(self, session: ChatSession) -> List[Dict]:
        """Get formatted chat history."""
        messages = ChatMessage.objects.filter(
            session=session
        ).order_by('created_at')[:20]
        
        return [
            {
                "role": message.role,
                "content": message.content
            }
            for message in messages
        ]
    
    def generate_response(self, user, message_text: str) -> Tuple[str, ChatMessage]:
        """Generate response using basic RAG."""
        start_time = time.time()
        
        # Get or create session
        session = self.create_or_continue_session(user)
        
        # Create prompt builder
        prompt_builder = PromptBuilder(patient=user, language=user.language)
        
        # Check for emergency
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
                "filter": search_filter,
                "fetch_k": self.retrieval_k * 5
            }
        )
    
    def process_document(self, document: ChatDocument) -> int:
        """Process document with basic chunking."""
        chunks_created = 0
        
        try:
            # Clear existing chunks
            document.chunks.all().delete()
            
            # Load document
            file_path = Path(document.file.path)
            loader = self._get_loader(file_path)
            
            if not loader:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")
            
            # Load and split document
            docs = loader.load()
            
            # Split into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            split_docs = text_splitter.split_documents(docs)
            
            # Create chunks with metadata
            for i, doc in enumerate(split_docs):
                # Prepare metadata
                metadata = {
                    "source": str(document.id),
                    "title": document.title,
                    "document_type": document.document_type,
                    "cancer_type": document.cancer_type.name if document.cancer_type else None,
                    "page": doc.metadata.get("page", 0),
                    "chunk_index": i
                }
                
                # Create document with metadata
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
                vector_id = self.vector_store.add_documents(
                    [doc_with_metadata],
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
            
            logger.info(f"Document {document.id} processed: {chunks_created} chunks created")
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            document.indexed = False
            document.save()
            raise
        
        return chunks_created
    
    def _get_loader(self, file_path: Path):
        """Get appropriate loader for file type."""
        loaders = {
            '.pdf': PDFMinerLoader,
            '.txt': TextLoader,
            '.docx': Docx2txtLoader,
            '.doc': Docx2txtLoader
        }
        
        loader_class = loaders.get(file_path.suffix.lower())
        if loader_class:
            return loader_class(str(file_path))
        return None
    
    def clear_document_embeddings(self, document: ChatDocument):
        """Clear embeddings for a document."""
        try:
            chunks = document.chunks.all()
            vector_ids = [chunk.vector_id for chunk in chunks if chunk.vector_id]
            
            if vector_ids:
                self.vector_store.delete(vector_ids)
            
            chunks.delete()
            
            document.indexed = False
            document.indexed_at = None
            document.save()
            
            logger.info(f"Cleared embeddings for document {document.id}")
            
        except Exception as e:
            logger.error(f"Error clearing embeddings: {e}")
            raise
    
    def health_check(self) -> Dict[str, bool]:
        """Perform health check."""
        health_status = {
            "service": True,
            "database": True,
            "vector_store": False,
            "llm": False
        }
        
        try:
            ChatDocument.objects.exists()
            health_status["database"] = True
        except Exception:
            health_status["database"] = False
        
        try:
            self.vector_store.similarity_search("test", k=1)
            health_status["vector_store"] = True
        except Exception:
            pass
        
        try:
            self.llm_model.invoke("test")
            health_status["llm"] = True
        except Exception:
            pass
        
        health_status["service"] = health_status["database"]
        
        return health_status


# Create singleton instance
simple_chat_service = SimpleChatService()