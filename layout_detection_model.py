import layoutparser as lp

try:
    model = lp.models.AutoLayoutModel('lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config')
    print("Model loaded?", model is not None)
except Exception as e:
    print("Failed to load model:", e)

import detectron2
print("Detectron2 imported successfully!")