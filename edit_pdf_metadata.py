import fitz  # PyMuPDF
from datetime import datetime, timedelta

def set_pdf_dates(pdf_path, output_path, creation_date, mod_date):
    """
    Set the /CreationDate and /ModDate of a PDF using PyMuPDF.

    Args:
        pdf_path (str): Path to the input PDF.
        output_path (str): Path to save the modified PDF.
        creation_date (datetime): Desired creation date.
        mod_date (datetime): Desired modification date.
    """
    # PDF date format: D:YYYYMMDDHHmmSS
    def pdf_date(dt):
        return dt.strftime("D:%Y%m%d%H%M%S")
    
    doc = fitz.open(pdf_path)
    metadata = doc.metadata

    metadata["creationDate"] = pdf_date(creation_date)
    metadata["modDate"] = pdf_date(mod_date)

    doc.set_metadata(metadata)
    doc.save(output_path)
    doc.close()

# Example usage:
if __name__ == "__main__":
    # Set creation date to now, modification date to 40 days later
    creation = datetime.now()
    modification = creation + timedelta(days=40)
    set_pdf_dates(
        pdf_path="sample-data/hi.pdf",         # Replace with your PDF file
        output_path="sample-data/hi_metadata_edited.pdf",     # This will contain the modified dates
        creation_date=creation,
        mod_date=modification
    )
    print("PDF dates updated and saved to output.pdf")