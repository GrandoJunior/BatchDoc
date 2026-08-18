import fitz
import sys

try:
    doc = fitz.open(sys.argv[1])
    print(f"Pages: {len(doc)}")
except Exception as e:
    print(f"Error: {e}")
