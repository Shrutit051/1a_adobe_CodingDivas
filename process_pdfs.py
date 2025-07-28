import os
import time
from pathlib import Path
from extract_headings import PDFHeadingExtractor
import json

INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"

def main():
    start_time = time.time()  # Start timing

    extractor = PDFHeadingExtractor()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith(".pdf"):
            in_path = os.path.join(INPUT_DIR, filename)
            out_path = os.path.join(OUTPUT_DIR, Path(filename).with_suffix('.json').name)
            try:
                result = extractor.extract_structured_headings(in_path, include_text=False)
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=4, ensure_ascii=False)
                print(f"Processed: {filename}")
            except Exception as e:
                print(f"Failed: {filename} - {e}")

    end_time = time.time()
    duration = end_time - start_time

if __name__ == "__main__":
    main()
