import sys
import os
sys.path.append(r"c:\Users\Miltiadis.t\Desktop\WebdocAPI\OCR")
import process_files
from PIL import Image
import pytesseract

img = Image.open(r"\\HJ-VAR-DT01\Pictures\2026Scan\2026-03-30_115512\Kvitto_2026-03-30_115437.jpg")
text = pytesseract.image_to_string(img)
pn = process_files.extract_personnummer(text)
print("TEXT:")
print(text[:500])
print("\nPN extracted:", pn)
