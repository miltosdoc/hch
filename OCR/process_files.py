import os
import re
import glob
import sys
from PIL import Image
try:
    import pytesseract
except ImportError:
    print("Error: pytesseract is not installed. Please run 'pip install pytesseract'.")
    sys.exit(1)

# Attempt to locate tesseract executable commonly on Windows
tesseract_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
    os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
]

tesseract_cmd = "tesseract" # Default code
found_tesseract = False

# Check if 'tesseract' is in PATH
import shutil
if shutil.which("tesseract"):
    found_tesseract = True
else:
    for path in tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            found_tesseract = True
            print(f"Using Tesseract at: {path}")
            break

if not found_tesseract:
    print("WARNING: Tesseract executable not found in PATH or common locations.")
    print("Please install Tesseract-OCR from https://github.com/UB-Mannheim/tesseract/wiki")
    print("Or ensure it is in your PATH.")
    # We will proceed, but pytesseract will likely raise an error if called.

def extract_personnummer(text):
    # Regex to capture personnummer.
    # Supported formats: YYYYMMDD-XXXX, YYMMDD-XXXX, YYYYMMDDXXXX, YYMMDDXXXX
    # Also handles '+' separator.
    # Regex breakdown:
    # \b indicates word boundary
    # ((?:18|19|20)?\d{2}) Year: Optional century (18, 19, 20) followed by 2 digits, or just 2 digits.
    # (\d{2}) Month
    # (\d{2}) Day
    # ([-+]?) Separator (optional)
    # (\d{4}) Last 4 digits
    # \b
    
    pattern = r'\b((?:19|20)?\d{2})(\d{2})(\d{2})([-+]?)(\d{4})\b'
    
    # Simple search
    match = re.search(pattern, text)
    if match:
        # Normalize to 12 digits: YYYYMMDDXXXX
        
        # Groups:
        # 1: Year (YY or YYYY)
        # 2: Month
        # 3: Day
        # 4: Separator
        # 5: Last 4
        
        year_part = match.group(1)
        month = match.group(2)
        day = match.group(3)
        separator = match.group(4)
        last_four = match.group(5)
        
        full_year = year_part
        
        # If year is 2 digits, guess century
        if len(year_part) == 2:
            val = int(year_part)
            # Assumption: We are dealing with standard personal numbers.
            # Current year approx 2025/2026.
            # If val > 26 (current short year approx), assume 19xx
            # If val <= 26, assume 20xx
            # Adjust based on separator if needed (separator '+' often means >100 years old)
            
            # Simple heuristic for now:
            if val > 26:
                full_year = "19" + year_part
            else:
                full_year = "20" + year_part
                
        # Return purely digits: YYYYMMDDXXXX
        normalized = f"{full_year}{month}{day}{last_four}"
        return normalized
    return None

def get_unique_filename(base_name, ext, original_filename):
    # If the new name is the same as the old name, we don't need to rename (or we do nothing).
    # But here we are renaming TO the personnummer.
    
    # First try the exact personnummer
    candidate = f"{base_name}{ext}"
    if candidate.lower() == original_filename.lower():
         return None # No change needed, or handle as "already named correctly"
    
    if not os.path.exists(candidate):
        return candidate
    
    # Add A, B, C...
    suffixes = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for char in suffixes:
        candidate = f"{base_name}{char}{ext}"
        if candidate.lower() == original_filename.lower():
            return None 
        if not os.path.exists(candidate):
            return candidate
            
    # Fallback
    i = 1
    while True:
        candidate = f"{base_name}_{i}{ext}"
        if candidate.lower() == original_filename.lower():
            return None
        if not os.path.exists(candidate):
            return candidate
        i += 1

def process_images():
    # Find all jpg and jpeg files
    # De-duplicate list handling Windows case-insensitivity
    seen = set()
    unique_files = []
    # glob returns paths, they might be duplicates if we ignore case
    raw_files = glob.glob("*.jpg") + glob.glob("*.jpeg") + glob.glob("*.JPG") + glob.glob("*.JPEG")
    
    for f in raw_files:
        if f.lower() not in seen:
            seen.add(f.lower())
            unique_files.append(f)
            
    files = sorted(unique_files)
    
    if not files:
        print("No JPG/JPEG files found in the current directory.")
        return

    print(f"Found {len(files)} files to process.")

    for file_path in files:
        print(f"Processing: {file_path}...")
        try:
            image = Image.open(file_path)
            # Perform OCR
            text = pytesseract.image_to_string(image)
            
            pnr = extract_personnummer(text)
            
            if pnr:
                print(f"  Found Personnummer: {pnr}")
                # Clean pnr for filename (remove invalid chars if any, though regex implies basic chars)
                # Windows filenames can't match: < > : " / \ | ? *
                # Our regex matches digits and - +, so it should be safe.
                
                base_name = pnr
                ext = os.path.splitext(file_path)[1]
                
                new_filename = get_unique_filename(base_name, ext, file_path)
                
                if new_filename:
                    print(f"  Renaming to: {new_filename}")
                    image.close() # Ensure file is closed before renaming
                    os.rename(file_path, new_filename)
                else:
                    print("  File already named correctly or collision prevented rename.")
            else:
                print("  No Personnummer found in file.")
        except Exception as e:
            print(f"  Error processing file {file_path}: {e}")

if __name__ == "__main__":
    process_images()
