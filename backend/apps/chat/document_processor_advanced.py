"""
Advanced Document Processor with Enhanced Chunking and Metadata Extraction
"""
import re
import logging
import hashlib
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import fitz  # PyMuPDF for better PDF processing

from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter, SentenceTransformersTokenTextSplitter
from langchain_community.document_loaders import PDFMinerLoader, TextLoader, Docx2txtLoader

logger = logging.getLogger(__name__)

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    logger.warning("NLTK not available. Some NLP features will be limited.")

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available. Entity extraction will be limited.")

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except:
    pass

# Load spaCy model for NER
try:
    nlp = spacy.load("en_core_web_sm") if SPACY_AVAILABLE else None
except:
    logger.warning("spaCy model not loaded. Some features will be limited.")
    nlp = None


class AdvancedDocumentProcessor:
    """
    Enhanced document processor with:
    - Intelligent chunking with context preservation
    - Metadata extraction (entities, topics, structure)
    - Section-aware splitting
    - Table and figure handling
    """
    
    def __init__(self):
        self.chunk_size = 800
        self.chunk_overlap = 200
        self.min_chunk_size = 100
        self.max_chunk_size = 1200
        
        # Initialize splitters
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        
        self.sentence_splitter = SentenceTransformersTokenTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
    
    def process_document(self, file_path: str, metadata: Dict) -> List[Document]:
        """Process document with enhanced chunking and metadata extraction"""
        file_path = Path(file_path)
        
        # Extract text based on file type
        if file_path.suffix.lower() == '.pdf':
            documents = self._process_pdf(file_path, metadata)
        elif file_path.suffix.lower() in ['.doc', '.docx']:
            documents = self._process_word(file_path, metadata)
        elif file_path.suffix.lower() == '.txt':
            documents = self._process_text(file_path, metadata)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
        
        # Enhance all documents with additional metadata
        enhanced_documents = []
        for doc in documents:
            enhanced_doc = self._enhance_document_metadata(doc)
            enhanced_documents.append(enhanced_doc)
        
        return enhanced_documents
    
    def _process_pdf(self, file_path: Path, base_metadata: Dict) -> List[Document]:
        """Process PDF with structure awareness"""
        documents = []
        
        try:
            # Use PyMuPDF for better PDF handling
            pdf_doc = fitz.open(str(file_path))
            
            full_text = ""
            sections = []
            
            for page_num, page in enumerate(pdf_doc):
                # Extract text with structure
                text = page.get_text()
                
                # Extract tables
                tables = page.find_tables()
                table_data = []
                for table in tables:
                    table_data.append(table.extract())
                
                # Detect section headers
                section_headers = self._extract_section_headers(text)
                
                page_metadata = {
                    **base_metadata,
                    "page": page_num + 1,
                    "total_pages": len(pdf_doc),
                    "has_tables": len(tables) > 0,
                    "table_count": len(tables),
                    "section_headers": section_headers
                }
                
                # Create structured chunks
                if section_headers:
                    # Split by sections
                    section_chunks = self._split_by_sections(text, section_headers)
                    for section_name, section_text in section_chunks:
                        chunk_metadata = {
                            **page_metadata,
                            "section": section_name,
                            "chunk_type": "section"
                        }
                        documents.extend(
                            self._create_chunks(section_text, chunk_metadata)
                        )
                else:
                    # Regular chunking
                    documents.extend(
                        self._create_chunks(text, page_metadata)
                    )
                
                # Process tables separately
                for i, table_data in enumerate(table_data):
                    table_text = self._format_table(table_data)
                    table_metadata = {
                        **page_metadata,
                        "chunk_type": "table",
                        "table_index": i
                    }
                    documents.append(Document(
                        page_content=table_text,
                        metadata=table_metadata
                    ))
                
                full_text += text + "\n"
            
            pdf_doc.close()
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            # Fallback to basic processing
            loader = PDFMinerLoader(str(file_path))
            documents = loader.load()
            documents = self._chunk_documents(documents, base_metadata)
        
        return documents
    
    def _extract_section_headers(self, text: str) -> List[str]:
        """Extract section headers from text"""
        headers = []
        
        # Common patterns for headers
        patterns = [
            r'^#+\s+(.+)$',  # Markdown headers
            r'^([A-Z][A-Z\s]+)$',  # All caps headers
            r'^\d+\.\s+(.+)$',  # Numbered headers
            r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*:$',  # Title case with colon
        ]
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    headers.append(line)
                    break
        
        return headers
    
    def _split_by_sections(self, text: str, headers: List[str]) -> List[Tuple[str, str]]:
        """Split text by section headers"""
        sections = []
        current_section = "Introduction"
        current_text = ""
        
        lines = text.split('\n')
        for line in lines:
            if line.strip() in headers:
                if current_text:
                    sections.append((current_section, current_text))
                current_section = line.strip()
                current_text = ""
            else:
                current_text += line + "\n"
        
        if current_text:
            sections.append((current_section, current_text))
        
        return sections
    
    def _create_chunks(self, text: str, metadata: Dict) -> List[Document]:
        """Create chunks with context overlap"""
        chunks = []
        
        # Use sentence-aware splitting
        sentences = sent_tokenize(text) if nltk else text.split('. ')
        
        current_chunk = ""
        chunk_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence exceeds chunk size
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                # Create chunk with context
                chunk_metadata = {
                    **metadata,
                    "sentence_count": len(chunk_sentences),
                    "chunk_type": "text"
                }
                
                # Add context from next sentence
                context_after = sentences[sentences.index(sentence)][:100] if sentence in sentences else ""
                chunk_metadata["context_after"] = context_after
                
                chunks.append(Document(
                    page_content=current_chunk,
                    metadata=chunk_metadata
                ))
                
                # Start new chunk with overlap
                overlap_sentences = chunk_sentences[-2:] if len(chunk_sentences) > 2 else chunk_sentences
                current_chunk = " ".join(overlap_sentences) + " " + sentence
                chunk_sentences = overlap_sentences + [sentence]
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                chunk_sentences.append(sentence)
        
        # Add last chunk
        if current_chunk:
            chunk_metadata = {
                **metadata,
                "sentence_count": len(chunk_sentences),
                "chunk_type": "text",
                "is_last_chunk": True
            }
            chunks.append(Document(
                page_content=current_chunk,
                metadata=chunk_metadata
            ))
        
        return chunks
    
    def _enhance_document_metadata(self, document: Document) -> Document:
        """Enhance document with extracted entities and topics"""
        text = document.page_content
        metadata = document.metadata.copy()
        
        # Extract entities using spaCy
        if nlp:
            try:
                doc = nlp(text[:1000])  # Process first 1000 chars for efficiency
                
                # Extract medical entities
                entities = {
                    "medications": [],
                    "conditions": [],
                    "symptoms": [],
                    "procedures": []
                }
                
                for ent in doc.ents:
                    if ent.label_ in ["DRUG", "CHEMICAL"]:
                        entities["medications"].append(ent.text)
                    elif ent.label_ in ["DISEASE", "CONDITION"]:
                        entities["conditions"].append(ent.text)
                
                # Look for medical terms
                medical_patterns = {
                    "medications": r'\b(?:drug|medication|treatment|therapy|dose|mg)\b',
                    "symptoms": r'\b(?:pain|fever|nausea|fatigue|weakness)\b',
                    "procedures": r'\b(?:surgery|procedure|test|scan|biopsy)\b'
                }
                
                for category, pattern in medical_patterns.items():
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    entities[category].extend(matches)
                
                metadata["entities"] = entities
                
            except Exception as e:
                logger.error(f"Entity extraction error: {e}")
        
        # Extract key terms
        metadata["key_terms"] = self._extract_key_terms(text)
        
        # Calculate text statistics
        metadata["statistics"] = {
            "char_count": len(text),
            "word_count": len(word_tokenize(text)) if nltk else len(text.split()),
            "sentence_count": len(sent_tokenize(text)) if nltk else text.count('.'),
            "avg_word_length": self._avg_word_length(text)
        }
        
        # Detect content type
        metadata["content_type"] = self._detect_content_type(text)
        
        return Document(page_content=text, metadata=metadata)
    
    def _extract_key_terms(self, text: str, max_terms: int = 10) -> List[str]:
        """Extract key terms using TF-IDF-like approach"""
        if not nltk:
            return []
        
        # Tokenize and filter
        words = word_tokenize(text.lower())
        stop_words = set(stopwords.words('english')) if nltk else set()
        
        # Filter words
        filtered_words = [
            word for word in words 
            if len(word) > 3 and word not in stop_words and word.isalpha()
        ]
        
        # Count frequencies
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_terms = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [term for term, freq in sorted_terms[:max_terms]]
    
    def _detect_content_type(self, text: str) -> str:
        """Detect the type of content (clinical, research, guidelines, etc.)"""
        content_patterns = {
            "clinical_trial": r"clinical trial|randomized|placebo",
            "guidelines": r"guideline|recommendation|protocol",
            "case_study": r"case report|patient presentation",
            "review": r"systematic review|meta-analysis",
            "educational": r"patient education|information for patients"
        }
        
        text_lower = text.lower()
        for content_type, pattern in content_patterns.items():
            if re.search(pattern, text_lower):
                return content_type
        
        return "general"
    
    def _format_table(self, table_data: List[List[str]]) -> str:
        """Format table data as readable text"""
        if not table_data:
            return ""
        
        formatted = "Table:\n"
        for row in table_data:
            formatted += " | ".join(str(cell) for cell in row) + "\n"
        
        return formatted
    
    def _avg_word_length(self, text: str) -> float:
        """Calculate average word length"""
        words = text.split()
        if not words:
            return 0
        
        total_length = sum(len(word) for word in words)
        return total_length / len(words)
    
    def _process_word(self, file_path: Path, metadata: Dict) -> List[Document]:
        """Process Word documents"""
        loader = Docx2txtLoader(str(file_path))
        documents = loader.load()
        return self._chunk_documents(documents, metadata)
    
    def _process_text(self, file_path: Path, metadata: Dict) -> List[Document]:
        """Process text files"""
        loader = TextLoader(str(file_path))
        documents = loader.load()
        return self._chunk_documents(documents, metadata)
    
    def _chunk_documents(self, documents: List[Document], metadata: Dict) -> List[Document]:
        """Fallback chunking method"""
        chunked_docs = []
        
        for doc in documents:
            chunks = self.recursive_splitter.split_text(doc.page_content)
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    **metadata,
                    **doc.metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
                chunked_docs.append(Document(
                    page_content=chunk,
                    metadata=chunk_metadata
                ))
        
        return chunked_docs