# saving_quiz.py
import os
import re
import json
import hashlib
import datetime
# ----------------------------
# Ensure quizzes folder exists
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUIZZES_FOLDER =  os.path.join(BASE_DIR, "quizzes")
USER_ATTEMPTS_FOLDER =  os.path.join(BASE_DIR, "user_quizzes")
os.makedirs(QUIZZES_FOLDER, exist_ok=True)
os.makedirs(USER_ATTEMPTS_FOLDER, exist_ok=True)

def parse_quiz(raw_text):
    """
    Converts LLM text output into a structured list of quiz items (MCQs and SAQs).
    Ensures explanations are separate from options in MCQs.
    """
    parts = re.split(r'\n?Q\d+\.\s*', raw_text)
    parts = [p.strip() for p in parts if p.strip()]

    quiz_items = []

    for part in parts:
        try:
            # Check if this is an MCQ (look for options A-D)
            # Stop option capturing at "Explanation:"
            option_matches = re.findall(
                r'([A-D])\)\s*(.*?)(?=\s*[A-D]\)|\s*Correct Answer:|\s*Explanation:|$)',
                part,
                re.DOTALL
            )

            if option_matches:
                # It's an MCQ
                question_match = re.match(r'(.+?)\s*A\)', part, re.DOTALL)
                question_text = question_match.group(1).strip() if question_match else "Untitled Question"

                # Extract options
                options = {key: value.strip().replace("\n", " ") for key, value in option_matches}

                # Extract correct answer
                correct_match = re.search(r'Correct Answer:\s*([A-D])', part)
                correct_answer = correct_match.group(1).strip() if correct_match else ""

                # Extract explanation (everything after 'Explanation:')
                explanation_match = re.search(r'Explanation:\s*(.+)', part, re.DOTALL)
                explanation = explanation_match.group(1).strip() if explanation_match else ""
                explanation = " ".join(explanation.split())

                quiz_items.append({
                    "question": question_text,
                    "options": options,
                    "correct_answer": correct_answer,
                    "explanation": explanation,
                    "type": "MCQ"
                })
            else:
                # It's a SAQ
                question_match = re.match(r'(.+?)\s*Answer:', part, re.DOTALL)
                question_text = question_match.group(1).strip() if question_match else part.split("Answer:")[0].strip()

                # Extract answer (everything after 'Answer:' but before 'Explanation:' if present)
                answer_match = re.search(r'Answer:\s*(.+?)(?:Explanation:|$)', part, re.DOTALL)
                answer_text = answer_match.group(1).strip() if answer_match else ""

                # Optional explanation for SAQ
                explanation_match = re.search(r'Explanation:\s*(.+)', part, re.DOTALL)
                explanation = explanation_match.group(1).strip() if explanation_match else ""

                quiz_items.append({
                    "question": question_text,
                    "answer": answer_text,
                    "explanation": " ".join(explanation.split()) if explanation else "",
                    "type": "SAQ"
                })

        except Exception as e:
            print(f"⚠️ Error parsing quiz item: {e}")

    return quiz_items

# ============================================================
# Helper to build safe PDF base name
# ============================================================
def build_pdf_base_name(pdf_list):
    """
    Returns:
    - single PDF  → pdfName
    - multiple PDFs → pdfName1_pdfName2_pdfName3
    Removes ALL occurrences of '.pdf' (case-insensitive)
    """
    if isinstance(pdf_list, str):
        pdf_list = [pdf_list]

    base_names = []

    for p in pdf_list:
        filename = os.path.basename(p)

        # 🔥 Remove ALL .pdf occurrences (even in malformed names)
        name = re.sub(r'\.pdf$', '', filename, flags=re.IGNORECASE)
        name = re.sub(r'\.pdf_', '_', name, flags=re.IGNORECASE)
        name = re.sub(r'\.pdf', '', name, flags=re.IGNORECASE)

        clean_name = (
            name.replace(" ", "_")
                .replace("-", "_")
        )

        base_names.append(clean_name)

    # ORDER-INDEPENDENT
    return "_".join(sorted(base_names))

# ============================================================
# Save or retrieve quiz from cache
# ============================================================
def save_quiz(pdf_paths, quiz_data):
    os.makedirs(QUIZZES_FOLDER, exist_ok=True)

    quiz_base = build_pdf_base_name(pdf_paths)
    quiz_file_path = os.path.join(QUIZZES_FOLDER, f"{quiz_base}.json")

    # Cache check
    if os.path.exists(quiz_file_path):
        print(f"⚠️ Quiz already exists: {quiz_file_path}")
        return quiz_file_path

    data = {
        "pdf_names": quiz_base,  # no .pdf, combined if multiple
        "quiz": quiz_data,
        "created_at": datetime.datetime.now().isoformat()
    }

    with open(quiz_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Quiz saved: {quiz_file_path}")
    return quiz_file_path

def save_user_attempt(user_id, pdf_paths, attempt_record):
    """
    Save user quiz attempt with LLM-based SAQ evaluation results.
    
    New fields in evaluated_quiz for SAQ questions:
    - score: float (0.0-1.0) from LLM evaluation
    - verdict: string (CORRECT | PARTIALLY_CORRECT | INCORRECT)
    - explanation: from LLM evaluation (improved over document-based)
    """
    os.makedirs(USER_ATTEMPTS_FOLDER, exist_ok=True)

    quiz_base = build_pdf_base_name(pdf_paths)
    filename = f"{quiz_base}_{user_id}.json"
    filepath = os.path.join(USER_ATTEMPTS_FOLDER, filename)

    # Calculate detailed statistics
    total_questions = attempt_record["total_questions"]
    total_correct = attempt_record["total_correct"]
    percentage = (total_correct / total_questions * 100) if total_questions > 0 else 0

    # Calculate SAQ score (sum of all SAQ scores normalized)
    evaluated_quiz = attempt_record["evaluated_quiz"]
    saq_scores = []
    for q in evaluated_quiz:
        if q.get("type") == "SAQ" and q.get("score") is not None:
            saq_scores.append(q.get("score", 0.0))
    
    avg_saq_score = (sum(saq_scores) / len(saq_scores) * 100) if saq_scores else 0

    data = {
        "user_id": user_id,
        "pdf_names": quiz_base,
        "attempted_at": str(datetime.datetime.now()),
        
        # Basic stats
        "total_questions": total_questions,
        "total_correct": total_correct,
        "percentage_correct": round(percentage, 2),
        
        # LLM-based SAQ evaluation
        "saq_average_score": round(avg_saq_score, 2),
        "saq_count": sum(1 for q in evaluated_quiz if q.get("type") == "SAQ"),
        "mcq_count": sum(1 for q in evaluated_quiz if q.get("type") == "MCQ"),
        
        # Full evaluated quiz with new LLM fields
        "evaluated_quiz": evaluated_quiz,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ User attempt saved: {filepath}")
    print(f"   Score: {total_correct}/{total_questions} ({percentage:.1f}%)")
    print(f"   SAQ Average Score: {avg_saq_score:.1f}%")

    return {
        "status": "success",
        "file_saved": filename,
        "score": f"{total_correct}/{total_questions}",
        "percentage": percentage,
        "saq_average": avg_saq_score
    }

def load_existing_quiz(pdf_paths):
    quiz_base = build_pdf_base_name(pdf_paths)
    quiz_file_path = os.path.join(QUIZZES_FOLDER, f"{quiz_base}.json")

    print(f"🔎 Looking for quiz file: {quiz_file_path}")

    if not os.path.exists(quiz_file_path):
        return None   # 🔥 THIS IS THE FIX

    with open(quiz_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extra safety: reject empty quizzes
    if not data.get("quiz"):
        return None

    return data
