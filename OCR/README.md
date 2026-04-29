# Personnummer Renamer

This tool scans all `.jpg` and `.jpeg` images in the current directory, detects Swedish personal identity numbers (Personnummer) using OCR (Optical Character Recognition), and renames the files to match the found Personnummer (e.g., `19900101-1234.jpg`).

## Prerequisites

### 1. Python
You need Python installed on your system.
- Download and install from [python.org](https://www.python.org/downloads/).
- **Important:** During installation, check the box **"Add Python to PATH"**.

### 2. Tesseract-OCR
This script relies on Tesseract for reading text from images.
- **Windows:**
    - Download the installer from [UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki).
    - Run the installer.
    - The script automatically looks for Tesseract in standard locations (e.g., `C:\Program Files\Tesseract-OCR`).

## Installation & Usage

### Option 1: Using the Batch File (Recommended)
1.  Place `process_files.py` and `run_process.bat` in the folder containing your images.
2.  Double-click `run_process.bat`.
    - It will automatically install the necessary Python libraries (`Pillow`, `pytesseract`).
    - It will then run the script and rename your files.
    - **Note:** This works even on network shares (UNC paths like `\\Server\Share\Folder`).

### Option 2: Manual Setup
1.  Open a terminal/command prompt in the folder.
2.  Install dependencies:
    ```bash
    pip install Pillow pytesseract
    ```
3.  Run the script:
    ```bash
    python process_files.py
    ```

## Troubleshooting
- **"Tesseract is not installed/found"**: Ensure Tesseract-OCR is installed. If you installed it to a custom location, you may need to add that location to your system `PATH` or edit `process_files.py` to include your custom path.
- **"File not found" errors**: Ensure you are running the script in the same directory as the images.
