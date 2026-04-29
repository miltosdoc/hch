import sys
import doc_parser

# Path provided by the user
test_file = r"\\HJ-VAR-DT01\Pictures\2026Scan\2026-03-30_115512\Kvitto_2026-03-30_115445 (3).jpg"

try:
    print(f"Testing OCR on: {test_file}")
    
    # 1. First print the raw Tesseract text so we know EXACTLY what it sees
    print("--- RAW OCR TEXT ---")
    raw_text = doc_parser.extract_text_from_image(test_file)
    print(raw_text)
    print("--------------------")
    
    # 2. Try the full parse pipeline
    result = doc_parser.parse_document(test_file)
    print("\n--- EXTRACTION RESULTS ---")
    print("Personnummer:", result.get('personnummer'))
    print("Referral Date:", result.get('referral_date'))
    print("Phone Number:", result.get('phone_number'))
    
except Exception as e:
    print("Error:", e)
