"""
Document Parser: OCR-based date extraction from JPG files.

Extracts:
- Remissdatum (referral date) from Vårdbegäran documents
- Vårdgarantisedel date from Vårdgaranti documents
- Personnummer from document body text
- Telefonnummer (phone number) from document body text
"""

import re
import os
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
    
    import shutil
    if not shutil.which("tesseract"):
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
        ]
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
except ImportError:
    HAS_OCR = False
    print("Warning: pytesseract or Pillow not installed. OCR extraction disabled.")


# Common Swedish date pattern: YYYY-MM-DD
DATE_PATTERN = r'(\d{4}-\d{2}-\d{2})'

# Personnummer patterns
PN_PATTERN = r'\b((?:19|20)?\s*\d{6})[-\s]?(\d{4})\b'


def extract_text_from_image(filepath):
    """Extract text from an image file using Tesseract OCR."""
    if not HAS_OCR:
        return ""
    
    try:
        img = Image.open(filepath)
        # Use Swedish language if available, fallback to default
        try:
            text = pytesseract.image_to_string(img, lang='swe')
        except:
            text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        print(f"OCR extraction failed for {filepath}: {e}")
        return ""


def extract_referral_date(text):
    """
    Extract Remissdatum from Vårdbegäran document text.
    Looks for patterns like:
      - Remissdatum: 2025-09-29
      - Remiggdatum: 2025-09-29 (OCR error)
    """
    # Try exact match or slight OCR misspellings
    match = re.search(r'[Rr]emi[a-z]{0,2}datum[:\s]+' + DATE_PATTERN, text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Fallback: look for date near "Remiss" keyword
    match = re.search(r'[Rr]emiss.*?' + DATE_PATTERN, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1)
    
    return None


def extract_vardgaranti_date(text):
    """
    Extract date from Vårdgarantisedel document.
    """
    # Primary: check for "Giltig Från" line
    match = re.search(r'[Gg]iltig\s+[Ff]r[aå]n\s*[:\s]+' + DATE_PATTERN, text, re.IGNORECASE)
    if match:
        return match.group(1)
        
    # Secondary: check for explicitly matching close to Vardgarantisedel
    match = re.search(r'[Vv][aå]rdgarantisedel[\s\n]+' + DATE_PATTERN, text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Fallback: find any date soon after "Vardgaranti"
    match = re.search(r'[Vv][aå]rdgaranti.*?' + DATE_PATTERN, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1)
    
    return None


def extract_personnummer_from_text(text):
    """Extract personnummer from document body text."""
    matches = re.findall(PN_PATTERN, text)
    if matches:
        # Just use the first valid match we find
        for p1, p2 in matches:
            p1_clean = re.sub(r'\s+', '', p1)
            if len(p1_clean) == 6:
                century = "19" if int(p1_clean[:2]) > 30 else "20"
                p1_clean = f"{century}{p1_clean}"
            return f"{p1_clean}-{p2}"
    return None


def extract_phone_number(text):
    """
    Extract phone number from document text.
    Patterns:
      - Telefonnummer: +46706764004
      - Telefonnummer: 0706764004
      - Tel: 070-676 40 04
      - Mobilnummer: 0720233343
    """
    # Look for labeled phone numbers first
    match = re.search(r'(?:Telefonnummer|Mobilnummer|Tel\.?|Mobil)[:\s]+([+\d][\d\s-]{7,})', text)
    if match:
        phone = re.sub(r'[\s-]', '', match.group(1).strip())
        return phone
    
    # Fallback: look for Swedish phone number patterns, making sure it's not embedded inside a larger number (like a Personnummer)
    match = re.search(r'(?<!\d)(\+46[\d\s-]{8,15}|0[7]\d[\d\s-]{6,10})(?!\d)', text)
    if match:
        phone = re.sub(r'[\s-]', '', match.group(1).strip())
        # Ensure it's not just part of a personnummer that slipped through
        if len(phone) >= 8 and len(phone) <= 15:
            return phone
    
    return None


def detect_document_type(text):
    """
    Auto-detect document type from content.
    Returns: 'vardbegararan' | 'vardgarantisedel' | 'unknown'
    """
    text_lower = text.lower()
    
    if 'vårdbegäran' in text_lower or 'remissdatum' in text_lower:
        return 'vardbegararan'
    elif 'vårdgarantisedel' in text_lower or 'vårdgaranti' in text_lower:
        return 'vardgarantisedel'
    else:
        return 'unknown'


def parse_document(filepath):
    """
    Parse a document file and extract all relevant data.
    
    Returns dict:
    {
        'personnummer': str or None,
        'referral_date': str or None,
        'vardgaranti_date': str or None,
        'doc_type': str,
        'raw_text': str,
        'ocr_success': bool
    }
    """
    result = {
        'personnummer': None,
        'referral_date': None,
        'vardgaranti_date': None,
        'phone_number': None,
        'doc_type': 'unknown',
        'raw_text': '',
        'ocr_success': False
    }
    
    filepath = Path(filepath)
    ext = filepath.suffix.lower()
    
    # Only process image files
    if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']:
        text = extract_text_from_image(filepath)
    else:
        # For PDFs or other formats, skip OCR for now
        return result
    
    if not text.strip():
        return result
    
    result['raw_text'] = text
    result['ocr_success'] = True
    
    # Detect document type
    result['doc_type'] = detect_document_type(text)
    
    # Extract personnummer
    result['personnummer'] = extract_personnummer_from_text(text)
    
    # Extract phone number
    result['phone_number'] = extract_phone_number(text)
    
    # Extract dates based on document type
    if result['doc_type'] == 'vardbegararan':
        result['referral_date'] = extract_referral_date(text)
    elif result['doc_type'] == 'vardgarantisedel':
        result['vardgaranti_date'] = extract_vardgaranti_date(text)
    else:
        # Try both
        result['referral_date'] = extract_referral_date(text)
        result['vardgaranti_date'] = extract_vardgaranti_date(text)
    
    return result
