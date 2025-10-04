import os
import shutil
import cv2
import json
import tempfile
import requests
from pdf2image import convert_from_path
from PIL import Image
import re

# Azure OCR subscription key and endpoint
subscription_key = "add your own key"
assert subscription_key
vision_base_url = "https://northcentralus.api.cognitive.microsoft.com/vision/v2.0/recognizeText?"

def clear_output_folder(folder_path):
    """Delete all contents of the output folder."""
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path, exist_ok=True)

def resize(image):
    """Resize image to half its original dimensions."""
    imgH, imgW = image.shape[:2]
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    image_path = temp_file.name
    image = cv2.resize(image, (imgW // 2, imgH // 2))
    cv2.imwrite(image_path, image)
    return image_path

def tiff2img(image_path):
    """Convert TIFF image to JPEG format."""
    image = Image.open(image_path)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_image_path = temp_file.name
    image.save(temp_image_path, 'JPEG', quality=96)
    return temp_image_path

def azure_ocr(image):
    """Extract text from image using Azure OCR."""
    _, image_data = cv2.imencode('.jpg', image)
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/octet-stream'
    }
    params = {'mode': 'Printed'}
    response = requests.post(
        vision_base_url, headers=headers, params=params, data=image_data.tobytes()
    )
    response.raise_for_status()
    operation_url = response.headers["Operation-Location"]

    # Polling for the result
    analysis = {}
    while True:
        response_final = requests.get(operation_url, headers=headers)
        analysis = response_final.json()
        if "recognitionResult" in analysis:
            break
        if "status" in analysis and analysis['status'] == 'Failed':
            raise Exception("OCR processing failed.")
    
    # Extracting words and their bounding boxes
    words = [
        (line["boundingBox"], line["text"])
        for line in analysis["recognitionResult"]["lines"]
    ]
    return words

def process_image(image_path):
    """Process an image file to extract text."""
    filename, file_extension = os.path.splitext(image_path)
    if file_extension.lower() in (".tif", ".tiff"):
        image_path = tiff2img(image_path)
    image = cv2.imread(image_path)

    # Resize image if dimensions are too large
    while max(image.shape[:2]) > 4000:
        image_path = resize(image)
        image = cv2.imread(image_path)

    words = azure_ocr(image)
    extracted_text = " ".join(word[1] for word in words)
    return extracted_text.strip()

def pdf_to_images(pdf_path, output_folder):
    """Convert PDF pages to images and save them to the output folder."""
    clear_output_folder(output_folder)
    images = convert_from_path(pdf_path)
    for i, page in enumerate(images):
        output_path = os.path.join(output_folder, f"page_{i + 1}.png")
        page.save(output_path, "PNG")
        print(f"Saved: {output_path}")

def process_images(folder_path):
    """Process all images in the specified folder to extract text."""
    full_text = ""
    images = sorted(
        os.path.join(folder_path, img)
        for img in os.listdir(folder_path)
        if img.lower().endswith(('.png', '.jpg', '.jpeg'))
    )
    for image in images:
        text = process_image(image)
        full_text += text + "\n"
    return full_text

def reformat_text(input_text):
    """Reformat extracted text into structured question-answer pairs."""
    question_pattern = r"(\d+\s*\.\s*\d+|\d+\s*\.\s*[A-Za-z])\s*(Ans\.?)\s*"

    # Use regex to find all matches and their positions
    matches = list(re.finditer(question_pattern, input_text))
    if not matches:
        return "No matches found in the input text. Please check the formatting."

    output = []

    # Iterate through all matches to extract and format question-answer pairs
    for idx, match in enumerate(matches):
        question_number = re.sub(r"\s+", "", match.group(1))  # Remove extra spaces from question number
        ans_label = match.group(2).strip()  # Extract "Ans."

        # Determine the start and end of the current answer
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(input_text)

        # Extract the content of the answer
        content = input_text[start:end].strip()

        # Handle multiline content by replacing extra spaces or newlines
        content = " ".join(content.split())

        # Format the question-answer pair
        formatted_output = f"{question_number}. {ans_label} {content}"
        output.append(formatted_output)

    return "\n\n".join(output)

# Specify input PDF and output folder
pdf_path = os.path.join("uploads", "uploaded_pdf.pdf")  # Generic filename
output_folder = "uploads/output"

# Convert PDF to images and extract text
pdf_to_images(pdf_path, output_folder)
extracted_text = process_images(output_folder)

# Reformat the extracted text
formatted_text = reformat_text(extracted_text)
# print(formatted_text)


def save_text_to_file(text, filename):
    """Save the given text to a file."""
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(text)
    # print(f"Text saved to {filename}")

# Example usage
output_filename = os.path.join("uploads", "answers.txt")
save_text_to_file(formatted_text, output_filename)
