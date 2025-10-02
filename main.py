import fitz  # PyMuPDF

def analyze_pdf_ocgs_and_blocks(pdf_path):
    doc = fitz.open(pdf_path)

    # Try to get the catalog object (xref 1 is typically the catalog)
    try:
        catalog = doc.xref_object(1, compressed=False)
        if "/OCProperties" in catalog:
            print("Document has Optional Content Groups (OCGs) / layers.")
        else:
            print("No OCGs found in the document.")
    except Exception as e:
        print("Could not access PDF catalog object:", e)

    print("="*50)

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        print(f"Page {page_num + 1}:")
        print("-"*40)

        # Get content blocks in draw order (z-order: bottom to top)
        blocks = page.get_text("dict")["blocks"]

        for idx, block in enumerate(blocks):
            block_type = block["type"]
            if block_type == 0:
                # Text block
                snippet = block['lines'][0]['spans'][0]['text'][:40].replace('\n', ' ')
                print(f"  Block {idx:02d}: Text: \"{snippet}\" ...")
            elif block_type == 1:
                print(f"  Block {idx:02d}: Image")
            elif block_type == 4:
                print(f"  Block {idx:02d}: Vector Drawing")
            elif block_type == 5:
                print(f"  Block {idx:02d}: Form XObject")
            else:
                print(f"  Block {idx:02d}: Other Type {block_type}")

        # Check for /OC (Optional Content) references in the page object
        try:
            page_obj = doc.xref_object(page.xref, compressed=False)
            if "/OC" in page_obj:
                print("  [!] This page's PDF object references /OC (may use a layer).")
        except Exception:
            pass

        print()

# Usage
analyze_pdf_ocgs_and_blocks("test.pdf")