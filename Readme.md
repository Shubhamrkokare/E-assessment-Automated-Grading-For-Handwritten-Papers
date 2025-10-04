# OCR & NLP-Driven E-Assessment System

## Overview
This project is an automated grading system that processes handwritten exam papers using OCR and NLP techniques. It extracts answers from PDF files, matches them with predefined questions, and grades them based on predefined criteria.

## Features
- **Automated Answer Extraction**: Extracts handwritten answers from uploaded PDFs.
- **Question Matching**: Matches extracted answers with corresponding questions.
- **Automated Grading**: Evaluates answers and assigns scores based on similarity.
- **Web Interface**: A simple frontend for uploading files and viewing results.

## Project Structure
```
project-root/
│-- static/               # Static assets (CSS, JS, images)
│-- templates/            # HTML templates (index.html, processing.html, result.html)
│-- uploads/              # Directory to store uploaded files
│-- answer.py             # Extracts answers from PDF and saves to answers.txt
│-- match.py              # Matches questions with answers
│-- grader.py             # Grades matched answers
│-- app.py                # Flask application to connect frontend and backend
│-- requirements.txt      # Python dependencies
│-- README.md             # Project documentation
```

## Installation
1. Clone the repository:
   ```sh
   git clone 
   cd E-Assessment
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Run the application:
   ```sh
   python app.py
   ```

## Usage
1. Open `http://127.0.0.1:5000/` in your browser.
2. Upload a PDF file with handwritten answers and a `question.txt` file.
3. The system will extract, match, and grade the answers automatically.
4. View the grading results on the `result.html` page.

## Dependencies
The project requires the following Python packages:
```
flask
opencv-python
pillow
numpy
requests
shutil
pdf2image
re
```

## Future Enhancements
- Improve NLP-based grading for better accuracy.
- Support multiple question formats (MCQs, diagrams, etc.).
- Add user authentication and role-based access.

## License
This project is open-source and available under the MIT License.

---
Feel free to contribute or suggest improvements!

## API Configuration

This project uses two external APIs for handwriting recognition and grading.

### 1. Google Cloud Vision API (for OCR)

We use the [Google Cloud Vision API](https://cloud.google.com/vision) to extract handwritten text from scanned answer sheets.

#### Setup Instructions:
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Vision API** in your project.
3. Create a **service account**, download the JSON key file.
4. Set the environment variable in your system:

   **Windows CMD:**
   ```sh
   set GOOGLE_APPLICATION_CREDENTIALS=path\to\credentials.json
   ```

   **macOS/Linux:**
   ```sh
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
   ```

> ⚠️ Make sure to restart your terminal/IDE after setting the environment variable.

---

### 2. Hugging Face Inference API (for grading)

We use [Hugging Face’s Inference API](https://huggingface.co/inference-api) to grade the answers using the model `mistralai/Mistral-7B-Instruct-v0.3`.

#### Setup Instructions:
1. Create an account at [https://huggingface.co](https://huggingface.co).
2. Visit [API Tokens](https://huggingface.co/settings/tokens) and create a new token.
3. Open `grader.py` and `change.py`, then **replace** the API key line:
   ```python
   HEADERS = {"Authorization": "Bearer hf_your_token_here"}
   ```
