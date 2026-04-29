import sys
import os
from PIL import Image
import pytesseract
import shutil

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
    img = Image.open(test_file)
    print("--- DEFAULT (NO LANG) ---")
    try:
        print(pytesseract.image_to_string(img)[0:1000])
    except Exception as e:
        print("Failed without lang:", e)
        
    print("\n--- SWE LANG ---")
    try:
        print(pytesseract.image_to_string(img, lang='swe')[0:1000])
    except Exception as e:
        print("Failed with swe lang:", e)
        
except Exception as e:
    print("Error:", e)
