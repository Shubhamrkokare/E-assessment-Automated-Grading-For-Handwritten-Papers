import os
import re
import pandas as pd

UPLOAD_FOLDER = "uploads"
TEXT_FILE_PATH = os.path.join(UPLOAD_FOLDER, "uploaded_questions.txt")

# Convert Excel file to Text (Extracting Questions & Marks)
def convert_excel_to_text(excel_path):
    df = pd.read_excel(excel_path, header=None)  # Read Excel file without headers
    df = df.dropna(how='all')  # Remove empty rows

    total_marks = df.iloc[0, 1]  # Extract "Total Marks" from Row 1
    df = df.iloc[2:, :]  # Start reading from Row 3 onward (actual questions)
    
    questions = df.iloc[:, 0].astype(str).tolist()  # Extract Column A (Question Number)
    question_texts = df.iloc[:, 1].astype(str).tolist()  # Extract Column B (Question Text)
    marks = df.iloc[:, 2].astype(str).tolist()  # Extract Column C (Marks)

    with open(TEXT_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(f"Total Marks: {total_marks}\n\n")  # Save total marks at the beginning
        for num, text, mark in zip(questions, question_texts, marks):
            f.write(f"{num} {text.strip()} ({mark} M)\n")  # FIX: Now includes marks

    print(f"✅ Excel converted: Questions saved in {TEXT_FILE_PATH}")

# Read Lines from Text File
def read_lines_from_file(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, 'r', encoding="utf-8") as file:
        return [line.strip() for line in file.readlines()]

# Extract Identifier (Format: "1.1." or "2.A.")
def extract_identifier(text):
    match = re.match(r"(\d+\.\w+)", text)  # FIX: Removed extra dot capture
    return match.group(1) if match else None

# --- STEP 1: FIND UPLOADED QUESTION FILE ---
question_file = None
for file in os.listdir(UPLOAD_FOLDER):
    if file.endswith(".xlsx"):  # If Excel file is found, convert it
        excel_file = os.path.join(UPLOAD_FOLDER, file)
        convert_excel_to_text(excel_file)
        question_file = TEXT_FILE_PATH
        break  # Stop searching after finding an Excel file
    elif file.endswith(".txt"):  # If a text file is found, use it directly
        question_file = os.path.join(UPLOAD_FOLDER, file)

if not question_file:
    print("❌ Error: No question file found in uploads folder!")
    exit()

# --- STEP 2: READ QUESTIONS & ANSWERS ---
questions = read_lines_from_file(question_file)
answers = read_lines_from_file(os.path.join(UPLOAD_FOLDER, "answers.txt"))

# --- STEP 3: MATCH QUESTIONS WITH ANSWERS ---
question_dict = {extract_identifier(q): q for q in questions if extract_identifier(q)}
answer_dict = {extract_identifier(a): a for a in answers if extract_identifier(a)}

matched_pairs = []
for q_id, question in question_dict.items():
    answer = answer_dict.get(q_id)
    if answer:
        matched_pairs.append((question, answer))

# --- STEP 4: SAVE MATCHED PAIRS ---
output_path = os.path.join(UPLOAD_FOLDER, "question_answer.txt")
with open(output_path, 'w', encoding="utf-8") as file:
    for question, answer in matched_pairs:
        file.write(f"Question: {question}\n")
        file.write(f"Answer: {answer}\n\n")

print(f"✅ Matched questions and answers saved to {output_path}")
