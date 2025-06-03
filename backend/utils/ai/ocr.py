"""
Utility functions for OCR processing of medical documents.
Uses PaddleOCR for text extraction from images and PDFs.
"""
import os
import tempfile
import logging
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)

# Initialize PaddleOCR once to avoid repeated initialization
ocr = None

def get_ocr_instance():
    """Get or initialize the PaddleOCR instance."""
    global ocr
    if ocr is None:
        # Initialize with English language and use CUDA if available
        try:
            ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True)
            logger.info("PaddleOCR initialized with GPU support")
        except Exception:
            # Fallback to CPU if GPU fails
            ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
            logger.info("PaddleOCR initialized with CPU (GPU not available)")
    return ocr

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file using both PDF text extraction and OCR.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
    logger.info(f"Processing PDF for text extraction: {pdf_path}")
    text_content = []
    print(f'PDF PATH: {pdf_path}')
    try:
        # Open the PDF file
        pdf_document = fitz.open(pdf_path)
        
        # Get OCR instance
        paddle_ocr = get_ocr_instance()
        
        # Process each page
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            
            # Try to extract text directly from PDF
            page_text = page.get_text()
            
            # If we got meaningful text, use it
            if page_text and len(page_text.strip()) > 100:
                text_content.append(page_text)
                logger.debug(f"Extracted text directly from page {page_num+1}")
            else:
                # If text extraction failed or returned minimal text, use OCR
                logger.debug(f"Using OCR for page {page_num+1} due to insufficient direct text")
                
                # Render the page as an image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scaling for better OCR
                
                # Create a temporary image file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_image_path = temp_file.name
                    
                # Save the page image
                pix.save(temp_image_path)
                
                try:
                    # Run OCR on the image
                    result = paddle_ocr.ocr(temp_image_path, cls=True)
                    
                    # Extract and concatenate text from OCR results
                    page_ocr_text = []
                    for line in result:
                        for item in line:
                            if isinstance(item, list) and len(item) == 2:
                                text, confidence = item[1]
                                page_ocr_text.append(text)
                    
                    if page_ocr_text:
                        text_content.append("\n".join(page_ocr_text))
                        logger.debug(f"Extracted {len(page_ocr_text)} lines via OCR from page {page_num+1}")
                except Exception as e:
                    logger.error(f"OCR processing error on page {page_num+1}: {str(e)}")
                
                # Clean up the temporary file
                try:
                    os.unlink(temp_image_path)
                except Exception:
                    pass
        
        # Close the PDF document
        pdf_document.close()
        
        # Combine all text content with page separators
        full_text = "\n\n----- PAGE BREAK -----\n\n".join(text_content)
        logger.info(f"Successfully extracted text from PDF ({len(full_text)} characters)")
        return full_text
        
    except Exception as e:
        logger.error(f"Error processing PDF for text extraction: {str(e)}")
        return ""

def is_pathology_report(text: str) -> bool:
    """
    Determine if the extracted text appears to be a pathology report.
    
    Args:
        text: Extracted text from document
        
    Returns:
        Boolean indicating if text is likely a pathology report
    """
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Keywords frequently found in pathology reports
    pathology_keywords = [
        "pathology report", "surgical pathology", "histopathology",
        "specimen type", "gross description", "microscopic description",
        "diagnosis:", "final diagnosis", "specimen received",
        "histologic type", "histologic grade", "tumor size",
        "margin status", "lymph node", "immunohistochemistry",
        "pathologist"
    ]
    
    # Count how many pathology keywords are found
    keyword_count = sum(1 for keyword in pathology_keywords if keyword in text_lower)
    
    # If more than 3 keywords are found, consider it a pathology report
    is_pathology = keyword_count >= 3
    
    logger.info(f"Document pathology report detection: {is_pathology} ({keyword_count} keywords matched)")
    return is_pathology