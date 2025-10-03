import layoutparser as lp
import cv2
import fitz  # PyMuPDF
from PIL import Image
import io
from layoutparser.ocr import TesseractAgent

PDF_PATH = 'data/Cosworth Quotation.pdf'
OUTPUT_TEXT_PATH = 'ocr_output/Cosworth Quotation OCR.pdf'

print("Before loading model...")
# MODEL = lp.models.Detectron2LayoutModel(
#     config_path='lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config',
#     label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"},
#     extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.8]
# )
MODEL = lp.models.AutoLayoutModel('lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config')
print("After loading model...")


OCR_AGENT = TesseractAgent(languages='eng')
RELEVANT_TYPES = ['Text', 'Table']

print("Testing model with dummy image...")
import numpy as np
dummy = Image.fromarray(np.ones((100, 100, 3), dtype=np.uint8) * 255)
test_layout = MODEL.detect(dummy)
print("Model loaded and can run detection ✅")

# def pdf_page_to_pil(page, zoom=2):
#     '''
#     Converts a PyMuPDF page to a high-resolution PIL image
#     '''
#     mat = fitz.Matrix(zoom, zoom) # higher zoom == better OCR
#     pix = page.get_pixmap(matrix=mat, alpha=False)
#     img_bytes = pix.tobytes('png')
#     return Image.open(io.BytesIO(img_bytes))


# def extract_text_from_pdf(pdf_path):
#     doc = fitz.open(pdf_path)
#     all_text = ""
#     for page_num in range(len(doc)):
#         print(f'Processing page {page_num + 1} of {len(doc)}...')
#         page = doc[page_num]
#         pil_image = pdf_page_to_pil(page, zoom=2.0) # 2x zoom (~300 DPI)

#         # Detect layout blocks
#         layout = MODEL.detect(pil_image)
#         # Sort blocks top-to-bottom, left-to-right for logical order
#         layout = lp.Layout(sorted(layout, key=lambda b: (b.block.y_1, b.block.x_1)))

#         for block in layout:
#             if block.type in RELEVANT_TYPES:
#                 cropped_img = block.crop_image(pil_image)
#                 text = OCR_AGENT.detect(cropped_img)
#                 if text.strip():
#                     all_text += text.strip() + "\n\n"
        
#         return all_text

# if __name__ == "__main__":
#     print("Starting...")
#     extracted_text = extract_text_from_pdf(pdf_path=PDF_PATH)
#     with open(OUTPUT_TEXT_PATH, 'w', encoding='utf-8') as f:
#         f.write(extracted_text)
#     print(f'\nExtraction complete! Saved to: {OUTPUT_TEXT_PATH}')

