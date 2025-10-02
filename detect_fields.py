import fitz

doc = fitz.open("test.pdf")
for page_num, page in enumerate(doc, 1):
    print(f"Page {page_num}")
    # Extract AcroForm fields (widgets)
    widgets = page.widgets()
    for widget in widgets:
        if widget.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
            print(f"  Form field: {widget.field_name}, value: {widget.field_value}")

    # Extract annotations
    for annot in page.annots():
        if annot.type[0] ==  FreeText:
            print(f"  FreeText annotation: {annot.info.get('content')}")

    # Extract all visible text (for burn-in text detection)
    for block in page.get_text("dict")["blocks"]:
        if block['type'] == 0:
            snippet = block['lines'][0]['spans'][0]['text'][:40].replace('\n', ' ')
            print(f"  Text block: \"{snippet}\" ...")