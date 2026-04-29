import os
import shutil
import pytesseract
from PIL import Image

# Find tesseract
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

test_file = r"\\HJ-VAR-DT01\Pictures\2026Scan\2026-03-30_115512\Kvitto_2026-03-30_115437.jpg"

try:
    print(f"Testing on {test_file}")
    img = Image.open(test_file)
    
    print("\n--- TEST 1: RAW IMAGE, NO LANG ---")
    print(pytesseract.image_to_string(img)[:500])
    
    print("\n--- TEST 2: GRAYSCALE + THRESHOLD, NO LANG ---")
    # Convert to grayscale
    gray = img.convert('L')
    # Threshold: make everything darker than 150 black (0), everything lighter white (255)
    # The watermark is light gray, so it should turn white and disappear!
    bw = gray.point(lambda x: 0 if x < 150 else 255, '1')
    
    text_bw = pytesseract.image_to_string(bw)
    
    import re
    pat = r'\b((?:19|20)?\s*\d{6})[-\s]?(\d{4})\b'
    matches = re.findall(pat, text_bw)
    
    print("Extracted Text Snippet:")
    print(text_bw[:500])
    print(f"\nFound Pattern? {matches}")

except Exception as e:
    print("Error:", e)
