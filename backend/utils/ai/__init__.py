"""
AI utilities package for the medical portal application.
Includes OCR and analysis features for medical documents.
"""
from .ocr import extract_text_from_pdf, is_pathology_report
from .analysis import analyze_pathology_report, process_document_for_analysis, get_matching_cancer_types

__all__ = [
    'extract_text_from_pdf',
    'is_pathology_report',
    'analyze_pathology_report',
    'process_document_for_analysis',
    'get_matching_cancer_types',
]