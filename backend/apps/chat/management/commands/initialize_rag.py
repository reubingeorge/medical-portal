"""
Django management command to initialize the advanced RAG system
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import logging

from apps.chat.services_integrated import integrated_chat_service
from apps.chat.rag_cache import rag_cache, COMMON_MEDICAL_QUERIES
from apps.chat.models import ChatDocument

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Initialize the advanced RAG system with cache warming and document reprocessing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--warm-cache',
            action='store_true',
            help='Warm the cache with common queries'
        )
        parser.add_argument(
            '--reprocess-documents',
            action='store_true',
            help='Reprocess all documents with advanced chunking'
        )
        parser.add_argument(
            '--download-models',
            action='store_true',
            help='Download required NLP models'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initializing Advanced RAG System...'))
        
        # Download models if requested
        if options['download_models']:
            self._download_models()
        
        # Warm cache if requested
        if options['warm_cache']:
            self._warm_cache()
        
        # Reprocess documents if requested
        if options['reprocess_documents']:
            self._reprocess_documents()
        
        self.stdout.write(self.style.SUCCESS('RAG system initialization complete!'))
    
    def _download_models(self):
        """Download required NLP models"""
        self.stdout.write('Downloading NLP models...')
        
        try:
            # Download NLTK data
            import nltk
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            
            # Download spaCy model
            import subprocess
            subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'], check=True)
            
            self.stdout.write(self.style.SUCCESS('✓ NLP models downloaded'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error downloading models: {e}'))
    
    def _warm_cache(self):
        """Warm the cache with common queries"""
        self.stdout.write('Warming cache...')
        
        try:
            # Extend common queries with more medical terms
            extended_queries = COMMON_MEDICAL_QUERIES + [
                {
                    "query": "what are the side effects of gemcitabine",
                    "response": {
                        "content": "Common side effects of gemcitabine include nausea, vomiting, fatigue...",
                        "confidence": 0.9
                    }
                },
                {
                    "query": "cancer staging explained",
                    "response": {
                        "content": "Cancer staging describes the size of a cancer and how far it has spread...",
                        "confidence": 0.95
                    }
                },
                {
                    "query": "what is palliative care",
                    "response": {
                        "content": "Palliative care focuses on improving quality of life for people with serious illnesses...",
                        "confidence": 0.9
                    }
                }
            ]
            
            rag_cache.warm_cache(extended_queries)
            self.stdout.write(self.style.SUCCESS(f'✓ Cache warmed with {len(extended_queries)} queries'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error warming cache: {e}'))
    
    def _reprocess_documents(self):
        """Reprocess all documents with advanced chunking"""
        self.stdout.write('Reprocessing documents...')
        
        try:
            documents = ChatDocument.objects.all()
            total_docs = documents.count()
            
            for i, doc in enumerate(documents):
                self.stdout.write(f'Processing document {i+1}/{total_docs}: {doc.title}')
                
                try:
                    chunks_created = integrated_chat_service.process_document(doc)
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created {chunks_created} chunks'))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error: {e}'))
            
            self.stdout.write(self.style.SUCCESS(f'✓ Processed {total_docs} documents'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reprocessing documents: {e}'))