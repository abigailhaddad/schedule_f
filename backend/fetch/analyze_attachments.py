#!/usr/bin/env python3
"""
Analyze attachment text extraction from a results folder.
This script:
1. Extracts text from supported file types locally (PDF, DOCX, TXT)
2. Identifies attachments with minimal text
3. Re-extracts those using Gemini
4. Updates in-memory text map with Gemini results
"""

import os
import re
import json
import time
import base64
import string
import argparse
import requests
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import docx

# Load environment variables
load_dotenv()

def extract_text_local(file_path):
    ext = file_path.lower().split('.')[-1]
    try:
        if ext == 'pdf':
            reader = PdfReader(file_path)
            return "\n".join(page.extract_text() or '' for page in reader.pages)
        elif ext == 'docx':
            doc = docx.Document(file_path)
            return "\n".join(para.text for para in doc.paragraphs)
        elif ext == 'txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        else:
            return ""
    except Exception as e:
        print(f"  → Local extraction failed for {file_path}: {e}")
        return ""

def extract_text_with_gemini(file_path):
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")

    with open(file_path, "rb") as f:
        encoded_data = base64.b64encode(f.read()).decode("utf-8")

    mime_type = "application/pdf" if file_path.lower().endswith(".pdf") else "image/png"

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
    headers = {"Content-Type": "application/json"}

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": encoded_data
                        }
                    },
                    {
                        "text": "Extract all the text from this document. Return only the raw text."
                    }
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)

    if response.ok:
        response_json = response.json()
        for candidate in response_json.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if "text" in part:
                    return part["text"]
        return ""
    else:
        raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}")

def analyze_attachment_extraction(results_dir):
    attachments_dir = Path(results_dir).rglob('*.*')
    attachment_texts_map = {}
    files_with_minimal_text = []
    extracted_by_type = defaultdict(lambda: {'total': 0, 'with_text': 0, 'text_length': 0})

    print(f"Analyzing files in: {results_dir}")
    for path in attachments_dir:
        if path.is_file():
            file_path = str(path)
            ext = path.suffix[1:].lower()
            text = extract_text_local(file_path)
            text_length = len(text.strip())

            if text_length < 50:
                files_with_minimal_text.append(file_path)
            else:
                extracted_by_type[ext]['with_text'] += 1
                extracted_by_type[ext]['text_length'] += text_length

            extracted_by_type[ext]['total'] += 1
            attachment_texts_map[file_path] = text

    print(f"\nFiles needing Gemini re-extraction: {len(files_with_minimal_text)}")
    for file_path in files_with_minimal_text:
        try:
            new_text = extract_text_with_gemini(file_path)
            attachment_texts_map[file_path] = new_text
            print(f"  → {os.path.basename(file_path)}: extracted {len(new_text.strip())} chars from Gemini")
            # Update file type stats after Gemini extraction
            ext = Path(file_path).suffix[1:].lower()
            if len(new_text.strip()) >= 50:
                extracted_by_type[ext]['with_text'] += 1
                extracted_by_type[ext]['text_length'] += len(new_text.strip())
        except Exception as e:
            print(f"  → Gemini failed on {file_path}: {e}")

    # Save extracted text to .txt files alongside attachments
    print("\nSaving extracted text to files...")
    saved_count = 0
    for file_path, text in attachment_texts_map.items():
        if text.strip():  # Only save non-empty text
            text_file_path = Path(file_path).with_suffix('.extracted.txt')
            try:
                with open(text_file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                saved_count += 1
            except Exception as e:
                print(f"  → Failed to save text for {file_path}: {e}")
    
    print(f"✅ Saved {saved_count} extracted text files")

    print("\nExtraction complete. Summary:")
    for ext, stats in sorted(extracted_by_type.items(), key=lambda x: x[1]['total'], reverse=True):
        success_rate = (stats['with_text'] / stats['total'] * 100) if stats['total'] else 0
        avg_len = int(stats['text_length'] / stats['with_text']) if stats['with_text'] else 0
        print(f"{ext}: {stats['with_text']}/{stats['total']} ({success_rate:.1f}%) - Avg length: {avg_len} chars")
    
    return attachment_texts_map

def main():
    parser = argparse.ArgumentParser(description='Analyze and extract attachment text using local methods and Gemini fallback')
    parser.add_argument('--results_dir', type=str, required=True, help='Path to the results directory')
    args = parser.parse_args()

    attachment_texts_map = analyze_attachment_extraction(args.results_dir)
    return 0

if __name__ == "__main__":
    exit(main())
