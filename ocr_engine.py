import pytesseract
from PIL import Image

# Tell pytesseract exactly where Tesseract-OCR is installed
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text_with_positions(image_path):
    """Runs OCR on the image and returns a list of detected text blocks,
    each with its bounding box (left, top, width, height)."""
    image = Image.open(image_path)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    results = []
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        if text:  # skip empty detections
            results.append({
                "text": text,
                "left": data["left"][i],
                "top": data["top"][i],
                "width": data["width"][i],
                "height": data["height"][i],
            })
    return results


if __name__ == "__main__":
    # Quick manual test — run this file directly to check OCR works
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ocr_engine.py <path_to_image>")
    else:
        results = extract_text_with_positions(sys.argv[1])
        for item in results:
            print(item)