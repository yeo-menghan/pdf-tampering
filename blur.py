from pdf2image import convert_from_path
from PIL import ImageDraw
import cv2
import numpy as np

def detect_blur_regions(image, window_size=100, threshold=100):
    img = np.array(image)
    if len(img.shape) == 3:
        img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        img_gray = img
    h, w = img_gray.shape
    boxes = []
    for y in range(0, h, window_size):
        for x in range(0, w, window_size):
            window = img_gray[y:y+window_size, x:x+window_size]
            if window.shape[0] != window_size or window.shape[1] != window_size:
                continue
            laplacian_var = cv2.Laplacian(window, cv2.CV_64F).var()
            if laplacian_var < threshold:
                boxes.append((x, y, x+window_size, y+window_size))
    return boxes

def draw_boxes_on_image(image, boxes):
    draw = ImageDraw.Draw(image)
    for box in boxes:
        draw.rectangle(box, outline="red", width=3)
    return image

# Main process
pages = convert_from_path('test.pdf', dpi=300)
print("Total pages:", len(pages))
new_pages = []
for page in pages:
    boxes = detect_blur_regions(page)
    new_img = draw_boxes_on_image(page.copy(), boxes)
    new_pages.append(new_img.convert("RGB"))
    print(f"Detected {len(boxes)} blur regions on a page.")

new_pages[0].save('output.pdf', save_all=True, append_images=new_pages[1:])