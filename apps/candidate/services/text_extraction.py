"""
Text extraction service for CVs with OCR fallback.
"""
import os
import platform
import logging
import tempfile
import textract
from django.conf import settings

logger = logging.getLogger(__name__)


def get_poppler_path():
    """Get Poppler path from settings, env var, or OS-specific default."""
    # Try settings first
    if hasattr(settings, 'POPPLER_BIN'):
        return settings.POPPLER_BIN
    
    # Try environment variable
    env_path = os.getenv('POPPLER_PATH')
    if env_path:
        return env_path
    
    # OS-specific defaults
    system = platform.system()
    if system == 'Windows':
        return r'C:\Program Files\poppler\Library\bin'
    elif system == 'Darwin':  # macOS
        return '/usr/local/bin'
    else:  # Linux
        return '/usr/bin'


def get_tesseract_path():
    """Get Tesseract path from settings, env var, or OS-specific default."""
    # Try settings first
    if hasattr(settings, 'TESSERACT_PATH'):
        return settings.TESSERACT_PATH
    
    # Try environment variable
    env_path = os.getenv('TESSERACT_PATH')
    if env_path:
        return env_path
    
    # OS-specific defaults
    system = platform.system()
    if system == 'Windows':
        return r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    elif system == 'Darwin':  # macOS
        return '/usr/local/bin/tesseract'
    else:  # Linux
        return '/usr/bin/tesseract'


try:
    from pdfminer.high_level import extract_text as pdfminer_extract
except ImportError:
    pdfminer_extract = None
    logger.warning("pdfminer not installed")

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None
    logger.warning("pytesseract or PIL not installed")

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None
    logger.warning("pdf2image not installed")


def extract_text_from_pdf(file_path):
    """Extract text from PDF using pdfminer (for text-based PDFs)."""
    if not pdfminer_extract:
        logger.warning("pdfminer not available")
        return ""
    
    try:
        text = pdfminer_extract(file_path)
        return text.strip() if text else ""
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        return ""


def extract_text_from_scanned_pdf(file_path):
    """Convert PDF pages to images, then run OCR."""
    if not convert_from_path or not pytesseract:
        logger.error("pdf2image or pytesseract not available for OCR")
        return ""
    
    poppler_path = get_poppler_path()
    tesseract_path = get_tesseract_path()
    
    # Optional validation (can be removed for flexibility)
    if poppler_path and not os.path.exists(poppler_path):
        logger.warning(f"Poppler path not found: {poppler_path}, attempting auto-detection")
        poppler_path = None  # Let pdf2image try to auto-detect
    
    try:
        # Set Tesseract path
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        logger.info(f"Using Tesseract at: {tesseract_path}")
        
        # Convert PDF to images
        logger.info(f"Converting PDF to images with Poppler at: {poppler_path or 'auto-detect'}")
        images = convert_from_path(file_path, poppler_path=poppler_path)
        
        # Extract text from each page
        all_text = []
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            if text.strip():
                all_text.append(f"--- Page {i+1} ---\n{text}")
        
        result = "\n\n".join(all_text)
        logger.info(f"OCR extracted {len(result)} chars from scanned PDF")
        return result
        
    except Exception as e:
        logger.error(f"Scanned PDF OCR failed: {e}")
        return ""

def extract_text_from_doc(file_path):
    """Extract text from .doc file using textract."""
    try:
        text = textract.process(file_path).decode('utf-8')
        return text.strip()
    except Exception as e:
        logger.error(f"textract failed for .doc file {file_path}: {e}")
        return ""

def extract_text_from_image(file_path):
    """Extract text from image using Tesseract OCR."""
    if not pytesseract or not Image:
        logger.error("pytesseract or PIL not available")
        return ""
    
    tesseract_path = get_tesseract_path()
    
    try:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        logger.info(f"Using Tesseract at: {tesseract_path}")
        
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip() if text else ""
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return ""


def extract_cv_text(file_path, file_extension):
    """
    Main function to extract text from CV with OCR fallback.
    
    Args:
        file_path: Path to the uploaded file
        file_extension: 'pdf', 'jpg', 'jpeg', 'png', 'docx'
    
    Returns:
        Extracted text string
    """
    file_extension = file_extension.lower()
    logger.info(f"Extracting text from {file_extension} file: {file_path}")
    
    if file_extension == 'pdf':
        # Try direct text extraction first
        text = extract_text_from_pdf(file_path)
        if text and len(text) > 100:
            logger.info(f"PDF text extracted directly: {len(text)} chars")
            return text
        
        # Fallback to OCR for scanned PDFs
        logger.info("No text found in PDF, trying OCR...")
        text = extract_text_from_scanned_pdf(file_path)
        if text:
            logger.info(f"OCR extracted from scanned PDF: {len(text)} chars")
            return text
        return ""
    
    elif file_extension in ['jpg', 'jpeg', 'png']:
        text = extract_text_from_image(file_path)
        if text:
            logger.info(f"OCR extracted from image: {len(text)} chars")
            return text
        return ""
    
    elif file_extension == 'docx':
        try:
            from docx import Document
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            if text and len(text) > 50:
                logger.info(f"DOCX text extracted: {len(text)} chars")
                return text
        except ImportError:
            logger.warning("python-docx not installed")
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
        return ""
    elif file_extension == 'doc':
        text = extract_text_from_doc(file_path)
        if text:
            logger.info(f"DOC text extracted via textract: {len(text)} chars")
            return text
        return ""
    return ""