import requests
import re, os
import time

# Define API URL
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"

# Hugging Face API Token
HEADERS = {"Authorization": f"Bearer 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"}

UPLOAD_FOLDER = "uploads"
RESULT_FILE = os.path.join(UPLOAD_FOLDER, "grading_results.txt")
SCORECARD_FILE = os.path.join(UPLOAD_FOLDER, "scorecard.txt")
QUESTION_FILE = os.path.join(UPLOAD_FOLDER, "uploaded_questions.txt")

# Function to extract total marks from uploaded_questions.txt
def extract_total_marks(filename):
    if not os.path.exists(filename):
        return 10  # Default value

    with open(filename, 'r', encoding="utf-8") as file:
        first_line = file.readline().strip()

    match = re.search(r"Total Marks:\s*(\d+)", first_line)
    return int(match.group(1)) if match else 10  # Default value if extraction fails

# Extract total marks
TOTAL_MARKS = extract_total_marks(QUESTION_FILE)

# Function to read question-answer pairs
def read_question_answer_pairs(filename):
    if not os.path.exists(filename) or os.stat(filename).st_size == 0:
        return []

    with open(filename, 'r', encoding="utf-8") as file:
        content = file.read().strip().split('\n\n')

    if not content:
        return []

    pairs = []
    for block in content:
        lines = block.split('\n')
        if len(lines) >= 2:
            question = lines[0].replace("Question: ", "").strip()
            answer = lines[1].replace("Answer: ", "").strip()
            pairs.append((question, answer))
    return pairs

# Extract marks from the question
def extract_marks(question):
    match = re.search(r"\((\d+)\s*M\)", question)
    return int(match.group(1)) if match else 10  # Default to 10 marks

# Apply word penalty reduction based on answer length
def apply_word_penalty(student_answer, model_marks, total_marks):
    word_count = len(student_answer.split())

    penalties = {
        2: {"ideal": (70, 80), "mild": (40, 50, 0.5), "severe": (15, 25, 1)},
        5: {"ideal": (200, 250), "mild": (150, 170, 1), "severe": (100, 120, 2)},
        10: {"ideal": (600, 650), "mild": (500, 530, 2), "severe": (400, 450, 3)}
    }

    if total_marks not in penalties:
        return model_marks  # No penalty if total marks category isn't defined

    penalty_data = penalties[total_marks]
    penalty_reduction = 0

    # Apply penalty based on word count
    if word_count <= penalty_data["severe"][1]:  # Severe penalty
        penalty_reduction = penalty_data["severe"][2]
    elif penalty_data["severe"][1] < word_count < penalty_data["mild"][0]:  # Between severe & mild
        penalty_reduction = penalty_data["severe"][2]
    elif penalty_data["mild"][0] <= word_count <= penalty_data["mild"][1]:  # Mild penalty
        penalty_reduction = penalty_data["mild"][2]

    # Ensure marks never go negative
    final_marks = max(model_marks - penalty_reduction, 0)
    return min(final_marks, model_marks)  # Ensure no marks exceed model grading

# Grade student's answer using API
def grade_answer(question, student_answer, total_marks):
    try:
        grading_prompt = f"""Compare the student's answer with the correct answer and assign a score out of {total_marks}.
        Give a score based on factual correctness and logical accuracy. Do NOT explain, just provide the score.

        Question: {question}
        Student's Answer: {student_answer}

        Provide the score in the format: "Score: X out of {total_marks}"
        """

        response = requests.post(API_URL, headers=HEADERS, json={"inputs": grading_prompt})
        response_json = response.json()

        if isinstance(response_json, list) and "generated_text" in response_json[0]:
            graded_response = response_json[0]["generated_text"]
        else:
            return 0

        match = re.search(r"Score:\s*(\d+(\.\d+)?)\s*out\s*of\s*(\d+)", graded_response)
        model_marks = float(match.group(1)) if match else total_marks

        # Apply word penalty after grading
        return apply_word_penalty(student_answer, model_marks, total_marks)

    except Exception as e:
        return 0  # Default to 0 if grading fails

# Main function
def main():
    input_path = os.path.join(UPLOAD_FOLDER, "question_answer.txt")
    question_answer_pairs = read_question_answer_pairs(input_path)

    if not question_answer_pairs:
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            f.write("Error: No questions found for grading.")
        return

    results = []
    graded_questions = []

    for idx, (question, student_answer) in enumerate(question_answer_pairs, start=1):
        total_marks = extract_marks(question)
        obtained_marks = grade_answer(question, student_answer, total_marks)

        results.append(f"Question: {question}\nStudent's Answer: {student_answer}\nScore: {obtained_marks}/{total_marks}\n")
        graded_questions.append((question, student_answer, obtained_marks, total_marks))

    # Filtering for 20 Marks system
    if TOTAL_MARKS == 20:
        filtered_questions = []
        question_groups = {}

        for q, ans, marks, total in graded_questions:
            main_q_no = q.split(".")[0]
            if main_q_no not in question_groups:
                question_groups[main_q_no] = []
            question_groups[main_q_no].append((q, ans, marks, total))

        if "1" in question_groups:
            question_groups["1"].sort(key=lambda x: x[2], reverse=True)
            filtered_questions.extend(question_groups["1"][:5])

        for main_q in ["2", "3"]:
            if main_q in question_groups:
                question_groups[main_q].sort(key=lambda x: x[2], reverse=True)
                filtered_questions.extend(question_groups[main_q][:1])

        graded_questions = filtered_questions

    # Filtering for 80 Marks system
    if TOTAL_MARKS == 80:
        filtered_questions = []
        question_groups = {}

        for q, ans, marks, total in graded_questions:
            main_q_no = q.split(".")[0]
            if main_q_no not in question_groups:
                question_groups[main_q_no] = []
            question_groups[main_q_no].append((q, ans, marks, total))

        if "1" in question_groups:
            question_groups["1"].sort(key=lambda x: x[2], reverse=True)
            filtered_questions.extend(question_groups["1"][:4])

        main_question_scores = sorted(
            [(main_q, sum(marks for _, _, marks, _ in question_groups[main_q]))
             for main_q in ["2", "3", "4", "5", "6"] if main_q in question_groups],
            key=lambda x: x[1], reverse=True
        )[:3]

        for main_q, _ in main_question_scores:
            filtered_questions.extend(question_groups[main_q])

        graded_questions = filtered_questions

    # Calculate total marks obtained
    total_obtained = sum(marks for _, _, marks, _ in graded_questions)
    
    # Determine pass/fail status
    passing_threshold = 8 if TOTAL_MARKS == 20 else 32
    status = "PASS" if total_obtained >= passing_threshold else "FAIL"

    # Save filtered results
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(results))

    with open(SCORECARD_FILE, "w", encoding="utf-8") as f:
        f.write("Question Number\tQuestion\tStudent Answer\tMarks Obtained\n")
        for idx, (q, ans, marks, total) in enumerate(graded_questions, start=1):
            f.write(f"{idx}\t{q}\t{ans}\t{marks}\n")
        # Add total marks and status at the end
        f.write(f"TOTAL\t \t \t{total_obtained}\n")
        f.write(f"STATUS\t \t \t{status}\n")

    print("✅ Grading Completed!")

if __name__ == "__main__":
    main()