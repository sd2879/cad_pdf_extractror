from paddleocr import PaddleOCR
import cv2

paddle_ocr_instance = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True)

def get_ocr_results(image_path):
    img = cv2.imread(image_path)
    ocr_result = paddle_ocr_instance.ocr(img, cls=True)
    print(ocr_result)
    
    if ocr_result and ocr_result[0]:
        text_lines = []
        for line in ocr_result[0]:
            text_lines.append(line[1][0])
        
        return text_lines if text_lines else None