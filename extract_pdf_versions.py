import sys
import os
import re

def extract_xref_versions(pdf_path):
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    # Find all locations of b'startxref' (as bytes)
    startxref_matches = [m.start() for m in re.finditer(b'startxref', pdf_bytes)]

    if not startxref_matches:
        print("No 'startxref' found in PDF.")
        return

    # Find all locations of b'%%EOF' after each startxref
    eof_matches = []
    for sx_pos in startxref_matches:
        eof_match = re.search(b'%%EOF', pdf_bytes[sx_pos:])
        if eof_match:
            eof_pos = sx_pos + eof_match.end()
            eof_matches.append(eof_pos)

    if len(eof_matches) != len(startxref_matches):
        print("Mismatch in 'startxref' and '%%EOF' counts. File might be malformed.")
        return

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    for i, eof_pos in enumerate(eof_matches):
        out_name = f"{base_name}_version_{i+1}.pdf"
        with open(out_name, 'wb') as out:
            out.write(pdf_bytes[:eof_pos])
        print(f"Wrote {out_name} (up to incremental update {i+1})")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_pdf_versions.py path/to/file.pdf")
    else:
        extract_xref_versions(sys.argv[1])