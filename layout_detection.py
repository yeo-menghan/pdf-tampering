import fitz  # PyMuPDF
import os
import subprocess
import json
import time

PDF_PATH = 'data/JL Quotation.pdf'
IMAGES_DIR = 'tmp_pdf_images'
MINERU_OUT_DIR = 'mineru_output'
OUTPUT_TEXT_PATH = 'ocr_output/Cosworth Quotation OCR.txt'
RELEVANT_TYPES = ['text', 'table', 'title', 'figure', 'list']

def pdf_to_images(pdf_path, images_dir):
    os.makedirs(images_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    image_paths = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom
        img_path = os.path.join(images_dir, f'page_{page_num+1}.png')
        pix.save(img_path)
        image_paths.append(img_path)
        print(f'Saved image: {img_path}')
    return image_paths

def run_mineru(images_dir, mineru_out_dir):
    os.makedirs(mineru_out_dir, exist_ok=True)
    cmd = [
        'mineru',
        'infer',
        '--path', images_dir,
        '--output', mineru_out_dir
    ]
    print("Running minerU CLI...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("minerU failed:")
        print(result.stderr)
        raise RuntimeError("minerU CLI failed")
    print("minerU complete.")

# def extract_text_from_mineru(mineru_out_dir, relevant_types):
#     all_text = ""
#     for fname in sorted(os.listdir(mineru_out_dir)):
#         if fname.endswith('.json'):
#             with open(os.path.join(mineru_out_dir, fname), 'r', encoding='utf-8') as f:
#                 data = json.load(f)
#             for block in data.get('blocks', []):
#                 if block.get('type') in relevant_types:
#                     text = block.get('text', '')
#                     if text.strip():
#                         all_text += text.strip() + "\n\n"
#     return all_text

if __name__ == "__main__":
    # Step 1: PDF to images
    print("Converting PDF to images...")
    t0 = time.time()
    pdf_to_images(PDF_PATH, IMAGES_DIR)
    t1 = time.time()
    print(f"PDF to images took {t1 - t0:.2f} seconds.")
    
    # Step 2: Run minerU CLI
    t2 = time.time()
    run_mineru(IMAGES_DIR, MINERU_OUT_DIR)
    t3 = time.time()
    print(f"minerU CLI inference took {t3 - t2:.2f} seconds.")

    # Step 3: Parse minerU output and extract text
    # print("Extracting OCR text from minerU output...")
    # t4 = time.time()
    # extracted_text = extract_text_from_mineru(MINERU_OUT_DIR, RELEVANT_TYPES)
    # t5 = time.time()
    # print(f"Text extraction took {t5 - t4:.2f} seconds.")

    # Step 4: Write to output file
    # os.makedirs(os.path.dirname(OUTPUT_TEXT_PATH), exist_ok=True)
    # with open(OUTPUT_TEXT_PATH, 'w', encoding='utf-8') as f:
    #     f.write(extracted_text)
    # print(f'\nExtraction complete! Saved to: {OUTPUT_TEXT_PATH}')

    print(f"\nTotal elapsed time: {t3 - t0:.2f} seconds")