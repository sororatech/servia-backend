"""
Text extraction service for CVs with OCR fallback.
"""
import os
import logging
import tempfile
from django.conf import settings

logger = logging.getLogger(__name__)

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
    """Extract text directly from PDF using pdfminer."""
    if not pdfminer_extract:
        return ""
    try:
        text = pdfminer_extract(file_path)
        return text.strip() if text else ""
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        return ""


def extract_text_from_image(file_path):
    """Extract text from image using Tesseract OCR."""
    if not pytesseract or not Image:
        return ""
    try:
        if hasattr(settings, 'TESSERACT_PATH'):
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
        else:
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip() if text else ""
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return ""


def extract_text_from_scanned_pdf(file_path):
    """Convert PDF pages to images, then run OCR."""
    if not convert_from_path or not pytesseract:
        return ""
    
    try:
        if hasattr(settings, 'TESSERACT_PATH'):
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
        else:
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        images = convert_from_path(file_path)
        all_text = []
        
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            if text.strip():
                all_text.append(f"--- Page {i+1} ---\n{text}")
        
        return "\n\n".join(all_text)
    except Exception as e:
        logger.error(f"Scanned PDF OCR failed: {e}")
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
        text = extract_text_from_pdf(file_path)
        if text and len(text) > 100:
            logger.info(f"PDF text extracted directly: {len(text)} chars")
            return text
        
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
    
    return ""