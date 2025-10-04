from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import shutil   
import subprocess
import threading
import time
import webbrowser
import signal
import sys
import psutil  # You might need to install this: pip install psutil

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

processing_status = {"completed": False}
current_process = None
processing_thread = None

def clear_uploads():
    """Delete all files inside the uploads folder before saving new ones."""
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")

def process_files():
    """Run the processing scripts sequentially and update the processing status."""
    global processing_status, current_process
    processing_status["completed"] = False  

    try:
        print("🚀 Running Answer Extraction...")
        current_process = subprocess.Popen(["python", "answer.py"])
        current_process.wait()
        if current_process.returncode != 0:
            print("❌ Answer extraction failed or was cancelled")
            processing_status["completed"] = False
            return

        print("🚀 Running Question Matching...")
        current_process = subprocess.Popen(["python", "match.py"])
        current_process.wait()
        if current_process.returncode != 0:
            print("❌ Question matching failed or was cancelled")
            processing_status["completed"] = False
            return

        print("🚀 Running Grading...")
        current_process = subprocess.Popen(["python", "grader.py"])
        current_process.wait()
        if current_process.returncode != 0:
            print("❌ Grading failed or was cancelled")
            processing_status["completed"] = False
            return

        print("✅ All processing completed! Results are ready.")
        processing_status["completed"] = True
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        processing_status["completed"] = False
    finally:
        current_process = None

def terminate_all_child_processes():
    """Terminate all child processes created by this app."""
    # Get the current process
    current_pid = os.getpid()
    parent = psutil.Process(current_pid)
    
    # Terminate children
    for child in parent.children(recursive=True):
        print(f"Terminating child process: {child.pid}")
        try:
            child.terminate()
        except:
            pass

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/processing")
def processing():
    return render_template("processing.html")

@app.route("/result")
def result():
    return render_template("result.html")

import re

@app.route('/scorecard')
def scorecard():
    total_marks = 0
    uploaded_questions_path = os.path.join('uploads', 'uploaded_questions.txt')

    # Extract "Total Marks" from the first line
    if os.path.exists(uploaded_questions_path):
        with open(uploaded_questions_path, 'r', encoding='utf-8') as file:
            first_line = file.readline().strip()
            match = re.search(r'Total Marks:\s*(\d+)', first_line)
            if match:
                total_marks = int(match.group(1))

    # Render scorecard.html with total_marks
    return render_template('scorecard.html', total_marks=total_marks)


@app.route("/upload", methods=["POST"])
def upload():
    global processing_status, processing_thread

    if "pdfFile" not in request.files or "questionFile" not in request.files:
        return "Missing file", 400

    pdf = request.files["pdfFile"]
    question_file = request.files["questionFile"]

    if pdf.filename == "" or question_file.filename == "":
        return "No file selected", 400

    clear_uploads()

    pdf_path = os.path.join(UPLOAD_FOLDER, "uploaded_pdf.pdf")
    pdf.save(pdf_path)

    if question_file.filename.endswith(".txt"):
        question_path = os.path.join(UPLOAD_FOLDER, "uploaded_questions.txt")
    elif question_file.filename.endswith(".xlsx"):
        question_path = os.path.join(UPLOAD_FOLDER, "uploaded_questions.xlsx")
    else:
        return "Invalid file format", 400

    question_file.save(question_path)

    print(f"✅ Uploaded PDF: {pdf_path}")
    print(f"✅ Uploaded Questions File: {question_path}")

    # Cancel any existing processing
    cancel_processing()
    
    # Start new processing thread
    processing_thread = threading.Thread(target=process_files)
    processing_thread.start()

    return redirect(url_for("processing"))

@app.route("/cancel_processing", methods=["POST"])
def cancel_processing():
    """Cancel the current processing if any."""
    global current_process, processing_status
    
    if current_process is not None:
        try:
            # Terminate the current process
            current_process.terminate()
        except:
            pass
    
    # Also terminate any child processes in case there are any
    terminate_all_child_processes()
    
    processing_status["completed"] = False
    print("❌ Processing cancelled by user")
    return jsonify({"status": "cancelled"})

@app.route("/get_results")
def get_results():
    """Check if grading is complete and return results."""
    global processing_status

    result_file = os.path.join(UPLOAD_FOLDER, "grading_results.txt")

    for _ in range(15):  
        if processing_status["completed"] and os.path.exists(result_file) and os.stat(result_file).st_size > 0:
            with open(result_file, "r") as f:
                return f.read()
        time.sleep(1)  

    return "Processing", 202  

@app.route("/check_status")
def check_status():
    """Return JSON response on processing status."""
    return jsonify({"completed": processing_status["completed"]})

@app.route('/get_scorecard', methods=['GET'])
def get_scorecard():
    try:
        scorecard_path = os.path.join(UPLOAD_FOLDER, "scorecard.txt")  

        if not os.path.exists(scorecard_path):
            return jsonify({"error": "scorecard.txt not found"}), 404

        with open(scorecard_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        if len(lines) < 2:
            return jsonify({"error": "scorecard.txt is empty or has invalid data"}), 500

        scorecard = []
        total_obtained = 0
        status = "FAIL"

        # Process all lines except header
        for line in lines[1:]:
            cols = line.strip().split("\t")
            if len(cols) == 4:
                scorecard.append(cols)
                
                # If this is the TOTAL row, get the total marks
                if cols[0] == "TOTAL":
                    total_obtained = float(cols[3])
                
                # If this is the STATUS row, get the pass/fail status
                if cols[0] == "STATUS":
                    status = cols[3]

        return jsonify({
            "total_obtained": total_obtained, 
            "scorecard": scorecard,
            "status": status
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=True)