"""
Utility functions for AI-powered analysis of medical documents.
Uses OpenAI API for text analysis and extraction of medical information.
"""
import json
import logging
import os
from typing import Dict, Any, Optional, Tuple, List, Union

import openai
from django.conf import settings

from .ocr import is_pathology_report, extract_text_from_pdf

logger = logging.getLogger(__name__)

# Configure OpenAI API key from settings
openai.api_key = settings.OPENAI_API_KEY


def analyze_pathology_report(text: str) -> Optional[Dict[str, Any]]:
    """
    Analyze a pathology report using OpenAI API to extract cancer type,
    FIGO stage, and final pathologic stage.
    
    Args:
        text: The text content of the pathology report
        
    Returns:
        Dictionary containing the extracted information or None if analysis failed
    """
    if not text:
        logger.warning("Cannot analyze empty text")
        return None
        
    if not is_pathology_report(text):
        logger.info("Text does not appear to be a pathology report")
        return None
        
    if not openai.api_key:
        logger.error("OpenAI API key not configured")
        return None
    
    # Get all cancer types from database to provide to the AI
    try:
        # Lazy import to avoid circular imports
        from django.apps import apps
        CancerType = apps.get_model('medical', 'CancerType')
        
        # Get all organ types
        organ_types = list(CancerType.objects.filter(is_organ=True).values('id', 'name'))
        
        # Create a mapping of organ types to their subtypes
        cancer_subtypes_by_organ = {}
        for organ in organ_types:
            subtypes = list(CancerType.objects.filter(parent_id=organ['id']).values('id', 'name'))
            if subtypes:
                cancer_subtypes_by_organ[organ['name']] = [subtype['name'] for subtype in subtypes]
            else:
                cancer_subtypes_by_organ[organ['name']] = []
                
        # Format for the prompt
        organ_types_str = ", ".join([o['name'] for o in organ_types])
        
        # Format subtypes for the prompt
        subtypes_str = ""
        for organ_name, subtypes in cancer_subtypes_by_organ.items():
            if subtypes:
                subtypes_str += f"\n- {organ_name}: {', '.join([s for s in subtypes])}"
            else:
                subtypes_str += f"\n- {organ_name}: No specific subtypes"
    
    except Exception as e:
        logger.error(f"Error fetching cancer types: {str(e)}")
        organ_types_str = "various organs (breast, lung, uterus, ovary, colon, etc.)"
        subtypes_str = "various subtypes"
        
    try:
        logger.info("Analyzing pathology report with OpenAI")
        
        # The prompt for analysis with improved cancer type and staging detection
        prompt = f"""
        You are a medical AI assistant specializing in oncology and pathology reports. 
        You need to extract key medical information from this pathology report, following NCCN guidelines STRICTLY.
        
        Our database contains the following organ types: {organ_types_str}
        
        And these subtypes for each organ: {subtypes_str}
        
        For the given pathology report, extract the following information with great attention to detail:
        
        1. Cancer Organ Type: Identify the specific organ affected from our database list above.
           - Choose EXACTLY ONE of these organ types: {organ_types_str}
           - If the organ is not in our list, choose the closest match
           - If truly not determinable, indicate "Not specified"
        
        2. Cancer Subtype: Identify the specific subtype of cancer within that organ.
           - Choose from the corresponding subtypes for the organ you selected
           - If the subtype is not in our list for that organ, provide your best medical assessment
           - Be as specific as the report allows
        
        3. FIGO Stage: Extract the FIGO staging information if present. Look for:
           - Any mentions of "FIGO" followed by stage numbers/letters (e.g., "FIGO Stage IIIC2")
           - Words like "stage" followed by Roman numerals (I, II, III, IV) with possible subdivisions (A, B, C)
           - Explicit statements about depth of invasion, myometrial invasion, or serosal involvement
           - Descriptions like "confined to endometrium" (typically Stage IA) or "invading outer half of myometrium" (typically Stage IB)
           - If grade information is provided alongside stage, include it
        
        4. Final Pathologic Stage: Extract the final pathologic stage information, including any TNM staging. Look for:
           - TNM notation like "pT1a", "pT2", "pN0", "pN1", "pM0", etc.
           - Tumor size measurements with T-classification (e.g., "T1: tumor ≤ 2cm")
           - Lymph node status (e.g., "lymph nodes negative 0/12" would be N0)
           - Statements about metastasis or distant spread
           - Look for staging summary in "DIAGNOSIS" or "FINAL DIAGNOSIS" sections
        
        5. Recommended Treatment: Based STRICTLY on NCCN guidelines for the identified cancer type and stage. Your recommendations MUST:
           - Be derived EXCLUSIVELY from current NCCN guidelines, not from general knowledge
           - Match the specific cancer type, stage, and any additional factors (like grade, receptor status) identified in the report
           - Include first-line treatment options in a concise format (e.g., "Surgery followed by adjuvant chemotherapy")
           - Mention if there are multiple standard-of-care options per NCCN guidelines
           - Be as specific as possible given the information available
           - If there's not enough information to determine a treatment recommendation, state: "Insufficient information to determine NCCN-based treatment recommendation"
           - DO NOT make recommendations that are not explicitly part of NCCN guidelines
        
        6. Description: Write a brief 1-2 sentence professional summary of the document.
           - Use appropriate medical terminology
           - Be specific about findings
           - Include key diagnostic information
        
        7. Patient Notes: Write 2-4 patient-friendly sentences explaining this document.
           - Use simple, non-technical language
           - Explain medical terms when necessary
           - Be compassionate but factual
           - Explain what the findings mean for the patient
           - Avoid being alarming while still being truthful
           - Include a mention of the recommended treatment approach
        
        IMPORTANT: Examine the document VERY CAREFULLY for staging information. Even if staging is not labeled explicitly, look for clinical descriptions that indicate staging according to NCCN guidelines.
        
        Return your analysis in a structured JSON format with these keys: "cancer_organ_type", "cancer_type", "figo_stage", "final_pathologic_stage", "recommended_treatment", "description", "notes_for_the_patient"
        
        Example JSON response:
        {{
          "cancer_organ_type": "Uterus",
          "cancer_type": "Endometrial endometrioid adenocarcinoma",
          "figo_stage": "FIGO Stage IA",
          "final_pathologic_stage": "pT1a N0 M0",
          "recommended_treatment": "According to NCCN guidelines for Stage IA, Grade 1 endometrial cancer: Total hysterectomy with bilateral salpingo-oophorectomy. Sentinel lymph node mapping/dissection may be considered. No adjuvant therapy is typically needed for low-risk Stage I disease.",
          "description": "Pathology report confirming endometrial adenocarcinoma, FIGO grade 1, with minimal myometrial invasion.",
          "notes_for_the_patient": "This report shows you have a type of cancer in the lining of your uterus. It is early stage and low grade, which generally has a good outlook. The cancer has not spread deeply, which is positive news for your treatment options. Standard treatment typically involves surgery to remove the uterus and ovaries, with excellent outcomes for this stage of disease."
        }}
        """
        print(f'Prompt: {prompt}')
        # Call OpenAI API with o4 reasoning model
        response = openai.responses.create(
            model="o4-mini",
            instructions=prompt,
            input=[{"role": "user", "content": text}],
            reasoning={"effort": "high"}  # ← deepest chain-of-thought
        )
        
        # Extract the response content
        analysis_text = response.output_text
        print(f'Analysis: {analysis_text}')
        print(f'Analysis length: {len(analysis_text)}')
        
        # If we got an empty response, use a simpler fallback
        if not analysis_text or len(analysis_text) < 5:
            logger.warning("Got empty or very short response from AI, using fallback")
            return {
                "cancer_organ_type": "Not specified",
                "cancer_type": "Not specified (AI error)",
                "figo_stage": "Not specified",
                "final_pathologic_stage": "Not specified",
                "recommended_treatment": "Insufficient information to determine NCCN-based treatment recommendation. Your doctor will discuss treatment options based on your full clinical picture.",
                "description": "Pathology report with medical findings.",
                "notes_for_the_patient": "This document contains important medical information. Your doctor will explain what this means for your care.",
                "analysis_text": "AI analysis failed to produce a response"
            }
        
        # Try to parse the JSON response
        try:
            # Find JSON in the response - sometimes the model wraps the JSON in text
            json_start = analysis_text.find('{')
            json_end = analysis_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = analysis_text[json_start:json_end]
                result = json.loads(json_str)
                
                # Validate the expected keys are present
                expected_keys = ["cancer_organ_type", "cancer_type", "figo_stage", "final_pathologic_stage", 
                               "recommended_treatment", "description", "notes_for_the_patient"]
                for key in expected_keys:
                    if key not in result:
                        if key == "description":
                            result[key] = "Pathology report with medical findings."
                        elif key == "notes_for_the_patient":
                            result[key] = "This document contains medical information about your diagnosis. Your doctor will explain what this means for your care."
                        elif key == "recommended_treatment":
                            result[key] = "Insufficient information to determine NCCN-based treatment recommendation. Your doctor will discuss treatment options based on your full clinical picture."
                        else:
                            result[key] = "Not specified"
                
                logger.info(f"Successfully extracted cancer information: {result}")
                return result
            else:
                logger.warning(f"Could not find JSON in OpenAI response: {analysis_text}")
                # Try to create a basic structured response
                return {
                    "cancer_organ_type": "Not specified",
                    "cancer_type": "Not specified",
                    "figo_stage": "Not specified",
                    "final_pathologic_stage": "Not specified",
                    "recommended_treatment": "Insufficient information to determine NCCN-based treatment recommendation. Your doctor will discuss treatment options based on your full clinical picture.",
                    "description": "Pathology report with medical findings.",
                    "notes_for_the_patient": "This document contains important medical information. Your doctor will explain what this means for your care.",
                    "analysis_text": analysis_text
                }
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from OpenAI response: {analysis_text}")
            return {
                "cancer_organ_type": "Not specified",
                "cancer_type": "Not specified",
                "figo_stage": "Not specified",
                "final_pathologic_stage": "Not specified",
                "recommended_treatment": "Insufficient information to determine NCCN-based treatment recommendation. Your doctor will discuss treatment options based on your full clinical picture.",
                "description": "Pathology report with medical findings.",
                "notes_for_the_patient": "This document contains important medical information. Your doctor will explain what this means for your care.",
                "analysis_text": analysis_text
            }
            
    except Exception as e:
        logger.error(f"Error analyzing pathology report: {str(e)}")
        return None


def get_matching_cancer_types(cancer_type_text: str) -> Tuple[Optional['CancerType'], Optional['CancerType']]:
    """
    Find matching cancer types in the database based on text description.

    This function uses a multi-step matching algorithm to identify the most
    appropriate cancer type in the database based on a textual description.
    It employs several matching strategies with confidence scoring:

    1. Text normalization (lowercase, strip whitespace)
    2. Medical terminology standardization (expanding abbreviations, handling synonyms)
    3. Exact match checking (highest confidence)
    4. Partial/substring matching with confidence scoring
    5. Word-level matching for complex descriptions

    The function first attempts to match specific cancer subtypes, then falls back
    to matching organ types if needed. For organ matches, it also tries to find
    the most appropriate subtype if possible.

    Args:
        cancer_type_text: Text describing the cancer type (e.g., "Lung adenocarcinoma")

    Returns:
        Tuple of (organ_type, subtype) CancerType instances, where either may be None
        if no appropriate match is found. If both are None, no match was found.
    """
    try:
        # Lazy import to avoid circular imports
        from django.apps import apps
        from django.db.models import Q
        CancerType = apps.get_model('medical', 'CancerType')

        # Input validation
        if not cancer_type_text or not isinstance(cancer_type_text, str):
            logger.debug("Invalid cancer_type_text input (None or not a string)")
            return None, None

        # ===== STEP 1: TEXT NORMALIZATION =====

        # Normalize the input text
        normalized_text = cancer_type_text.lower().strip()
        logger.debug(f"Normalized cancer type text: '{normalized_text}'")

        # ===== STEP 2: MEDICAL TERMINOLOGY STANDARDIZATION =====

        # Normalize common phrasings
        normalized_text = normalized_text.replace('carcinoma of the ', '')
        normalized_text = normalized_text.replace('carcinoma of ', '')
        normalized_text = normalized_text.replace('cancer of the ', '')
        normalized_text = normalized_text.replace('cancer of ', '')

        # Expand common abbreviations and handle synonyms
        replacements = {
            'scc': 'squamous cell carcinoma',
            'adenoca': 'adenocarcinoma',
            'ca': 'cancer',
            'nsclc': 'non-small cell lung cancer',
            'sclc': 'small cell lung cancer',
            'crc': 'colorectal cancer',
            'hcc': 'hepatocellular carcinoma',
            'rcc': 'renal cell carcinoma',
            'gist': 'gastrointestinal stromal tumor',
        }

        for abbr, full in replacements.items():
            # Only replace if it's a standalone abbreviation (surrounded by spaces or punctuation)
            if f" {abbr} " in f" {normalized_text} " or f"{abbr}," in normalized_text or f"{abbr}." in normalized_text:
                normalized_text = normalized_text.replace(abbr, full)

        logger.debug(f"Standardized cancer type text: '{normalized_text}'")

        # ===== STEP 3: SUBTYPE MATCHING =====

        # First priority: Try to find exact matches for subtypes
        subtypes = CancerType.objects.filter(is_organ=False)

        # Check for exact subtype match first (highest confidence)
        for subtype in subtypes:
            if subtype.name.lower() == normalized_text:
                logger.info(f"Exact subtype match found: {subtype.name}")
                return subtype.parent, subtype

        # ===== STEP 4: SUBTYPE FUZZY MATCHING WITH CONFIDENCE SCORING =====

        matched_subtypes = _score_subtype_matches(subtypes, normalized_text)

        # If we have high confidence subtype matches, use the best one
        if matched_subtypes and matched_subtypes[0][1] >= 60:  # Threshold for good matches
            best_match = matched_subtypes[0][0]
            logger.info(f"Strong subtype match found: {best_match.name} (score: {matched_subtypes[0][1]})")
            return best_match.parent, best_match

        # ===== STEP 5: ORGAN TYPE MATCHING =====

        # If no good subtype matches, try to match organ types
        organs = CancerType.objects.filter(is_organ=True)

        # Check for exact organ match first
        for organ in organs:
            if organ.name.lower() == normalized_text:
                logger.info(f"Exact organ match found: {organ.name}")
                return organ, None

        # ===== STEP 6: ORGAN FUZZY MATCHING WITH CONFIDENCE SCORING =====

        matched_organs = _score_organ_matches(organs, normalized_text)

        # ===== STEP 7: COMBINE MATCHES AND SELECT BEST RESULT =====

        # If we have organ matches, use the best one
        if matched_organs:
            best_match = matched_organs[0][0]
            logger.info(f"Organ match found: {best_match.name} (score: {matched_organs[0][1]})")

            # If we also had some subtype matches but below threshold,
            # check if any belong to this organ to improve specificity
            if matched_subtypes:
                for subtype, score in matched_subtypes:
                    if subtype.parent == best_match:
                        logger.info(f"Found matching subtype {subtype.name} for organ {best_match.name}")
                        return best_match, subtype

            return best_match, None

        # No matches found
        logger.info(f"No cancer type match found for: {cancer_type_text}")
        return None, None
    except Exception as e:
        logger.error(f"Error matching cancer types: {str(e)}")
        return None, None


def _score_subtype_matches(subtypes: List['CancerType'], normalized_text: str) -> List[Tuple['CancerType', float]]:
    """
    Score potential subtype matches based on various matching strategies.

    This helper function implements the confidence scoring algorithm for
    cancer subtypes, considering exact matches, substring containment,
    and word-level matching with appropriate weighting.

    Args:
        subtypes: List of CancerType objects to check against
        normalized_text: The normalized cancer type text to match

    Returns:
        List of (subtype, score) tuples, sorted by score descending
    """
    matched_subtypes = []

    for subtype in subtypes:
        subtype_name = subtype.name.lower()
        # Score the match (higher is better)
        score = 0

        # Exact match would be highest (this is a redundant check but kept for completeness)
        if subtype_name == normalized_text:
            score = 100
        # Subtype contains the full search text
        elif normalized_text in subtype_name:
            # Weight by how much of the subtype name is matched
            score = 80 + (len(normalized_text) / len(subtype_name) * 20)
        # Search text contains the full subtype name
        elif subtype_name in normalized_text:
            # Weight by how specific the match is compared to the search text
            score = 70 + (len(subtype_name) / len(normalized_text) * 20)
        # Partial word matches (if at least 4 chars)
        elif len(subtype_name) >= 4 and len(normalized_text) >= 4:
            # Word-by-word matching
            subtype_words = subtype_name.split()
            search_words = normalized_text.split()

            matching_words = 0
            for s_word in search_words:
                if len(s_word) < 4:  # Skip short words
                    continue
                for t_word in subtype_words:
                    if len(t_word) < 4:  # Skip short words
                        continue
                    if s_word in t_word or t_word in s_word:
                        matching_words += 1

            # Only consider word matches if we found some
            if matching_words > 0:
                # Weight by the proportion of matching words relative to total words
                score = 40 + (matching_words / max(len(subtype_words), len(search_words)) * 30)

        # Add to matches if we have a non-zero score
        if score > 0:
            matched_subtypes.append((subtype, score))

    # Sort by score descending
    matched_subtypes.sort(key=lambda x: x[1], reverse=True)
    return matched_subtypes


def _score_organ_matches(organs: List['CancerType'], normalized_text: str) -> List[Tuple['CancerType', float]]:
    """
    Score potential organ matches based on various matching strategies.

    This helper function implements the confidence scoring algorithm for
    cancer organ types, with specialized handling for organ names which
    tend to be shorter and more common than subtype names.

    Args:
        organs: List of CancerType organ objects to check against
        normalized_text: The normalized cancer type text to match

    Returns:
        List of (organ, score) tuples, sorted by score descending
    """
    matched_organs = []

    for organ in organs:
        organ_name = organ.name.lower()
        # Score the match (higher is better)
        score = 0

        # Exact match would be highest (redundant but complete)
        if organ_name == normalized_text:
            score = 100
        # Text contains organ name as a whole word - very strong signal
        elif f" {organ_name} " in f" {normalized_text} ":
            score = 90
        # Organ contains the full search text
        elif normalized_text in organ_name:
            score = 80 + (len(normalized_text) / len(organ_name) * 20)
        # Search text contains the full organ name
        elif organ_name in normalized_text:
            score = 70 + (len(organ_name) / len(normalized_text) * 20)
        # Word-level matching
        else:
            organ_words = organ_name.split()
            search_words = normalized_text.split()

            matching_words = 0
            for o_word in organ_words:
                if len(o_word) < 3:  # Skip very short words
                    continue
                for s_word in search_words:
                    if len(s_word) < 3:  # Skip very short words
                        continue
                    # For organs, require exact word matches (more strict)
                    if o_word == s_word:
                        matching_words += 1

            # Only consider word matches if we found some
            if matching_words > 0:
                # Weight by proportion of matching words
                score = 50 + (matching_words / max(len(organ_words), len(search_words)) * 30)

        # Add to matches if we have a non-zero score
        if score > 0:
            matched_organs.append((organ, score))

    # Sort by score descending
    matched_organs.sort(key=lambda x: x[1], reverse=True)
    return matched_organs


def generate_document_metadata(text: str, filename: str) -> Dict[str, Any]:
    """
    Generate metadata for a document using AI.
    
    Args:
        text: The extracted text content
        filename: Original filename for context
        
    Returns:
        Dictionary with generated metadata (title, type, description, notes, language)
    """
    if not text or len(text) < 50:
        # Not enough text to analyze
        return {
            "title": filename,
            "document_type": "Unknown",
            "description": "Document could not be analyzed.",
            "patient_notes": "",
            "language": "en",
            "cancer_type_text": ""
        }
    
    if not openai.api_key:
        logger.error("OpenAI API key not configured")
        return {
            "title": filename,
            "document_type": "Unknown",
            "description": "Document could not be analyzed due to API configuration.",
            "patient_notes": "",
            "language": "en",
            "cancer_type_text": ""
        }
    
    try:
        logger.info("Generating document metadata using OpenAI")
        
        # Truncate text if it's too long to avoid token limits
        analysis_text = text[:8000]
        
        # The prompt for metadata generation with enhanced cancer type detection
        prompt = """
        You are a medical AI assistant that helps healthcare professionals organize medical documents.
        Given the content of a medical document, provide the following metadata:
        
        1. Document Title: A concise, descriptive title based on the content (max 100 chars)
        
        2. Document Type: The type of medical document (e.g., Pathology Report, Lab Results, Imaging Report, Clinical Note, etc.)
        
        3. Description: A brief 1-2 sentence professional summary of the document's content written for healthcare providers. 
           This should use appropriate medical terminology and be specific about findings.
        
        4. Patient Notes: Write 3-4 patient-friendly sentences explaining the key information in this document.
           IMPORTANT GUIDELINES FOR PATIENT NOTES:
           - Use simple, non-technical language that a person without medical training can understand
           - Avoid medical jargon - when you must use medical terms, briefly explain what they mean
           - Be compassionate but factual in tone
           - If a cancer diagnosis is mentioned, explain it clearly without being alarming
           - Mention if there are any next steps indicated in the document (like further tests or treatment options)
           - Don't oversimplify to the point of being vague - patients need clear information
        
        5. Language: The ISO 639-1 code of the document's primary language (e.g., en, es, fr)
        
        6. Cancer Type: If the document mentions a specific cancer type, identify it as precisely as possible with these guidelines:
           - Be as specific as possible about both the organ affected and the cancer subtype
           - Specify the organ (e.g., breast, lung, uterus, ovary, colon, etc.) first
           - Then specify the histologic subtype if available (e.g., adenocarcinoma, squamous cell, etc.)
           - Example format: "Endometrial adenocarcinoma" or "Ovarian serous carcinoma"
           - If no cancer type is mentioned, leave this field empty
        
        Return your analysis in a structured JSON format with these keys: "title", "document_type", "description", "patient_notes", "language", "cancer_type_text"
        
        Example JSON response:
        {
          "title": "Endometrial Biopsy Pathology Report - University Hospital",
          "document_type": "Pathology Report",
          "description": "Pathology report confirming endometrial adenocarcinoma, FIGO grade 1, with myometrial invasion < 50%.",
          "patient_notes": "This report confirms a diagnosis of endometrial cancer that is early stage and low grade. The cancer has not spread deeply into the uterine wall.",
          "language": "en",
          "cancer_type_text": "Endometrial adenocarcinoma"
        }
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="o3",  # Using o3 reasoning model
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": analysis_text}
            ],
            max_completion_tokens=500,
        )
        
        # Extract the response content
        analysis_text = response.choices[0].message.content.strip()
        print(f'Analysis response: {analysis_text}')
        print(f'Metadata analysis response length: {len(analysis_text)}')
        
        # If we got an empty response, use fallback metadata
        if not analysis_text or len(analysis_text) < 5:
            logger.warning("Got empty or very short metadata response from AI, using fallback")
            return {
                "title": filename,
                "document_type": "Medical Document",
                "description": "Document analysis failed. Please review manually.",
                "patient_notes": "This document contains medical information. Please ask your healthcare provider for details.",
                "language": "en",
                "cancer_type_text": ""
            }
            
        # Try to parse the JSON response
        try:
            # Find JSON in the response
            json_start = analysis_text.find('{')
            json_end = analysis_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = analysis_text[json_start:json_end]
                result = json.loads(json_str)
                
                # Validate and provide defaults for missing fields
                defaults = {
                    "title": filename,
                    "document_type": "Medical Document",
                    "description": "This appears to be a medical document related to patient diagnosis.",
                    "patient_notes": "This document contains important medical information. Please discuss with your healthcare provider for a detailed explanation.",
                    "language": "en",
                    "cancer_type_text": ""
                }
                
                for key, default_value in defaults.items():
                    if key not in result or not result[key]:
                        result[key] = default_value
                        
                # Ensure title is not too long
                if len(result["title"]) > 100:
                    result["title"] = result["title"][:97] + "..."
                
                logger.info(f"Successfully generated document metadata")
                return result
            else:
                logger.warning(f"Could not find JSON in OpenAI response: {analysis_text}")
                return {
                    "title": filename,
                    "document_type": "Medical Document",
                    "description": "Medical document related to patient care.",
                    "patient_notes": "This document contains medical information about your care.",
                    "language": "en",
                    "cancer_type_text": ""
                }
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from OpenAI response")
            return {
                "title": filename,
                "document_type": "Medical Document",
                "description": "Medical document related to patient care.",
                "patient_notes": "This document contains medical information about your care.",
                "language": "en",
                "cancer_type_text": ""
            }
    except Exception as e:
        logger.error(f"Error generating document metadata: {str(e)}")
        return {
            "title": filename,
            "document_type": "Unknown",
            "description": "Document could not be analyzed.",
            "patient_notes": "",
            "language": "en",
            "cancer_type_text": ""
        }


def process_document_for_analysis(file_path: str) -> Tuple[Optional[Dict[str, Any]], str, Dict[str, Any]]:
    """
    Process a document for AI analysis:
    1. Extract text from PDF
    2. Generate document metadata and detect cancer type
    3. Check if it's a pathology report and analyze it if applicable
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Tuple of (pathology_analysis_result, extracted_text, document_metadata)
    """
    # Extract text from PDF
    extracted_text = extract_text_from_pdf(file_path)
    
    if not extracted_text:
        logger.warning(f"Could not extract text from {file_path}")
        return None, "", {
            "title": os.path.basename(file_path),
            "document_type": "Unknown",
            "description": "Document could not be analyzed.",
            "patient_notes": "",
            "language": "en",
            "cancer_type_text": ""
        }
    
    # Generate metadata for the document regardless of type
    import os
    filename = os.path.basename(file_path)
    metadata = generate_document_metadata(extracted_text, filename)
    
    # Track if we found cancer types to include in metadata 
    cancer_types_found = False
    
    # Check if it's a pathology report
    pathology_analysis = None
    cancer_info = ""
    
    if is_pathology_report(extracted_text):
        # Analyze the pathology report
        pathology_analysis = analyze_pathology_report(extracted_text)
        
        # If we have pathology data, enhance the metadata with detailed information
        if pathology_analysis and metadata:
            # Extract all the new fields from the pathology analysis
            cancer_organ_type = pathology_analysis.get('cancer_organ_type')
            cancer_type = pathology_analysis.get('cancer_type')
            figo_stage = pathology_analysis.get('figo_stage')
            pathologic_stage = pathology_analysis.get('final_pathologic_stage')
            recommended_treatment = pathology_analysis.get('recommended_treatment')
            description = pathology_analysis.get('description')
            patient_notes = pathology_analysis.get('notes_for_the_patient')
            
            # Update the metadata with the new fields
            if cancer_type and cancer_type != "Not specified":
                metadata['cancer_type_text'] = cancer_type
                cancer_types_found = True
                cancer_info = cancer_type
            
            # Use the AI-generated description if available
            if description and description != "Not specified":
                metadata['description'] = description
                
            # Use the AI-generated patient notes if available
            if patient_notes and patient_notes != "Not specified":
                metadata['patient_notes'] = patient_notes
                
            # Add the NCCN-based recommended treatment
            if recommended_treatment and recommended_treatment != "Not specified":
                metadata['recommended_treatment'] = recommended_treatment
                
            # Store the cancer organ type and other info for matching later
            metadata['cancer_organ_type'] = cancer_organ_type
            metadata['figo_stage'] = figo_stage
            metadata['final_pathologic_stage'] = pathologic_stage
    
    # If no cancer type was found in pathology analysis but AI identified a cancer type in metadata
    if not cancer_types_found and metadata.get('cancer_type_text'):
        cancer_info = metadata['cancer_type_text']
        cancer_types_found = True
    
    # Log the detected cancer type
    if cancer_types_found:
        logger.info(f"Detected cancer type: {cancer_info}")
    
    return pathology_analysis, extracted_text, metadata