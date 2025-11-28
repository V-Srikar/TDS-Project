import os
import requests
import pandas as pd
import pdfplumber
import subprocess
import sys
import traceback
import base64
import uuid
import pytesseract
from PIL import Image
from io import BytesIO
import speech_recognition as sr
from pydub import AudioSegment

# Global store for Base64 images to avoid context bloat
BASE64_STORE = {}

# ---------------------------------------------------------------------------
# FILE OPERATIONS
# ---------------------------------------------------------------------------
def download_file(url: str, dest_folder: str = ".") -> str:
    """Downloads a file from a URL to the specified folder."""
    try:
        os.makedirs(dest_folder, exist_ok=True)
        local_filename = url.split('/')[-1]
        if '?' in local_filename:
            local_filename = local_filename.split('?')[0]
        
        path = os.path.join(dest_folder, local_filename)
        
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return path
    except Exception as e:
        return f"Error downloading file: {str(e)}"

def read_file_content(file_path: str) -> str:
    """Reads content based on file extension."""
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found."
    
    ext = file_path.split('.')[-1].lower()
    
    if ext == 'pdf':
        return read_pdf(file_path)
    elif ext in ['csv', 'xls', 'xlsx']:
        return read_csv_summary(file_path)
    elif ext in ['png', 'jpg', 'jpeg', 'webp', 'gif']:
        return "Image file. Use `ocr_image` to read text or `encode_image_to_base64` to process it."
    elif ext in ['mp3', 'wav']:
        return "Audio file. Use `transcribe_audio` to convert to text."
    elif ext in ['txt', 'md', 'json', 'html', 'xml']:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading text file: {str(e)}"
    else:
        return f"Error: Unsupported file type {ext}"

def read_pdf(file_path: str) -> str:
    """Extracts text and tables from a PDF."""
    text_content = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    text_content.append(f"--- Page {i+1} ---")
                    text_content.append(text)
                
                tables = page.extract_tables()
                if tables:
                    text_content.append(f"--- Tables on Page {i+1} ---")
                    for table in tables:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        text_content.append(df.to_markdown())
        return "\n".join(text_content)
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def read_csv_summary(file_path: str) -> str:
    """Reads a CSV/Excel and returns a summary."""
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        summary = []
        summary.append(f"File: {file_path}")
        summary.append(f"Shape: {df.shape}")
        summary.append(f"Columns: {list(df.columns)}")
        summary.append("First 5 rows:")
        summary.append(df.head().to_markdown())
        summary.append("\nNumeric Column Stats:")
        summary.append(df.describe().to_markdown())
        return "\n".join(summary)
    except Exception as e:
        return f"Error reading data file: {str(e)}"

# ---------------------------------------------------------------------------
# ADVANCED TOOLS
# ---------------------------------------------------------------------------
def ocr_image(image_path: str, lang: str = "eng") -> str:
    """Extracts text from an image using Tesseract OCR."""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=lang)
        return text.strip()
    except Exception as e:
        return f"OCR Error: {str(e)}"

def transcribe_audio(file_path: str) -> str:
    """Transcribes audio file to text."""
    try:
        # Convert mp3 to wav if needed
        if file_path.lower().endswith('.mp3'):
            sound = AudioSegment.from_mp3(file_path)
            wav_path = file_path.replace('.mp3', '.wav')
            sound.export(wav_path, format="wav")
            file_path = wav_path
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(file_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
        return text
    except Exception as e:
        return f"Transcription Error: {str(e)}"

def encode_image_to_base64(image_path: str) -> str:
    """
    Encodes image to base64 and stores it globally.
    Returns a placeholder key to be used by the LLM.
    """
    try:
        with open(image_path, "rb") as f:
            raw = f.read()
        encoded = base64.b64encode(raw).decode("utf-8")
        key = f"BASE64_KEY:{uuid.uuid4()}"
        BASE64_STORE[key] = encoded
        return key
    except Exception as e:
        return f"Encoding Error: {str(e)}"

def install_package(package_name: str) -> str:
    """Installs a python package."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return f"Successfully installed {package_name}"
    except Exception as e:
        return f"Installation Error: {str(e)}"

# ---------------------------------------------------------------------------
# CODE EXECUTION
# ---------------------------------------------------------------------------
def run_python_code(code: str) -> str:
    """Executes Python code and returns stdout/stderr."""
    temp_script = "temp_script.py"
    with open(temp_script, "w", encoding="utf-8") as f:
        f.write(code)
    
    try:
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=30 # Increased timeout
        )
        output = result.stdout
        if result.stderr:
            output += "\nErrors:\n" + result.stderr
        return output
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out."
    except Exception as e:
        return f"Error executing code: {str(e)}"
    finally:
        if os.path.exists(temp_script):
            os.remove(temp_script)
